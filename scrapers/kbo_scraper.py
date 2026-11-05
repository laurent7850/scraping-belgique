"""Scraper pour la Banque-Carrefour des Entreprises (KBO/BCE).

Recherche les entreprises belges par mot-clé
via le moteur de recherche public kbopub.economie.fgov.be.

Note : La recherche par NACE est actuellement cassée côté serveur KBO.
On utilise la recherche par mot-clé (zoeknaamfonetischform.html) comme fallback.
"""

import re
import time
import logging

import requests
from bs4 import BeautifulSoup

from config import get_headers, get_random_delay
from location_utils import get_primary_postal_code, get_postal_codes_for_location, is_province
from models import Professional

logger = logging.getLogger(__name__)


class KBOScraper:
    """Scraper pour le registre public KBO/BCE."""

    BASE_URL = "https://kbopub.economie.fgov.be/kbopub"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(get_headers())

    def search_by_keyword(
        self,
        keyword: str,
        zipcode: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche des entreprises par mot-clé.

        Utilise le formulaire de recherche phonétique par nom.

        Args:
            keyword: Mot-clé de recherche (ex: "plombier", "avocat")
            zipcode: Code postal ou nom de ville pour filtrer (optionnel)
            max_results: Nombre max de résultats

        Returns:
            Liste de Professional
        """
        # Resolve city name to postal code for KBO (expects numeric postal code)
        resolved_zip = get_primary_postal_code(zipcode) if zipcode else ""
        results = []
        page = 1

        while len(results) < max_results:
            try:
                professionals = self._fetch_search_page(keyword, resolved_zip, page)
                if not professionals:
                    break

                results.extend(professionals)
                logger.info(f"KBO: Page {page} - {len(professionals)} résultats (total: {len(results)})")

                page += 1
                time.sleep(get_random_delay("kbo"))

            except Exception as e:
                logger.error(f"KBO: Erreur page {page}: {e}")
                break

        return results[:max_results]

    def search_by_nace(
        self,
        nace_code: str,
        zipcode: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche par code NACE.

        Supporte ville (1 code postal), province (itération sur la plage),
        ou code postal direct.
        """
        postal_codes = get_postal_codes_for_location(zipcode) if zipcode else []

        if not postal_codes:
            logger.warning(
                f"KBO: Recherche NACE {nace_code} sans lieu — "
                "KBO exige un code postal pour la recherche par activité."
            )
            return []

        seen_bce: set[str] = set()
        results: list[Professional] = []

        for i in range(0, len(postal_codes), 4):
            batch = postal_codes[i:i + 4]
            batch_results = self._try_activity_search(nace_code, batch, max_results - len(results))

            for prof in batch_results:
                key = prof.numero_bce or prof.nom
                if key not in seen_bce:
                    seen_bce.add(key)
                    results.append(prof)

            logger.info(
                f"KBO NACE: codes postaux {batch} — "
                f"{len(batch_results)} résultats (total unique: {len(results)})"
            )

            if len(results) >= max_results:
                break

            if len(batch) > 1 or is_province(zipcode):
                time.sleep(get_random_delay("kbo"))

        return results[:max_results]

    def get_enterprise_details(self, enterprise_number: str) -> Professional | None:
        """Récupère les détails d'une entreprise par son numéro BCE."""
        clean_number = re.sub(r"[^0-9]", "", enterprise_number)
        if len(clean_number) == 9:
            clean_number = "0" + clean_number

        url = f"{self.BASE_URL}/toonondernemingps.html"
        params = {"ondernemingsnummer": clean_number}

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse_detail_page(resp.text, clean_number)
        except Exception as e:
            logger.error(f"KBO détail {enterprise_number}: {e}")
            return None

    def _fetch_search_page(
        self, keyword: str, zipcode: str, page: int
    ) -> list[Professional]:
        """Récupère une page de résultats via le formulaire phonétique."""
        url = f"{self.BASE_URL}/zoeknaamfonetischform.html"

        # Paramètres conformes au vrai formulaire KBO
        params = {
            "searchWord": keyword,
            "_oudeBenaming": "on",
            "pstcdeNPRP": zipcode,
            "postgemeente1": "",
            "ondNP": "true",
            "_ondNP": "on",
            "ondRP": "true",
            "_ondRP": "on",
            "rechtsvormFonetic": "ALL",
            "vest": "true",
            "_vest": "on",
            "filterEnkelActieve": "true",
            "_filterEnkelActieve": "on",
            "actionLu": "Recherche",
        }

        if page > 1:
            params["page"] = str(page)

        try:
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return self._parse_search_results(resp.text)
        except requests.RequestException as e:
            logger.error(f"KBO search request failed: {e}")
            return []

    def _try_activity_search(
        self, nace_code: str, postal_codes: list[str], max_results: int
    ) -> list[Professional]:
        """Recherche par activité NACE avec 1 à 4 codes postaux."""
        if not postal_codes:
            return []

        url = f"{self.BASE_URL}/zoekactiviteitform.html"
        clean_nace = nace_code.replace(".", "")

        params = {
            "nacecodes": clean_nace,
            "ondNP": "true",
            "_ondNP": "on",
            "ondRP": "true",
            "_ondRP": "on",
            "vest": "true",
            "_vest": "on",
            "filterEnkelActieve": "true",
            "_filterEnkelActieve": "on",
            "actionLu": "Recherche",
            "keuzeopzloc": "postnr",
        }

        for i, code in enumerate(postal_codes[:4], 1):
            params[f"postnummer{i}"] = code

        try:
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 404:
                logger.debug("KBO: Endpoint activité retourne 404")
                return []
            resp.raise_for_status()
            return self._parse_search_results(resp.text)[:max_results]
        except requests.RequestException as e:
            logger.debug(f"KBO activity search failed: {e}")
            return []

    def _parse_search_results(self, html: str) -> list[Professional]:
        """Parse la page de résultats de recherche KBO."""
        soup = BeautifulSoup(html, "lxml")
        professionals = []

        result_table = (
            soup.find("table", {"id": "onderneminglistfonetisch"})
            or soup.find("table", {"id": "result"})
            or soup.find("table", class_="table")
            or soup.find("table", class_="list")
        )

        if result_table:
            rows = result_table.find_all("tr", class_=re.compile(r"odd|even"))
        else:
            rows = soup.find_all("tr", class_=re.compile(r"odd|even"))

        for row in rows:
            prof = self._parse_result_row(row)
            if prof:
                professionals.append(prof)

        return professionals

    def _parse_result_row(self, element) -> Professional | None:
        """Parse une ligne de résultat KBO.

        Structure KBO: 6 colonnes
        [0] n° ligne  [1] type/statut  [2] n° BCE  [3] vestigings  [4] nom  [5] adresse
        """
        try:
            cells = element.find_all("td")
            if len(cells) < 5:
                return None

            # Nom — colonne avec class "benaming" ou cells[4]
            name_cell = element.find("td", class_="benaming") or cells[4]
            name = name_cell.get_text(strip=True)
            if not name:
                return None

            prof = Professional(nom=name, sources="KBO")

            # N° BCE — cells[2], extraire uniquement depuis le lien <a>
            bce_cell = cells[2]
            bce_link = bce_cell.find("a")
            if bce_link:
                bce_text = bce_link.get_text(strip=True)
                bce_match = re.search(r"(\d{4}[\.\s]?\d{3}[\.\s]?\d{3})", bce_text)
                if bce_match:
                    prof.numero_bce = bce_match.group(1)

            # Statut — cells[1]
            if len(cells) > 1:
                status_text = cells[1].get_text(strip=True)
                prof.statut = status_text

            # Adresse — cells[5]
            if len(cells) > 5:
                addr_cell = cells[5]
                addr_parts = []
                for content in addr_cell.children:
                    if getattr(content, "name", None) == "br":
                        continue
                    text = content.get_text(strip=True) if hasattr(content, "get_text") else str(content).strip()
                    text = text.replace("\xa0", " ").strip()
                    if text:
                        addr_parts.append(text)

                if addr_parts:
                    prof.adresse = ", ".join(addr_parts)

                addr_text = addr_cell.get_text(" ", strip=True).replace("\xa0", " ")
                cp_match = re.search(r"\b(\d{4})\s+([A-Za-zÀ-ÿ\-]+(?:\s+[A-Za-zÀ-ÿ\-]+)*)", addr_text)
                if cp_match:
                    prof.code_postal = cp_match.group(1)
                    prof.ville = cp_match.group(2).strip()

            return prof

        except Exception as e:
            logger.debug(f"KBO parse row error: {e}")
            return None

    def _parse_detail_page(self, html: str, bce_number: str) -> Professional | None:
        """Parse la page de détail d'une entreprise."""
        soup = BeautifulSoup(html, "lxml")
        prof = Professional(numero_bce=bce_number, sources="KBO")

        try:
            title = soup.find("h2") or soup.find("h1")
            if title:
                prof.nom = title.get_text(strip=True)

            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows:
                    header = row.find("th")
                    value = row.find("td")
                    if not header or not value:
                        continue

                    label = header.get_text(strip=True).lower()
                    val = value.get_text(strip=True)

                    if "dénomination" in label or "nom" in label:
                        prof.nom = prof.nom or val
                    elif "adresse" in label or "siège" in label:
                        prof.adresse = val
                        cp_match = re.search(r"(\d{4})\s+(.+)", val)
                        if cp_match:
                            prof.code_postal = cp_match.group(1)
                            prof.ville = cp_match.group(2)
                    elif "forme" in label and "juridique" in label:
                        prof.forme_juridique = val
                    elif "activité" in label or "nace" in label:
                        prof.description_activite = val
                        nace_match = re.search(r"(\d{2}\.\d{3})", val)
                        if nace_match:
                            prof.code_nace = nace_match.group(1)
                    elif "téléphone" in label or "phone" in label:
                        prof.telephone = val
                    elif "email" in label or "courriel" in label:
                        prof.email = val
                    elif "web" in label or "site" in label:
                        prof.site_web = val
                    elif "situation" in label or "statut" in label:
                        prof.statut = val

            return prof if prof.nom else None

        except Exception as e:
            logger.error(f"KBO detail parse error: {e}")
            return None

    def close(self):
        self.session.close()
