"""Enrichissement email multi-sources.

Trois stratégies pour trouver les adresses email des professionnels :
1. Pages d'Or : visite de la page détail de chaque entreprise
2. Site web : crawl du site de l'entreprise (accueil + /contact)
3. Google Search : recherche "{nom} {ville} email contact"

Chaque stratégie est essayée dans l'ordre jusqu'à trouver un email.
"""

import re
import time
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    get_headers,
    get_random_delay,
    PAGESDOR_BASE_URL,
    WEBSITE_CRAWL_TIMEOUT,
)
from models import Professional

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"

logger = logging.getLogger(__name__)

# Pattern email robuste (filtre les faux positifs courants)
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Emails à ignorer (faux positifs, génériques inutiles)
BLACKLISTED_EMAILS = {
    "email@example.com",
    "your@email.com",
    "info@example.com",
    "name@domain.com",
    "user@example.com",
    "test@test.com",
    "contact@example.com",
}

# Domaines email à ignorer (images, assets, etc.)
BLACKLISTED_DOMAINS = {
    "example.com",
    "sentry.io",
    "wixpress.com",
    "w3.org",
    "schema.org",
    "googleapis.com",
    "googleusercontent.com",
    "gstatic.com",
    "gravatar.com",
    "wordpress.org",
    "wordpress.com",
    "wp.com",
    "cloudflare.com",
}

# Extensions de fichiers à ignorer dans les emails trouvés
BLACKLISTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js"}


