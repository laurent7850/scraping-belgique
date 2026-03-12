"""Enricher France — pipeline API Entreprises + Pages Jaunes + Email."""

import logging
from typing import Callable, Optional

from models import Professional
from scrapers.entreprises_api_client import EntreprisesAPIClient
from scrapers.pagesjaunes_scraper import PagesJaunesScraper
from scrapers.email_enricher import EmailEnricher

logger = logging.getLogger(__name__)

# Type du callback : fn(step, current, total, message)
ProgressCallback = Callable[[str, int, int, str], None]


class WebEnricherFR:
    """Pipeline d'enrichissement France (4 étapes).

    1. API Entreprises gouv.fr
    2. Pages Jaunes
    3. Fusion
    4. Email (optionnel)
    """

    def __init__(
        self,
        use_pagesjaunes: bool = True,
        use_deep_email: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.entreprises_api = EntreprisesAPIClient()
        self.pagesjaunes = PagesJaunesScraper() if use_pagesjaunes else None
        self.email_enricher = EmailEnricher(
            use_pagesdor_detail=False,
            use_website_crawl=True,
            use_google_search=True,
            country="FR",
        ) if use_deep_email else None
        self.progress_callback = progress_callback or (lambda *a: None)
        self.stats = {
            "total": 0,
            "enriched_pagesjaunes": 0,
            "enriched_email": 0,
            "with_phone": 0,
            "with_email": 0,
            "with_website": 0,
        }

    def _notify(self, step: str, current: int, total: int, message: str):
        try:
            self.progress_callback(step, current, total, message)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    def search_and_enrich(
        self,
        keyword: str,
        pagesjaunes_keyword: str = "",
        naf_code: str = "",
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche et enrichit les professionnels français."""

        # Étape 1 : Recherche API Entreprises
        self._notify("entreprises_api", 0, 1, "Recherche API Entreprises en cours...")
        api_results = self.entreprises_api.search(keyword, naf_code, location, max_results)
        self._notify("entreprises_api", 1, 1, f"API Entreprises : {len(api_results)} résultats trouvés")

        # Étape 2 : Recherche Pages Jaunes
        pj_results = []
        if self.pagesjaunes:
            self._notify("pagesjaunes", 0, 1, "Recherche Pages Jaunes en cours...")
            pj_keyword = pagesjaunes_keyword or keyword
            pj_results = self.pagesjaunes.search(pj_keyword, location, max_results)
            self._notify("pagesjaunes", 1, 1, f"Pages Jaunes : {len(pj_results)} résultats trouvés")
        else:
            self._notify("pagesjaunes", 1, 1, "Pages Jaunes : désactivé")

        # Étape 3 : Fusion
        self._notify("fusion", 0, 1, "Fusion des données...")
        all_professionals = self._merge_results(api_results, pj_results)
        self._notify("fusion", 1, 1, f"Fusion : {len(all_professionals)} professionnels uniques")

        # Étape 4 : Enrichissement email approfondi
        if self.email_enricher:
            no_email = [p for p in all_professionals if not p.email]
            total_email = len(no_email)
            if total_email > 0:
                self._notify("email", 0, total_email, f"Enrichissement email ({total_email} sans email)...")
                for i, prof in enumerate(no_email):
                    had_email = bool(prof.email)
                    self.email_enricher.enrich_emails([prof])
                    if prof.email and not had_email:
                        self.stats["enriched_email"] += 1
                    self._notify("email", i + 1, total_email, f"Email : {i + 1}/{total_email}")
            else:
                self._notify("email", 1, 1, "Email : tous les professionnels ont déjà un email")
        else:
            self._notify("email", 1, 1, "Enrichissement email : désactivé")

        # Stats finales
        self._compute_stats(all_professionals)
        return all_professionals[:max_results]

    def _merge_results(
        self,
        api_results: list[Professional],
        pj_results: list[Professional],
    ) -> list[Professional]:
        """Fusionne les résultats API Entreprises et Pages Jaunes."""
        merged = list(api_results)
        used_indices = set()

        for pj_prof in pj_results:
            matched = False
            for i, api_prof in enumerate(merged):
                if i in used_indices:
                    continue
                if self._is_match(api_prof, pj_prof):
                    api_prof.merge(pj_prof)
                    self.stats["enriched_pagesjaunes"] += 1
                    used_indices.add(i)
                    matched = True
                    break
            if not matched:
                merged.append(pj_prof)

        return merged

    def _is_match(self, prof1: Professional, prof2: Professional) -> bool:
        """Vérifie si deux professionnels sont la même entité."""
        # Match par SIREN
        if prof1.numero_entreprise and prof2.numero_entreprise:
            siren1 = prof1.numero_entreprise.replace(" ", "")[:9]
            siren2 = prof2.numero_entreprise.replace(" ", "")[:9]
            if siren1 == siren2:
                return True

        # Match par nom + code postal
        name1 = prof1.nom.lower().strip()
        name2 = prof2.nom.lower().strip()
        if not name1 or not name2:
            return False

        name_match = name1 == name2 or name1 in name2 or name2 in name1
        if name_match:
            if prof1.code_postal and prof2.code_postal:
                return prof1.code_postal == prof2.code_postal
            return name1 == name2

        return False

    def _compute_stats(self, professionals: list[Professional]):
        self.stats["total"] = len(professionals)
        self.stats["with_phone"] = sum(1 for p in professionals if p.telephone)
        self.stats["with_email"] = sum(1 for p in professionals if p.email)
        self.stats["with_website"] = sum(1 for p in professionals if p.site_web)

    def get_stats(self) -> dict:
        return self.stats.copy()

    def get_email_stats(self) -> dict:
        if self.email_enricher:
            return self.email_enricher.get_stats()
        return {}

    def close(self):
        self.entreprises_api.close()
        if self.pagesjaunes:
            self.pagesjaunes.close()
        if self.email_enricher:
            self.email_enricher.close()
