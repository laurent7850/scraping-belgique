"""Client pour l'API CBEAPI.be.

API REST basée sur les données ouvertes KBO/BCE.
Authentification : Bearer token.
Limite : 2500 requêtes/jour.
"""

import logging
import time

import requests

from config import CBEAPI_BASE_URL, CBEAPI_SECRET, get_random_delay
from models import Professional

logger = logging.getLogger(__name__)


class CBEAPIClient:
    """Client pour l'API CBEAPI.be avec authentification Bearer."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {CBEAPI_SECRET}",
            "User-Agent": "BelgianProfessionScraper/1.0",
        })
        self.request_count = 0
        self.daily_limit = 2500

    def search_by_name(self, name: str) -> list[Professional]:
        """Recherche une entreprise par nom.

        Args:
            name: Nom de l'entreprise

        Returns:
            Liste de Professional
        """
        if self.request_count >= self.daily_limit:
            logger.warning("CBEAPI: Limite journalière atteinte (2500 requêtes)")
            return []

        try:
            url = f"{CBEAPI_BASE_URL}/company/search"
            params = {"name": name}

            resp = self.session.get(url, params=params, timeout=10)
            self.request_count += 1

            if resp.status_code == 429:
                logger.warning("CBEAPI: Rate limit atteint, pause de 60s")
                time.sleep(60)
                return []

            if resp.status_code != 200:
                logger.warning(f"CBEAPI: HTTP {resp.status_code} pour '{name}'")
                return []

            data = resp.json()
            return self._parse_results(data)

        except Exception as e:
            logger.error(f"CBEAPI search error: {e}")
            return []

    def get_by_bce(self, bce_number: str) -> Professional | None:
        """Récupère les données d'une entreprise par son numéro BCE.

        Args:
            bce_number: Numéro BCE (format: 0xxx.xxx.xxx ou 0xxxxxxxxx)

        Returns:
            Professional ou None
        """
        if self.request_count >= self.daily_limit:
            logger.warning("CBEAPI: Limite journalière atteinte")
            return None

        # Nettoyer le numéro BCE
        clean = bce_number.replace(".", "").replace(" ", "").strip()
        if len(clean) == 9:
            clean = "0" + clean

        try:
            url = f"{CBEAPI_BASE_URL}/company/{clean}"

            resp = self.session.get(url, timeout=10)
            self.request_count += 1

            if resp.status_code == 429:
                logger.warning("CBEAPI: Rate limit, pause 60s")
                time.sleep(60)
                return None

            if resp.status_code == 404:
                logger.debug(f"CBEAPI: Entreprise {bce_number} non trouvée")
                return None

            if resp.status_code != 200:
                logger.warning(f"CBEAPI: HTTP {resp.status_code}")
                return None

            data = resp.json()
            # L'API retourne { "data": {...} } pour un seul résultat
            company = data.get("data", data)
            return self._parse_company(company)

        except Exception as e:
            logger.error(f"CBEAPI get error: {e}")
            return None

    def enrich_professional(self, prof: Professional) -> Professional:
        """Enrichit un Professional avec les données CBEAPI.

        Cherche par numéro BCE si disponible, sinon par nom.
        """
        result = None

        if prof.numero_bce:
            result = self.get_by_bce(prof.numero_bce)
        elif prof.nom:
            results = self.search_by_name(prof.nom)
            if results:
                result = self._find_best_match(prof, results)

        if result:
            prof.merge(result)
            logger.debug(f"CBEAPI: Enrichi '{prof.nom}'")

        time.sleep(get_random_delay("cbeapi"))
        return prof

    def _parse_results(self, data) -> list[Professional]:
        """Parse les résultats de recherche CBEAPI.

        Format réponse : { "data": [ {...}, {...} ] }
        """
        professionals = []

        items = []
        if isinstance(data, dict):
            items = data.get("data", [])
            if isinstance(items, dict):
                items = [items]
        elif isinstance(data, list):
            items = data

        for item in items:
            prof = self._parse_company(item)
            if prof:
                professionals.append(prof)

        return professionals

    def _parse_company(self, data: dict) -> Professional | None:
        """Parse les données d'une entreprise CBEAPI en Professional.

        Structure CBEAPI :
        {
            "cbe_number": "0123456789",
            "cbe_number_formatted": "0123.456.789",
            "denomination": "Nom",
            "address": { "street": "...", "street_number": "...", "post_code": "...", "city": "..." },
            "contact_infos": { "email": null, "phone": null, "web": null },
            "nace_activities": [ { "code": "...", "description": "...", "classification": "main" } ],
            "juridical_form": "...",
            "status": "active",
            "juridical_situation": "..."
        }
        """
        if not isinstance(data, dict):
            return None

        name = (
            data.get("denomination", "")
            or data.get("commercial_name", "")
            or data.get("abbreviation", "")
        )
        if not name:
            return None

        prof = Professional(nom=name, sources="CBEAPI")

        # Numéro BCE
        bce = data.get("cbe_number_formatted", "") or data.get("cbe_number", "")
        if bce:
            prof.numero_bce = str(bce)

        # Adresse
        address = data.get("address", {})
        if isinstance(address, dict):
            street = address.get("street", "")
            number = address.get("street_number", "")
            box = address.get("box", "")
            if street:
                addr_parts = [street]
                if number:
                    addr_parts.append(number)
                if box:
                    addr_parts.append(f"bte {box}")
                prof.adresse = " ".join(addr_parts)

            prof.code_postal = str(address.get("post_code", ""))
            prof.ville = address.get("city", "")

        # Contact
        contact = data.get("contact_infos", {})
        if isinstance(contact, dict):
            prof.telephone = contact.get("phone", "") or ""
            prof.email = contact.get("email", "") or ""
            prof.site_web = contact.get("web", "") or ""

        # Activités NACE
        activities = data.get("nace_activities", [])
        if activities and isinstance(activities, list):
            # Prendre l'activité principale (classification: "main")
            main_act = None
            for act in activities:
                if isinstance(act, dict):
                    if act.get("classification") == "main":
                        main_act = act
                        break
            if not main_act and activities:
                main_act = activities[0]

            if main_act and isinstance(main_act, dict):
                code = main_act.get("code", "")
                # Formater le code NACE (ex: "43221" -> "43.221")
                if code and len(code) >= 4 and "." not in code:
                    code = f"{code[:2]}.{code[2:]}"
                prof.code_nace = code
                prof.description_activite = main_act.get("description", "")

        # Forme juridique
        prof.forme_juridique = data.get("juridical_form", "")

        # Statut
        status = data.get("status", "")
        situation = data.get("juridical_situation", "")
        prof.statut = situation if situation else status

        return prof

    def _find_best_match(
        self, target: Professional, candidates: list[Professional]
    ) -> Professional | None:
        """Trouve la meilleure correspondance."""
        if not candidates:
            return None

        target_name = target.nom.lower().strip()

        for candidate in candidates:
            cand_name = candidate.nom.lower().strip()
            if target_name == cand_name:
                return candidate
            if target_name in cand_name or cand_name in target_name:
                return candidate

        return candidates[0] if candidates else None

    @property
    def remaining_requests(self) -> int:
        return max(0, self.daily_limit - self.request_count)

    def close(self):
        self.session.close()
