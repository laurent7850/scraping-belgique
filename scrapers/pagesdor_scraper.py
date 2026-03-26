"""Scraper pour Pages d'Or (pagesdor.be).

Récupère les données enrichies des professionnels :
téléphone, email, site web, horaires, réseaux sociaux.
"""

import re
import time
import json
import logging

import requests
from bs4 import BeautifulSoup

from config import get_headers, get_random_delay, PAGESDOR_BASE_URL
from models import Professional

logger = logging.getLogger(__name__)


class PagesDorScraper:
    """Scraper pour pagesdor.be (Pages d'Or Belgique)."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_headers())

    def search(
        self,
        keyword: str,
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche sur Pages d'Or par mot-clé et localisation.

        Args:
            keyword: Mot-clé de recherche (ex: "plombier", "avocat")
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
                logger.info(f"Pages d'Or: Requête page {page} - {keyword} {location}")

                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Pages d'Or: HTTP {resp.status_code}")
                    break

                professionals = self._parse_search_page(resp.text)
                if not professionals:
                    logger.info("Pages d'Or: Plus de résultats")
                    break

                results.extend(professionals)
                logger.info(f"Pages d'Or: Page {page} - {len(professionals)} résultats (total: {len(results)})")

                page += 1
                time.sleep(get_random_delay("pagesdor"))

            except Exception as e:
                logger.error(f"Pages d'Or: Erreur page {page}: {e}")
                break

        return results[:max_results]

    def get_details(self, detail_url: str) -> Professional | None:
        """Récupère les détails complets d'un professionnel depuis sa page."""
        try:
            if not detail_url.startswith("http"):
                detail_url = PAGESDOR_BASE_URL + detail_url

            time.sleep(get_random_delay("pagesdor"))
            resp = self.session.get(detail_url, timeout=15)
            resp.raise_for_status()

            return self._parse_detail_page(resp.text)

        except Exception as e:
            logger.error(f"Pages d'Or détail: {e}")
            return None

    def enrich_professional(self, prof: Professional) -> Professional:
        """Enrichit un Professional existant avec les données Pages d'Or.

        Recherche par nom + ville et fusionne les résultats.
        """
        search_term = prof.nom
        location = prof.ville or prof.code_postal

        if not search_term:
            return prof

        results = self.search(search_term, location, max_results=5)

        # Trouver la meilleure correspondance
        best_match = self._find_best_match(prof, results)
        if best_match:
            prof.merge(best_match)
            logger.info(f"Pages d'Or: Enrichi '{prof.nom}'")

        return prof

    def _build_search_url(self, keyword: str, location: str, page: int) -> str:
        """Construit l'URL de recherche Pages d'Or.

        Format correct : https://www.pagesdor.be/trouvez/{what}/{Where}/
        Pagination : https://www.pagesdor.be/trouvez/{what}/{Where}/{page}/
        """
        # Le keyword est en minuscules dans l'URL
        keyword_slug = keyword.lower().strip().replace(" ", "-")
        keyword_slug = re.sub(r"[^a-z0-9-]", "", keyword_slug)

        if location:
            # La localisation a la première lettre en majuscule
            location_clean = location.strip()
            location_slug = location_clean[0].upper() + location_clean[1:] if location_clean else ""
            location_slug = re.sub(r"[^a-zA-Z0-9-]", "", location_slug)
            base = f"{PAGESDOR_BASE_URL}/trouvez/{keyword_slug}/{location_slug}/"
        else:
            base = f"{PAGESDOR_BASE_URL}/trouvez/{keyword_slug}/"

        if page > 1:
            base = base.rstrip("/") + f"/{page}/"

        return base

    def _parse_search_page(self, html: str) -> list[Professional]:
        """Parse une page de résultats de recherche Pages d'Or.

        Deux stratégies combinées :
        1. JSON-LD (ItemList) pour les données de base
        2. HTML (li.result-item) pour les données enrichies (adresse, horaires)
        """
        soup = BeautifulSoup(html, "lxml")

        # Stratégie 1 : JSON-LD (fiable mais parfois incomplet pour l'adresse)
        jsonld_profs = self._parse_jsonld(soup)

        # Stratégie 2 : HTML result-items (données complètes)
        html_profs = self._parse_html_results(soup)

        # Fusionner : utiliser les HTML profs comme base, enrichir avec JSON-LD
        if html_profs:
            # Associer JSON-LD aux HTML par nom
            for hp in html_profs:
                for jp in jsonld_profs:
                    if hp.nom and jp.nom and hp.nom.lower() == jp.nom.lower():
                        hp.merge(jp)
                        break
            return html_profs

        return jsonld_profs

    def _parse_jsonld(self, soup: BeautifulSoup) -> list[Professional]:
        """Parse les données JSON-LD de la page."""
        professionals = []

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if not isinstance(data, dict):
                    continue

                # Format ItemList (liste de résultats)
                if data.get("@type") == "ItemList":
                    for list_item in data.get("itemListElement", []):
                        item = list_item.get("item", list_item)
                        prof = self._parse_jsonld_item(item)
                        if prof:
                            professionals.append(prof)

                # Format direct LocalBusiness
                elif data.get("@type") in ("LocalBusiness", "Organization", "ProfessionalService"):
                    prof = self._parse_jsonld_item(data)
                    if prof:
                        professionals.append(prof)

            except (json.JSONDecodeError, TypeError):
                continue

        return professionals

    def _parse_jsonld_item(self, data: dict) -> Professional | None:
        """Parse un item JSON-LD en Professional."""
        if not isinstance(data, dict):
            return None

        name = data.get("name", "")
        if not name:
            return None

        prof = Professional(nom=name, sources="PagesDor")

        # Adresse
        address = data.get("address", {})
        if isinstance(address, dict):
            street = address.get("streetAddress", "")
            postal = address.get("postalCode", "")
            city = address.get("addressLocality", "")
            prof.adresse = street
            prof.code_postal = postal
            prof.ville = city

        # Téléphone
        raw_phone = data.get("telephone", "")
        if raw_phone:
            prof.telephone = self._format_phone(raw_phone)

        # Email
        prof.email = data.get("email", "")

        # Site web (ignorer les URLs pagesdor/goudengids)
        url = data.get("url", "") or data.get("sameAs", "")
        if url and "pagesdor" not in url and "goudengids" not in url:
            prof.site_web = url

        # Horaires
        opening_hours = data.get("openingHoursSpecification", [])
        if opening_hours:
            prof.horaires = self._format_opening_hours(opening_hours)

        return prof

    def _parse_html_results(self, soup: BeautifulSoup) -> list[Professional]:
        """Parse les résultats HTML depuis les li.result-item."""
        professionals = []

        # Structure Pages d'Or : <li class="result-item ...">
        items = soup.find_all("li", class_=re.compile(r"result-item"))

        for item in items:
            prof = self._parse_result_item(item)
            if prof and prof.nom:
                professionals.append(prof)

        return professionals

    def _parse_result_item(self, item) -> Professional | None:
        """Parse un élément li.result-item Pages d'Or.

        Structure HTML observée :
        - Nom : premier lien vers /entreprise/... avec texte court
        - Téléphone : <a href="tel:+32...">
        - Adresse : spans avec rue, code postal, ville séparés
        - Horaires : span.opening__hours
        - Site web : liens externes (pas pagesdor.be)
        """
        try:
            prof = Professional(sources="PagesDor")

            # === NOM + URL DÉTAIL ===
            # Le nom est dans le premier lien /entreprise/
            company_link = item.find("a", href=re.compile(r"/entreprise/"))
            if company_link:
                name = company_link.get_text(strip=True)
                # Ignorer les liens "Plus d'infos" et "Toutes les sociétés de"
                if name and name != "Plus d'infos" and not name.startswith("Toutes les"):
                    prof.nom = name
                # Sauvegarder l'URL de la page détail
                href = company_link.get("href", "")
                if href and "/entreprise/" in href:
                    prof.detail_url = href if href.startswith("http") else PAGESDOR_BASE_URL + href

            # Fallback : span.sr-only contient souvent le nom propre
            if not prof.nom:
                sr_only = item.find("span", class_="sr-only")
                if sr_only:
                    prof.nom = sr_only.get_text(strip=True)

            if not prof.nom:
                return None

            # === TÉLÉPHONE ===
            phone_link = item.find("a", href=re.compile(r"^tel:"))
            if phone_link:
                phone_href = phone_link["href"].replace("tel:", "")
                # Formater : +32470970297 -> 0470/97.02.97
                prof.telephone = self._format_phone(phone_href)

            # === ADRESSE ===
            # Les spans contiennent rue, code postal, ville séparément
            all_spans = item.find_all("span")
            address_parts = {"street": "", "postal": "", "city": ""}

            for i, span in enumerate(all_spans):
                text = span.get_text(strip=True)
                classes = span.get("class", [])

                # Classe text-sm avec le format "Rue..., 1000 Ville"
                if "text-sm" in classes and re.match(r".+,\s*\d{4}", text):
                    addr_match = re.match(r"(.+?),\s*(\d{4})\s*(.+)", text)
                    if addr_match:
                        address_parts["street"] = addr_match.group(1)
                        address_parts["postal"] = addr_match.group(2)
                        address_parts["city"] = addr_match.group(3)

                # Spans individuels sans classe contenant juste la rue, le CP ou la ville
                if not classes and not span.find_all():  # leaf spans
                    if re.match(r"^\d{4}$", text):
                        address_parts["postal"] = text
                    elif re.match(r"^(Rue|Avenue|Boulevard|Chaussée|Place|Allée)\b", text, re.I):
                        address_parts["street"] = text
                    elif (
                        not address_parts["city"]
                        and address_parts["postal"]
                        and re.match(r"^[A-Z]", text)
                        and len(text) > 2
                        and text not in ("Appeler", "Site Web", "Plus d'infos", "Ouvert", "Fermé")
                    ):
                        # Le span juste après le code postal est la ville
                        prev_span = all_spans[i - 1] if i > 0 else None
                        if prev_span and re.match(r"^\d{4}$", prev_span.get_text(strip=True)):
                            address_parts["city"] = text

            prof.adresse = address_parts["street"]
            prof.code_postal = address_parts["postal"]
            prof.ville = address_parts["city"]

            # === HORAIRES ===
            hours_span = item.find("span", class_=re.compile(r"opening__hours"))
            if hours_span:
                hours_text = hours_span.get_text(strip=True)
                # Nettoyer (enlever "Ouvert"/"Fermé" à la fin)
                hours_text = re.sub(r"(Ouvert|Fermé|Open|Gesloten)$", "", hours_text).strip()
                prof.horaires = hours_text

            # === SITE WEB ===
            for link in item.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if text == "Site Web" and href.startswith("http") and "pagesdor" not in href:
                    prof.site_web = href
                    break

            # === EMAIL ===
            email_link = item.find("a", href=re.compile(r"^mailto:"))
            if email_link:
                prof.email = email_link["href"].replace("mailto:", "")

            # === RÉSEAUX SOCIAUX ===
            for link in item.find_all("a", href=True):
                href = link["href"]
                if "facebook.com" in href:
                    prof.facebook = href
                elif "instagram.com" in href:
                    prof.instagram = href
                elif "linkedin.com" in href:
                    prof.linkedin = href

            return prof

        except Exception as e:
            logger.debug(f"Pages d'Or parse result-item error: {e}")
            return None

    @staticmethod
    def _format_phone(phone: str) -> str:
        """Formate un numéro de téléphone belge.

        +32470970297 -> 0470 97 02 97
        """
        phone = re.sub(r"[^\d+]", "", phone)
        if phone.startswith("+32"):
            phone = "0" + phone[3:]
        if len(phone) == 10:
            return f"{phone[:4]} {phone[4:6]} {phone[6:8]} {phone[8:]}"
        return phone

    def _parse_detail_page(self, html: str) -> Professional | None:
        """Parse une page de détail Pages d'Or."""
        soup = BeautifulSoup(html, "lxml")

        # D'abord essayer JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("name"):
                    return self._parse_jsonld_item(data)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("name"):
                            return self._parse_jsonld_item(item)
            except (json.JSONDecodeError, TypeError):
                continue

        # Fallback HTML parsing
        prof = Professional(sources="PagesDor")

        title = soup.find("h1")
        if title:
            prof.nom = title.get_text(strip=True)

        # Chercher les données structurées dans la page
        for item in soup.find_all(attrs={"itemprop": True}):
            prop = item.get("itemprop", "")
            val = item.get("content", "") or item.get_text(strip=True)

            if prop == "telephone":
                prof.telephone = val
            elif prop == "email":
                prof.email = val
            elif prop == "url" and "pagesdor" not in val:
                prof.site_web = val
            elif prop == "streetAddress":
                prof.adresse = val
            elif prop == "postalCode":
                prof.code_postal = val
            elif prop == "addressLocality":
                prof.ville = val

        return prof if prof.nom else None

    def _format_opening_hours(self, hours_spec: list) -> str:
        """Formate les horaires d'ouverture en texte lisible."""
        days_map = {
            "Monday": "Lun",
            "Tuesday": "Mar",
            "Wednesday": "Mer",
            "Thursday": "Jeu",
            "Friday": "Ven",
            "Saturday": "Sam",
            "Sunday": "Dim",
        }

        parts = []
        for spec in hours_spec:
            if not isinstance(spec, dict):
                continue
            day = spec.get("dayOfWeek", "")
            if isinstance(day, list):
                day = day[0] if day else ""
            day_name = day.split("/")[-1] if "/" in day else day
            day_short = days_map.get(day_name, day_name[:3])
            opens = spec.get("opens", "")
            closes = spec.get("closes", "")
            if opens and closes:
                parts.append(f"{day_short}: {opens}-{closes}")

        return " | ".join(parts)

    def _find_best_match(
        self, target: Professional, candidates: list[Professional]
    ) -> Professional | None:
        """Trouve la meilleure correspondance parmi les candidats."""
        if not candidates:
            return None

        best = None
        best_score = 0

        target_name = target.nom.lower().strip()

        for candidate in candidates:
            score = 0
            cand_name = candidate.nom.lower().strip()

            # Score par similarité de nom
            if target_name == cand_name:
                score += 10
            elif target_name in cand_name or cand_name in target_name:
                score += 5
            else:
                # Comparaison par mots
                target_words = set(target_name.split())
                cand_words = set(cand_name.split())
                common = target_words & cand_words
                if common:
                    score += len(common) * 2

            # Score par code postal
            if target.code_postal and candidate.code_postal:
                if target.code_postal == candidate.code_postal:
                    score += 3

            # Bonus pour les données de contact
            if candidate.telephone:
                score += 1
            if candidate.email:
                score += 1

            if score > best_score:
                best_score = score
                best = candidate

        return best if best_score >= 3 else None

    def close(self):
        self.session.close()
