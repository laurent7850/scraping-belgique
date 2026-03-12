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
            zipcode: Code postal pour filtrer (optionnel)
            max_results: Nombre max de résultats

        Returns:
            Liste de Professional
        """
        results = []
        page = 1

        while len(results) < max_results:
            try:
                professionals = self._fetch_search_page(keyword, zipcode, page)
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

        NOTE: L'endpoint NACE de KBO est actuellement cassé (404).
        On tente d'abord l'endpoint activité, puis fallback sur mot-clé.
        """
        # Tentative via le formulaire activité (nouvelle URL)
        results = self._try_activity_search(nace_code, zipcode, max_results)
        if results:
            return results

        # Fallback: pas de résultats NACE, on log un warning
        logger.warning(
            f"KBO: Recherche NACE {nace_code} non disponible. "
            "Utilisez la recherche par mot-clé à la place."
        )
        return []

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
        self, nace_code: str, zipcode: str, max_results: int
    ) -> list[Professional]:
        """Tente la recherche par activité NACE (peut être cassée)."""
        url = f"{self.BASE_URL}/zoekactiviteitform.html"

        # Nettoyer le code NACE (retirer le point)
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
        }

        if zipcode:
            params["keuzeopzloc"] = "postnr"
            params["postnummer1"] = zipcode
        else:
            params["keuzeopzloc"] = "gemeenten"

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

        # Chercher les lignes de résultats dans le tableau
        result_table = soup.find("table", {"id": "result"}) or soup.find(
            "table", class_="list"
        )

        if not result_table:
            # Essayer de trouver les résultats dans des divs ou lignes alternées
            result_rows = soup.find_all("tr", class_=re.compile(r"odd|even"))
            if not result_rows:
                # Essayer avec les liens vers les entreprises
                result_rows = soup.find_all("div", class_=re.compile(r"result"))

            for row in result_rows:
                prof = self._parse_result_row(row)
                if prof:
                    professionals.append(prof)
            return professionals

        rows = result_table.find_all("tr")
        for row in rows[1:]:  # Skip header
            prof = self._parse_result_row(row)
            if prof:
                professionals.append(prof)

        return professionals

    def _parse_result_row(self, element) -> Professional | None:
        """Parse une ligne de résultat."""
        try:
            cells = element.find_all("td")
            if len(cells) < 2:
                link = element.find("a")
                name_text = link.get_text(strip=True) if link else ""
                if not name_text:
                    return None

                prof = Professional(nom=name_text, sources="KBO")

                text = element.get_text()
                bce_match = re.search(r"(\d{4}[\.\s]?\d{3}[\.\s]?\d{3})", text)
                if bce_match:
                    prof.numero_bce = bce_match.group(1).replace(" ", ".").strip()

                return prof

            # Format tableau standard
            name_cell = cells[0]
            link = name_cell.find("a")
            name = link.get_text(strip=True) if link else name_cell.get_text(strip=True)

            if not name:
                return None

            prof = Professional(nom=name, sources="KBO")

            # Numéro BCE
            if len(cells) > 1:
                bce_text = cells[1].get_text(strip=True)
                bce_match = re.search(r"(\d{4}[\.\s]?\d{3}[\.\s]?\d{3})", bce_text)
                if bce_match:
                    prof.numero_bce = bce_match.group(1)

            # Adresse
            if len(cells) > 2:
                addr_text = cells[2].get_text(strip=True)
                prof.adresse = addr_text
                cp_match = re.search(r"(\d{4})\s+(\w+)", addr_text)
                if cp_match:
                    prof.code_postal = cp_match.group(1)
                    prof.ville = cp_match.group(2)

            # Statut
            if len(cells) > 3:
                prof.statut = cells[3].get_text(strip=True)

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
