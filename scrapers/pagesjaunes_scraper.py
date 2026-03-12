"""Scraper pour Pages Jaunes (pagesjaunes.fr).

Récupère les données enrichies des professionnels français :
téléphone, email, site web, adresse.
"""

import re
import time
import json
import logging

import requests
from bs4 import BeautifulSoup

from config import get_headers, get_random_delay, PAGESJAUNES_BASE_URL
from models import Professional

logger = logging.getLogger(__name__)


class PagesJaunesScraper:
    """Scraper pour pagesjaunes.fr (Pages Jaunes France)."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_headers(country="FR"))

    def search(
        self,
        keyword: str,
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche sur Pages Jaunes par mot-clé et localisation.

        Args:
            keyword: Mot-clé de recherche (ex: "plombier")
            location: Ville ou code postal
            max_results: Nombre max de résultats

        Returns:
            Liste de Professional enrichis
        """
        results = []
        page = 1

        while len(results) < max_results:
            try:
                url = self._build_search_url(keyword, location, page)
                logger.info(f"Pages Jaunes: Requête page {page} - {keyword} {location}")

                time.sleep(get_random_delay("pagesjaunes"))
                resp = self.session.get(url, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"Pages Jaunes: HTTP {resp.status_code}")
                    break

                professionals = self._parse_search_page(resp.text)
                if not professionals:
                    logger.info("Pages Jaunes: Plus de résultats")
                    break

                results.extend(professionals)
                logger.info(f"Pages Jaunes: Page {page} - {len(professionals)} résultats (total: {len(results)})")

                page += 1

            except Exception as e:
                logger.error(f"Pages Jaunes: Erreur page {page}: {e}")
                break

        return results[:max_results]

    def _build_search_url(self, keyword: str, location: str, page: int) -> str:
        """Construit l'URL de recherche Pages Jaunes."""
        base = f"{PAGESJAUNES_BASE_URL}/annuaire/chercherlespros"
        params = f"?quoiqui={requests.utils.quote(keyword)}"
        if location:
            params += f"&ou={requests.utils.quote(location)}"
        if page > 1:
            params += f"&page={page}"
        return base + params

    def _parse_search_page(self, html: str) -> list[Professional]:
        """Parse une page de résultats Pages Jaunes."""
        soup = BeautifulSoup(html, "lxml")
        professionals = []

        # Essayer JSON-LD en premier
        jsonld_profs = self._parse_jsonld(soup)
        if jsonld_profs:
            return jsonld_profs

        # Fallback: parse HTML
        items = soup.find_all("li", class_=re.compile(r"bi-pro|bi-generic"))
        if not items:
            items = soup.find_all("div", class_=re.compile(r"bi-pro|bi-generic"))

        for item in items:
            prof = self._parse_result_item(item)
            if prof and prof.nom:
                professionals.append(prof)

        return professionals

    def _parse_jsonld(self, soup: BeautifulSoup) -> list[Professional]:
        """Parse les données JSON-LD."""
        professionals = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if not isinstance(data, (dict, list)):
                    continue

                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue

                    # ItemList
                    if item.get("@type") == "ItemList":
                        for list_item in item.get("itemListElement", []):
                            inner = list_item.get("item", list_item)
                            prof = self._parse_jsonld_item(inner)
                            if prof:
                                professionals.append(prof)

                    # Direct LocalBusiness
                    elif item.get("@type") in ("LocalBusiness", "Organization", "ProfessionalService"):
                        prof = self._parse_jsonld_item(item)
                        if prof:
                            professionals.append(prof)

            except (json.JSONDecodeError, TypeError):
                continue

        return professionals

    def _parse_jsonld_item(self, data: dict) -> Professional | None:
        """Parse un item JSON-LD en Professional."""
        name = data.get("name", "")
        if not name:
            return None

        prof = Professional(nom=name, pays="FR", sources="PagesJaunes")

        # Adresse
        address = data.get("address", {})
        if isinstance(address, dict):
            prof.adresse = address.get("streetAddress", "")
            prof.code_postal = address.get("postalCode", "")
            prof.ville = address.get("addressLocality", "")

        # Téléphone
        phone = data.get("telephone", "")
        if phone:
            prof.telephone = self._format_phone(phone)

        # Email
        prof.email = data.get("email", "")

        # Site web
        url = data.get("url", "") or data.get("sameAs", "")
        if url and "pagesjaunes" not in url:
            prof.site_web = url

        return prof

    def _parse_result_item(self, item) -> Professional | None:
        """Parse un élément de résultat Pages Jaunes."""
        try:
            prof = Professional(pays="FR", sources="PagesJaunes")

            # Nom
            name_elem = item.find(class_=re.compile(r"denomination|bi-denomination|business-name"))
            if name_elem:
                link = name_elem.find("a")
                if link:
                    prof.nom = link.get_text(strip=True)
                    href = link.get("href", "")
                    if href and "/pros/" in href:
                        prof.detail_url = href if href.startswith("http") else PAGESJAUNES_BASE_URL + href
                else:
                    prof.nom = name_elem.get_text(strip=True)

            if not prof.nom:
                return None

            # Téléphone
            phone_elem = item.find("a", href=re.compile(r"^tel:"))
            if phone_elem:
                phone = phone_elem["href"].replace("tel:", "")
                prof.telephone = self._format_phone(phone)
            else:
                phone_span = item.find(class_=re.compile(r"phone|tel"))
                if phone_span:
                    phone_text = phone_span.get_text(strip=True)
                    if re.match(r"[\d\s+]+", phone_text):
                        prof.telephone = self._format_phone(phone_text)

            # Adresse
            addr_elem = item.find(class_=re.compile(r"address|adresse|bi-address"))
            if addr_elem:
                addr_text = addr_elem.get_text(strip=True)
                # Format courant : "12 Rue de la Paix 75001 Paris"
                match = re.match(r"(.+?)\s+(\d{5})\s+(.+)", addr_text)
                if match:
                    prof.adresse = match.group(1)
                    prof.code_postal = match.group(2)
                    prof.ville = match.group(3)
                else:
                    prof.adresse = addr_text

            # Site web
            for link in item.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True).lower()
                if ("site" in text or "web" in text) and "pagesjaunes" not in href and href.startswith("http"):
                    prof.site_web = href
                    break

            # Email
            email_link = item.find("a", href=re.compile(r"^mailto:"))
            if email_link:
                prof.email = email_link["href"].replace("mailto:", "").split("?")[0]

            return prof

        except Exception as e:
            logger.debug(f"Pages Jaunes parse error: {e}")
            return None

    @staticmethod
    def _format_phone(phone: str) -> str:
        """Formate un numéro de téléphone français.

        +33612345678 -> 06 12 34 56 78
        """
        phone = re.sub(r"[^\d+]", "", phone)

        if phone.startswith("+33"):
            phone = "0" + phone[3:]
        elif phone.startswith("33") and len(phone) >= 11:
            phone = "0" + phone[2:]

        # Formater en groupes de 2 (format français standard)
        if len(phone) == 10 and phone.startswith("0"):
            return f"{phone[0:2]} {phone[2:4]} {phone[4:6]} {phone[6:8]} {phone[8:10]}"

        return phone

    def close(self):
        self.session.close()
