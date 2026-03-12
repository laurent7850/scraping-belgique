"""Client pour l'API Recherche Entreprises (gouv.fr).

API REST gratuite, sans authentification.
Documentation : https://recherche-entreprises.api.gouv.fr/docs/
"""

import time
import logging

import requests

from config import ENTREPRISES_API_URL, get_random_delay
from models import Professional

logger = logging.getLogger(__name__)


class EntreprisesAPIClient:
    """Client pour l'API Recherche Entreprises du gouvernement français."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ScrapingProfessions/1.0",
        })

    def search(
        self,
        keyword: str,
        naf_code: str = "",
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche des entreprises via l'API gouv.fr.

        Args:
            keyword: Mot-clé de recherche (ex: "plombier")
            naf_code: Code NAF pour filtrer (ex: "43.22A")
            location: Ville ou code postal
            max_results: Nombre max de résultats

        Returns:
            Liste de Professional
        """
        results = []
        page = 1
        per_page = min(25, max_results)  # API max 25 par page

        while len(results) < max_results:
            try:
                params = {
                    "q": keyword,
                    "per_page": per_page,
                    "page": page,
                }

                # Filtrer par code postal ou département
                if location:
                    location_clean = location.strip()
                    if location_clean.isdigit():
                        if len(location_clean) == 5:
                            params["code_postal"] = location_clean
                        elif len(location_clean) == 2 or (len(location_clean) == 3 and location_clean.startswith("97")):
                            params["departement"] = location_clean
                    else:
                        # Ajouter le nom de ville à la requête
                        params["q"] = f"{keyword} {location_clean}"

                # Filtrer par code NAF
                if naf_code:
                    params["activite_principale"] = naf_code

                # Ne chercher que les entreprises actives
                params["etat_administratif"] = "A"

                logger.info(f"API Entreprises: page {page} - {keyword} {location}")
                time.sleep(get_random_delay("entreprises_api"))

                resp = self.session.get(ENTREPRISES_API_URL, params=params, timeout=15)

                if resp.status_code == 429:
                    logger.warning("API Entreprises: Rate limit, pause 5s")
                    time.sleep(5)
                    continue

                if resp.status_code != 200:
                    logger.warning(f"API Entreprises: HTTP {resp.status_code}")
                    break

                data = resp.json()
                entreprises = data.get("results", [])

                if not entreprises:
                    logger.info("API Entreprises: Plus de résultats")
                    break

                for ent in entreprises:
                    prof = self._parse_entreprise(ent)
                    if prof:
                        results.append(prof)

                total_available = data.get("total_results", 0)
                logger.info(f"API Entreprises: Page {page} - {len(entreprises)} résultats (total dispo: {total_available})")

                if len(entreprises) < per_page:
                    break

                page += 1

            except Exception as e:
                logger.error(f"API Entreprises: Erreur page {page}: {e}")
                break

        return results[:max_results]

    def get_by_siren(self, siren: str) -> Professional | None:
        """Récupère une entreprise par son SIREN."""
        try:
            time.sleep(get_random_delay("entreprises_api"))
            resp = self.session.get(
                ENTREPRISES_API_URL,
                params={"q": siren, "per_page": 1},
                timeout=15,
            )

            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", [])
            if results:
                return self._parse_entreprise(results[0])

        except Exception as e:
            logger.error(f"API Entreprises get_by_siren: {e}")

        return None

    def _parse_entreprise(self, ent: dict) -> Professional | None:
        """Convertit une entrée API en Professional."""
        nom = ent.get("nom_complet", "")
        if not nom:
            return None

        prof = Professional(
            nom=nom,
            pays="FR",
            sources="APIEntreprises",
        )

        # SIREN
        siren = ent.get("siren", "")
        if siren:
            prof.numero_entreprise = siren

        # Siège social
        siege = ent.get("siege", {})
        if siege:
            # Adresse
            adresse_parts = []
            numero_voie = siege.get("numero_voie", "")
            type_voie = siege.get("type_voie", "")
            libelle_voie = siege.get("libelle_voie", "")
            if numero_voie:
                adresse_parts.append(numero_voie)
            if type_voie:
                adresse_parts.append(type_voie)
            if libelle_voie:
                adresse_parts.append(libelle_voie)
            prof.adresse = " ".join(adresse_parts)

            prof.code_postal = siege.get("code_postal", "")
            prof.ville = siege.get("libelle_commune", "")

            # Région
            region = siege.get("region", "")
            if region:
                prof.province = region

        # Activité principale
        activite = ent.get("activite_principale", "")
        if activite:
            prof.code_nace = activite

        # Nature juridique
        nature_juridique = ent.get("nature_juridique", "")
        if nature_juridique:
            prof.forme_juridique = nature_juridique

        # Statut
        etat = ent.get("etat_administratif", "")
        if etat == "A":
            prof.statut = "Active"
        elif etat == "C":
            prof.statut = "Cessée"

        return prof

    def close(self):
        self.session.close()
