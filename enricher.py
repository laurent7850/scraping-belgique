"""Pipeline d'enrichissement des données professionnelles.

Combine les données de KBO, Pages d'Or et CBEAPI pour obtenir
des fiches professionnelles les plus complètes possible.
"""

import logging

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from models import Professional
from scrapers.kbo_scraper import KBOScraper
from scrapers.pagesdor_scraper import PagesDorScraper
from scrapers.cbeapi_client import CBEAPIClient
from scrapers.email_enricher import EmailEnricher

logger = logging.getLogger(__name__)


class Enricher:
    """Pipeline d'enrichissement multi-sources."""

    def __init__(
        self,
        use_pagesdor: bool = True,
        use_cbeapi: bool = True,
        use_deep_email: bool = False,
    ):
        self.kbo = KBOScraper()
        self.pagesdor = PagesDorScraper() if use_pagesdor else None
        self.cbeapi = CBEAPIClient() if use_cbeapi else None
        self.email_enricher = EmailEnricher() if use_deep_email else None
        self.stats = {
            "total": 0,
            "enriched_pagesdor": 0,
            "enriched_cbeapi": 0,
            "enriched_email": 0,
            "with_phone": 0,
            "with_email": 0,
            "with_website": 0,
        }

    def search_and_enrich(
        self,
        keyword: str,
        pagesdor_keyword: str = "",
        nace_code: str = "",
        location: str = "",
        max_results: int = 100,
    ) -> list[Professional]:
        """Recherche et enrichit les professionnels.

        Étapes :
        1. Recherche KBO (par NACE ou mot-clé)
        2. Recherche Pages d'Or en parallèle
        3. Fusion des résultats
        4. Enrichissement CBEAPI pour les données manquantes

        Args:
            keyword: Mot-clé de recherche
            pagesdor_keyword: Mot-clé spécifique pour Pages d'Or
            nace_code: Code NACE pour la recherche KBO
            location: Ville ou code postal
            max_results: Nombre max de résultats

        Returns:
            Liste de Professional enrichis
        """
        all_professionals = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:

            # Étape 1 : Recherche KBO
            task_kbo = progress.add_task("Recherche KBO/BCE...", total=None)
            kbo_results = self._search_kbo(keyword, nace_code, location, max_results)
            progress.update(task_kbo, completed=True, total=1, description=f"KBO: {len(kbo_results)} résultats")

            # Étape 2 : Recherche Pages d'Or
            pagesdor_results = []
            if self.pagesdor:
                task_pd = progress.add_task("Recherche Pages d'Or...", total=None)
                pd_keyword = pagesdor_keyword or keyword
                pagesdor_results = self.pagesdor.search(pd_keyword, location, max_results)
                progress.update(task_pd, completed=True, total=1, description=f"Pages d'Or: {len(pagesdor_results)} résultats")

            # Étape 3 : Fusion
            task_merge = progress.add_task("Fusion des données...", total=None)
            all_professionals = self._merge_results(kbo_results, pagesdor_results)
            progress.update(task_merge, completed=True, total=1, description=f"Fusionné: {len(all_professionals)} professionnels")

            # Étape 4 : Enrichissement CBEAPI pour les données manquantes
            if self.cbeapi:
                incomplete = [p for p in all_professionals if not p.has_contact]
                if incomplete:
                    task_cbe = progress.add_task(
                        "Enrichissement CBEAPI...",
                        total=len(incomplete),
                    )
                    for i, prof in enumerate(incomplete):
                        self.cbeapi.enrich_professional(prof)
                        if prof.has_contact:
                            self.stats["enriched_cbeapi"] += 1
                        progress.update(task_cbe, advance=1)

            # Étape 5 : Enrichissement email approfondi (Pages d'Or détail + site web + Google)
            if self.email_enricher:
                no_email = [p for p in all_professionals if not p.email]
                if no_email:
                    task_email = progress.add_task(
                        "Enrichissement email...",
                        total=len(no_email),
                    )
                    for prof in no_email:
                        had_email = bool(prof.email)
                        self.email_enricher.enrich_emails([prof])
                        if prof.email and not had_email:
                            self.stats["enriched_email"] += 1
                        progress.update(task_email, advance=1)

        # Calculer les stats finales
        self._compute_stats(all_professionals)

        return all_professionals[:max_results]

    def _search_kbo(
        self, keyword: str, nace_code: str, location: str, max_results: int
    ) -> list[Professional]:
        """Recherche dans la base KBO.

        Tente d'abord par NACE, puis fallback par mot-clé.
        """
        results = []

        if nace_code:
            results = self.kbo.search_by_nace(nace_code, location, max_results)

        # Fallback par mot-clé si NACE n'a rien donné
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
        """Fusionne les résultats KBO et Pages d'Or.

        Stratégie :
        - Commence avec tous les résultats KBO
        - Pour chaque résultat Pages d'Or, cherche un match dans KBO
        - Si match trouvé, fusionne les données
        - Si pas de match, ajoute comme nouvel enregistrement
        """
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
        # Match par numéro BCE
        if prof1.numero_bce and prof2.numero_bce:
            bce1 = prof1.numero_bce.replace(".", "").replace(" ", "")
            bce2 = prof2.numero_bce.replace(".", "").replace(" ", "")
            if bce1 == bce2:
                return True

        # Match par nom + code postal
        name1 = prof1.nom.lower().strip()
        name2 = prof2.nom.lower().strip()

        if not name1 or not name2:
            return False

        name_match = name1 == name2 or name1 in name2 or name2 in name1

        if name_match:
            # Si les codes postaux correspondent aussi, c'est un match fort
            if prof1.code_postal and prof2.code_postal:
                return prof1.code_postal == prof2.code_postal
            # Sinon, match par nom seul si assez similaire
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
        """Retourne les statistiques détaillées de l'enrichissement email."""
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