class EmailEnricher:
    """Enrichissement email via Pages d'Or détail, site web et Google."""

    def __init__(
        self,
        use_pagesdor_detail: bool = True,
        use_website_crawl: bool = True,
        use_google_search: bool = True,
        country: str = "BE",
    ):
        self.session = requests.Session()
        self.session.headers.update(get_headers(country=country))
        self.use_pagesdor_detail = use_pagesdor_detail
        self.use_website_crawl = use_website_crawl
        self.use_google_search = use_google_search
        self.country = country
        self.use_google_maps = True
        self.stats = {
            "total_processed": 0,
            "email_found_google_maps": 0,
            "email_found_pagesdor": 0,
            "email_found_website": 0,
            "email_found_google": 0,
            "email_not_found": 0,
        }

    def enrich_emails(self, professionals: list[Professional]) -> int:
        """Enrichit les emails manquants pour une liste de professionnels.

        Essaie les 3 stratégies dans l'ordre pour chaque professionnel
        sans email. S'arrête dès qu'un email est trouvé.

        Args:
            professionals: Liste de Professional à enrichir

        Returns:
            Nombre d'emails trouvés
        """
        emails_found = 0

        for prof in professionals:
            if prof.email:
                continue  # Déjà un email

            self.stats["total_processed"] += 1
            email = self._find_email(prof)

            if email:
                prof.email = email
                emails_found += 1
                if "EmailDetail" not in prof.sources:
                    prof.sources += ",EmailEnrich"
                logger.info(f"Email trouvé pour '{prof.nom}': {email}")
            else:
                self.stats["email_not_found"] += 1
                logger.debug(f"Pas d'email trouvé pour '{prof.nom}'")

        return emails_found

    def _find_email(self, prof: Professional) -> str:
        """Essaie les stratégies pour trouver un email.

        Ordre de priorité :
        1. Google Maps (rapide, une seule requête, souvent complet)
        2. Pages d'Or detail (fiable pour la Belgique)
        3. Site web entreprise (crawl accueil + contact)
        4. Google Search (fallback)
        """
        # Stratégie 1 : Google Maps
        if self.use_google_maps and prof.nom:
            email = self._try_google_maps(prof)
            if email:
                self.stats["email_found_google_maps"] += 1
                return email

        # Stratégie 2 : Pages d'Or page détail
        if self.use_pagesdor_detail and prof.detail_url:
            email = self._try_pagesdor_detail(prof)
            if email:
                self.stats["email_found_pagesdor"] += 1
                return email

        # Stratégie 3 : Crawl du site web de l'entreprise
        if self.use_website_crawl and prof.site_web:
            email = self._try_website_crawl(prof)
            if email:
                self.stats["email_found_website"] += 1
                return email

        # Stratégie 4 : Google Search
        if self.use_google_search and prof.nom:
            email = self._try_google_search(prof)
            if email:
                self.stats["email_found_google"] += 1
                return email

        return ""

    # ===================================================================
    # Stratégie 1 : Google Maps
    # ===================================================================

    def _try_google_maps(self, prof: Professional) -> str:
        """Cherche l'entreprise sur Google Maps pour extraire l'email."""
        query_parts = [prof.nom]
        if prof.ville:
            query_parts.append(prof.ville)
        elif prof.code_postal:
            query_parts.append(prof.code_postal)
        query = " ".join(query_parts)

        try:
            time.sleep(get_random_delay("google_maps"))

            url = GOOGLE_MAPS_SEARCH_URL
            params = {"api": "1", "query": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-BE,fr;q=0.9,en;q=0.5",
            }

            resp = self.session.get(
                url, params=params, headers=headers,
                timeout=WEBSITE_CRAWL_TIMEOUT, allow_redirects=True,
            )

            if resp.status_code != 200:
                return ""

            text = resp.text

            emails = self._extract_emails_from_text(text)
            if emails:
                company_words = set(w.lower() for w in prof.nom.split() if len(w) > 2)
                best = self._score_and_pick_email(emails, company_words)
                if best:
                    logger.debug(f"Google Maps: email trouvé pour '{prof.nom}': {best}")
                    return best

            if not prof.site_web:
                site_match = re.search(
                    r'"(https?://(?:www\.)?[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}[^"]*)"',
                    text,
                )
                if site_match:
                    site = site_match.group(1)
                    parsed = urlparse(site)
                    if parsed.netloc and "google" not in parsed.netloc:
                        prof.site_web = site
                        logger.debug(f"Google Maps: site web trouvé pour '{prof.nom}': {site}")

            if not prof.telephone:
                phone_match = re.search(
                    r'(\+32\s?\d[\d\s]{7,}|\b0[1-9][\d\s/\.\-]{7,})',
                    text,
                )
                if phone_match:
                    phone = re.sub(r'[\s/\.\-]', '', phone_match.group(1))
                    if len(phone) >= 9:
                        prof.telephone = phone_match.group(1).strip()

        except Exception as e:
            logger.debug(f"Google Maps error: {e}")

        return ""

    def _score_and_pick_email(self, emails: list[str], company_words: set[str]) -> str:
        """Score and pick the best email from a list."""
        scored = []
        for email in emails:
            domain = email.split("@")[1].split(".")[0].lower()
            local = email.split("@")[0].lower()
            score = 0
            for word in company_words:
                if word in domain:
                    score += 5
                if word in local:
                    score += 2
            generic_prefixes = ["info", "contact", "office", "admin", "hello"]
            if any(local.startswith(p) for p in generic_prefixes):
                score += 3
            scored.append((email, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else ""

    # ===================================================================
    # Stratégie 2 : Pages d'Or - Page détail
    # ===================================================================

    def _try_pagesdor_detail(self, prof: Professional) -> str:
        """Visite la page détail Pages d'Or pour extraire l'email.

        La page détail contient souvent plus d'infos que la liste :
        - Email dans JSON-LD
        - Email dans un lien mailto:
        - Email dans le texte (itemprop="email")
        """
        try:
            url = prof.detail_url
            if not url:
                return ""

            time.sleep(get_random_delay("pagesdor"))
            resp = self.session.get(url, timeout=WEBSITE_CRAWL_TIMEOUT)

            if resp.status_code != 200:
                logger.debug(f"Pages d'Or detail HTTP {resp.status_code} pour {url}")
                return ""

            return self._extract_email_from_pagesdor(resp.text)

        except Exception as e:
            logger.debug(f"Pages d'Or detail error: {e}")
            return ""

    def _extract_email_from_pagesdor(self, html: str) -> str:
        """Extrait l'email depuis une page détail Pages d'Or."""
        soup = BeautifulSoup(html, "lxml")

        # 1. Chercher dans JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    email = data.get("email", "")
                    if email and self._is_valid_email(email):
                        return email.lower().strip()
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            email = item.get("email", "")
                            if email and self._is_valid_email(email):
                                return email.lower().strip()
            except Exception:
                continue

        # 2. Chercher dans les liens mailto:
        mailto_link = soup.find("a", href=re.compile(r"^mailto:", re.I))
        if mailto_link:
            email = mailto_link["href"].replace("mailto:", "").split("?")[0].strip()
            if self._is_valid_email(email):
                return email.lower()

        # 3. Chercher dans les itemprop="email"
        email_elem = soup.find(attrs={"itemprop": "email"})
        if email_elem:
            email = email_elem.get("content", "") or email_elem.get_text(strip=True)
            if email and self._is_valid_email(email):
                return email.lower()

        # 4. Regex dans le texte de la page (dernière chance)
        # Limiter à certaines sections pour éviter les faux positifs
        for section_class in ["contact", "info", "detail", "company"]:
            section = soup.find(class_=re.compile(section_class, re.I))
            if section:
                emails = self._extract_emails_from_text(section.get_text())
                if emails:
                    return emails[0]

        return ""

    # ===================================================================
    # Stratégie 2 : Crawl du site web de l'entreprise
    # ===================================================================

    def _try_website_crawl(self, prof: Professional) -> str:
        """Crawle le site web de l'entreprise pour trouver un email.

        Visite 2 pages max :
        1. La page d'accueil
        2. La page /contact (si elle existe)
        """
        site_url = prof.site_web
        if not site_url:
            return ""

        # Nettoyer l'URL
        if not site_url.startswith("http"):
            site_url = "https://" + site_url

        # Page 1 : Accueil — extraire email + chercher lien contact
        try:
            time.sleep(get_random_delay("website"))
            resp = self.session.get(site_url, timeout=WEBSITE_CRAWL_TIMEOUT, allow_redirects=True)
            if resp.status_code != 200:
                return ""
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                return ""

            soup = BeautifulSoup(resp.text, "lxml")
            email = self._extract_email_from_soup(soup, site_url)
            if email:
                return email

            # Page 2 : chercher un lien contact dans la page déjà chargée
            contact_url = self._find_contact_link(soup, site_url)
            if contact_url:
                email = self._crawl_page_for_email(contact_url)
                if email:
                    return email

            # Page 3 : fallback /contact
            contact_url = urljoin(site_url, "/contact")
            email = self._crawl_page_for_email(contact_url)
            if email:
                return email

        except (requests.Timeout, requests.ConnectionError):
            pass
        except Exception as e:
            logger.debug(f"Website crawl error: {e}")

        return ""

    def _extract_email_from_soup(self, soup: BeautifulSoup, url: str) -> str:
        """Extrait un email depuis un soup BeautifulSoup déjà parsé."""
        for mailto in soup.find_all("a", href=re.compile(r"^mailto:", re.I)):
            email = mailto["href"].replace("mailto:", "").split("?")[0].strip()
            if self._is_valid_email(email):
                logger.debug(f"Email trouvé (mailto) sur {url}: {email}")
                return email.lower()

        page_text = soup.get_text(separator=" ")
        emails = self._extract_emails_from_text(page_text)
        if emails:
            domain = urlparse(url).netloc.replace("www.", "")
            domain_emails = [e for e in emails if domain.split(".")[0] in e]
            if domain_emails:
                return domain_emails[0]
            return emails[0]

        return ""

    def _crawl_page_for_email(self, url: str) -> str:
        """Visite une page et extrait les emails."""
        try:
            time.sleep(get_random_delay("website"))
            resp = self.session.get(url, timeout=WEBSITE_CRAWL_TIMEOUT, allow_redirects=True)
            if resp.status_code != 200:
                return ""
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type.lower():
                return ""
            soup = BeautifulSoup(resp.text, "lxml")
            return self._extract_email_from_soup(soup, url)
        except (requests.Timeout, requests.ConnectionError):
            pass
        except Exception as e:
            logger.debug(f"Erreur crawl {url}: {e}")
        return ""

    def _find_contact_link(self, soup: BeautifulSoup, base_url: str) -> str:
        """Cherche un lien contact dans un soup déjà parsé."""
        contact_keywords = ["contact", "contactez", "nous contacter", "kontakt"]
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True).lower()
            href = link["href"].lower()
            for kw in contact_keywords:
                if kw in text or kw in href:
                    full_url = urljoin(base_url, link["href"])
                    if urlparse(full_url).netloc == urlparse(base_url).netloc:
                        return full_url
        return ""

    # ===================================================================
    # Stratégie 3 : Google Search
    # ===================================================================

    def _try_google_search(self, prof: Professional) -> str:
        """Cherche l'email via Google Search.

        Recherche : "{nom entreprise}" "{ville}" email OR contact OR "@"
        Parse les résultats pour trouver des emails.
        """
        query = self._build_google_query(prof)
        if not query:
            return ""

        try:
            time.sleep(get_random_delay("google"))

            # Utiliser Google Search avec des headers réalistes
            search_url = "https://www.google.com/search"
            gl = "fr" if self.country == "FR" else "be"
            accept_lang = "fr-FR,fr;q=0.9,en;q=0.5" if self.country == "FR" else "fr-BE,fr;q=0.9,en;q=0.5"
            params = {
                "q": query,
                "num": 5,
                "hl": "fr",
                "gl": gl,
            }

            # Headers spécifiques pour Google
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": accept_lang,
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
            }

            resp = self.session.get(
                search_url,
                params=params,
                headers=headers,
                timeout=10,
            )

            if resp.status_code == 429:
                logger.warning("Google Search: Rate limit atteint. Pause de 60s.")
                time.sleep(60)
                return ""

            if resp.status_code != 200:
                logger.debug(f"Google Search: HTTP {resp.status_code}")
                return ""

            return self._parse_google_results(resp.text, prof)

        except Exception as e:
            logger.debug(f"Google Search error: {e}")
            return ""

    def _build_google_query(self, prof: Professional) -> str:
        """Construit la requête Google optimale."""
        parts = []

        # Nom de l'entreprise entre guillemets
        name = prof.nom.strip()
        if name:
            parts.append(f'"{name}"')

        # Ville
        if prof.ville:
            parts.append(prof.ville)

        # Mots-clés email
        parts.append("email OR contact OR @")

        return " ".join(parts)

    def _parse_google_results(self, html: str, prof: Professional) -> str:
        """Parse les résultats Google pour extraire un email.

        Cherche des emails dans :
        1. Les snippets de résultats
        2. Les URLs des résultats (page contact, etc.)
        """
        soup = BeautifulSoup(html, "lxml")

        # Extraire le texte de tous les résultats
        full_text = soup.get_text(separator=" ")

        # Chercher des emails dans le texte
        emails = self._extract_emails_from_text(full_text)

        if emails:
            company_words = set(w.lower() for w in prof.nom.split() if len(w) > 2)
            best = self._score_and_pick_email(emails, company_words)
            if best:
                logger.debug(f"Google: Email trouvé '{best}'")
                return best

        return ""

    # ===================================================================
    # Utilitaires
    # ===================================================================

    def _extract_emails_from_text(self, text: str) -> list[str]:
        """Extrait les emails valides d'un texte, filtre les faux positifs."""
        raw_emails = EMAIL_PATTERN.findall(text)
        valid = []

        seen = set()
        for email in raw_emails:
            email_lower = email.lower().strip()

            # Ignorer les doublons
            if email_lower in seen:
                continue
            seen.add(email_lower)

            # Valider
            if self._is_valid_email(email_lower):
                valid.append(email_lower)

        return valid

    def _is_valid_email(self, email: str) -> bool:
        """Vérifie qu'un email est valide et n'est pas un faux positif."""
        if not email or "@" not in email:
            return False

        email = email.lower().strip()

        # Trop court
        if len(email) < 6:
            return False

        # Blacklist
        if email in BLACKLISTED_EMAILS:
            return False

        # Vérifier le domaine
        try:
            local, domain = email.split("@", 1)
        except ValueError:
            return False

        # Domaine blacklisté
        for bd in BLACKLISTED_DOMAINS:
            if domain.endswith(bd):
                return False

        # Extension de fichier dans le local part (image@2x.png faux positif)
        for ext in BLACKLISTED_EXTENSIONS:
            if local.endswith(ext.replace(".", "")):
                return False
            if email.endswith(ext):
                return False

        # Le domaine doit avoir au moins un point
        if "." not in domain:
            return False

        # Le TLD doit avoir au moins 2 caractères
        tld = domain.split(".")[-1]
        if len(tld) < 2:
            return False

        # Ignorer les emails avec des mots "noreply", "no-reply", etc.
        ignore_prefixes = ["noreply", "no-reply", "no_reply", "donotreply", "mailer-daemon"]
        if any(local.startswith(p) for p in ignore_prefixes):
            return False

        return True

    def get_stats(self) -> dict:
        return self.stats.copy()

    def close(self):
        self.session.close()
