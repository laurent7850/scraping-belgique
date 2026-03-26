"""Enricher adapté pour le web — remplace rich.progress par un callback."""

import logging
from typing import Callable, Optional

from models import Professional
from location_utils import resolve_location, filter_by_location
from scrapers.kbo_scraper import KBOScraper
from scrapers.pagesdor_scraper import PagesDorScraper
from scrapers.cbeapi_client import CBEAPIClient
from scrapers.email_enricher import EmailEnricher

logger = logging.getLogger(__name__)

# Type du callback : fn(step, current, total, message)
ProgressCallback = Callable[[str, int, int, str], None]


class WebEnricher:
    """Pipeline d'enrichissement multi-sources pour le contexte web.

    Similaire à Enricher mais utilise un callback au lieu de rich.progress.
    """

    def __init__(
        self,
        use_pagesdor: bool = True,
        use_cbeapi: bool = True,
        use_deep_email: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
    ):
        self.kbo = KBOScraper()
        self.pagesdor = PagesDorScraper() if use_pagesdor else None
        self.cbeapi = CBEAPIClient() if use_cbeapi else None
        self.email_enricher = EmailEnricher() if use_deep_email else None
        self.progress_callback = progress_callback or (lambda *a: None)
        self.stats = {
            "total": 0,
            "enriched_pagesdor": 0,
            "enriched_cbeapi": 0,
            "enriched_email": 0,
            "with_phone": 0,
            "with_email": 0,
            "with_website": 0,
        }

    def _notify(self, step: str, current: int, total: int, message: str):
        """Envoie une notification de progression."""
        try:
            self.progress_callback(step, current, total, message)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    def search_and_enrich(
        self,
        keyword: str,
        pagesdor_keyword: str = "",
        nace_code: str = "",
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche et enrichit les professionnels (version web)."""
        all_professionals = []

        # Étape 1 : Recherche KBO
        self._notify("kbo", 0, 1, "Recherche KBO/BCE en cours...")
        kbo_results = self._search_kbo(keyword, nace_code, location, max_results)
        self._notify("kbo", 1, 1, f"KBO : {len(kbo_results)} résultats trouvés")

        # Étape 2 : Recherche Pages d'Or
        pagesdor_results = []
        if self.pagesdor:
            self._notify("pagesdor", 0, 1, "Recherche Pages d'Or en cours...")
            pd_keyword = pagesdor_keyword or keyword
            pagesdor_results = self.pagesdor.search(pd_keyword, location, max_results)
            self._notify("pagesdor", 1, 1, f"Pages d'Or : {len(pagesdor_results)} résultats trouvés")
        else:
            self._notify("pagesdor", 1, 1, "Pages d'Or : désactivé")

        # Étape 3 : Fusion
        self._notify("fusion", 0, 1, "Fusion des données...")
        all_professionals = self._merge_results(kbo_results, pagesdor_results)
        self._notify("fusion", 1, 1, f"Fusion : {len(all_professionals)} professionnels uniques")

        # Étape 3b : Filtrage par localisation
        if location:
            _, postal_codes = resolve_location(location)
            if postal_codes:
                before = len(all_professionals)
                all_professionals = filter_by_location(all_professionals, location, postal_codes)
                removed = before - len(all_professionals)
                if removed > 0:
                    self._notify("fusion", 1, 1, f"Filtrage : {removed} résultats hors '{location}' supprimés")
                    logger.info(f"Location filter: removed {removed} results outside '{location}'")

        # Étape 4 : Enrichissement CBEAPI
        if self.cbeapi:
            incomplete = [p for p in all_professionals if not p.has_contact]
            total_cbe = len(incomplete)
            if total_cbe > 0:
                self._notify("cbeapi", 0, total_cbe, f"Enrichissement CBEAPI ({total_cbe} sans contact)...")
                for i, prof in enumerate(incomplete):
                    self.cbeapi.enrich_professional(prof)
                    if prof.has_contact:
                        self.stats["enriched_cbeapi"] += 1
                    self._notify("cbeapi", i + 1, total_cbe, f"CBEAPI : {i + 1}/{total_cbe}")
            else:
                self._notify("cbeapi", 1, 1, "CBEAPI : tous les professionnels ont déjà un contact")
        else:
            self._notify("cbeapi", 1, 1, "CBEAPI : désactivé")

        # Étape 5 : Enrichissement email approfondi
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

    def _search_kbo(
        self, keyword: str, nace_code: str, location: str, max_results: int
    ) -> list[Professional]:
        """Recherche dans la base KBO."""
        results = []
        if nace_code:
            results = self.kbo.search_by_nace(nace_code, location, max_results)
        if not results and keyword:
            results = self.kbo.search_by_keyword(keyword, location, max_results)
        for prof in results:
            if nace_code:
                prof.code_nace = nace_code
        return results

    def _merge_results(
        self,
        kbo_results: list[Professional],
        pagesdor_results: list[Professional],
    ) -> list[Professional]:
        """Fusionne les résultats KBO et Pages d'Or."""
        merged = list(kbo_results)
        used_indices = set()

        for pd_prof in pagesdor_results:
            matched = False
            for i, kbo_prof in enumerate(merged):
                if i in used_indices:
                    continue
                if self._is_match(kbo_prof, pd_prof):
                    kbo_prof.merge(pd_prof)
                    self.stats["enriched_pagesdor"] += 1
                    used_indices.add(i)
                    matched = True
                    break
            if not matched:
                merged.append(pd_prof)

        return merged

    def _is_match(self, prof1: Professional, prof2: Professional) -> bool:
        """Vérifie si deux professionnels sont probablement la même entité."""
        if prof1.numero_bce and prof2.numero_bce:
            bce1 = prof1.numero_bce.replace(".", "").replace(" ", "")
            bce2 = prof2.numero_bce.replace(".", "").replace(" ", "")
            if bce1 == bce2:
                return True
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
        """Calcule les statistiques finales."""
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
        self.kbo.close()
        if self.pagesdor:
            self.pagesdor.close()
        if self.cbeapi:
            self.cbeapi.close()
        if self.email_enricher:
            self.email_enricher.close()
