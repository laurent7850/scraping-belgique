"""Gestionnaire de jobs de scraping en background."""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models import Professional
from exporter import export_csv
from nace_codes import find_profession
from nace_codes_fr import find_profession_fr
from web.web_enricher import WebEnricher
from web.web_enricher_fr import WebEnricherFR

logger = logging.getLogger(__name__)

# Durée de vie max d'un job en secondes (1h)
JOB_TTL = 3600


@dataclass
class Job:
    """Représente un job de scraping."""

    id: str = ""
    status: str = "pending"  # pending | running | completed | error
    country: str = "BE"  # "BE" ou "FR"
    profession: str = ""
    location: str = ""
    max_results: int = 100
    use_enrich: bool = True
    use_deep_email: bool = False

    # Progression
    progress: list = field(default_factory=list)
    current_step: str = ""
    current_progress: int = 0
    current_total: int = 0

    # Résultats
    results: list = field(default_factory=list)
    csv_path: str = ""
    stats: dict = field(default_factory=dict)
    email_stats: dict = field(default_factory=dict)
    error: str = ""

    # Métadonnées
    created_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "country": self.country,
            "profession": self.profession,
            "location": self.location,
            "max_results": self.max_results,
            "current_step": self.current_step,
            "current_progress": self.current_progress,
            "current_total": self.current_total,
            "stats": self.stats,
            "email_stats": self.email_stats,
            "csv_path": self.csv_path,
            "error": self.error,
            "result_count": len(self.results),
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class JobManager:
    """Gère les jobs de scraping en background."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        profession: str,
        location: str = "",
        max_results: int = 100,
        use_enrich: bool = True,
        use_deep_email: bool = False,
        country: str = "BE",
    ) -> str:
        """Crée et lance un nouveau job. Retourne le job_id."""
        job_id = str(uuid.uuid4())[:8]

        job = Job(
            id=job_id,
            country=country,
            profession=profession,
            location=location,
            max_results=max_results,
            use_enrich=use_enrich,
            use_deep_email=use_deep_email,
            created_at=time.time(),
        )

        with self._lock:
            self._jobs[job_id] = job

        # Lancer le thread
        thread = threading.Thread(
            target=self._run_job,
            args=(job,),
            daemon=True,
        )
        thread.start()

        # Nettoyer les vieux jobs
        self._cleanup_old_jobs()

        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def _run_job(self, job: Job):
        """Exécute le job de scraping dans un thread."""
        job.status = "running"

        if job.country == "FR":
            self._run_job_fr(job)
        else:
            self._run_job_be(job)

    def _make_progress_callback(self, job: Job):
        """Crée un callback de progression pour un job."""
        def progress_callback(step: str, current: int, total: int, message: str):
            job.current_step = step
            job.current_progress = current
            job.current_total = total
            job.progress.append({
                "step": step,
                "current": current,
                "total": total,
                "message": message,
                "timestamp": time.time(),
            })
        return progress_callback

    def _run_job_be(self, job: Job):
        """Exécute un job Belgique."""
        keyword = ""
        pagesdor_keyword = ""
        nace_code = ""
        profession_name = job.profession

        matches = find_profession(job.profession)
        if matches:
            match = matches[0]
            keyword = match["description"]
            pagesdor_keyword = match["pagesdor_keyword"]
            nace_code = match["nace"]
            profession_name = match["description"]
        else:
            keyword = job.profession

        progress_callback = self._make_progress_callback(job)

        enricher = WebEnricher(
            use_pagesdor=job.use_enrich,
            use_cbeapi=job.use_enrich,
            use_deep_email=job.use_deep_email,
            progress_callback=progress_callback,
        )

        try:
            professionals = enricher.search_and_enrich(
                keyword=keyword,
                pagesdor_keyword=pagesdor_keyword,
                nace_code=nace_code,
                location=job.location,
                max_results=job.max_results,
            )

            self._finalize_job(job, enricher, professionals, profession_name, "BE")

        except Exception as e:
            logger.exception(f"Job {job.id} failed: {e}")
            job.status = "error"
            job.error = str(e)
            job.completed_at = time.time()
            progress_callback("error", 0, 0, f"Erreur : {e}")

        finally:
            enricher.close()

    def _run_job_fr(self, job: Job):
        """Exécute un job France."""
        keyword = ""
        pagesjaunes_keyword = ""
        naf_code = ""
        profession_name = job.profession

        matches = find_profession_fr(job.profession)
        if matches:
            match = matches[0]
            keyword = match["description"]
            pagesjaunes_keyword = match.get("pagesjaunes_keyword", "")
            naf_code = match.get("naf", "")
            profession_name = match["description"]
        else:
            keyword = job.profession

        progress_callback = self._make_progress_callback(job)

        enricher = WebEnricherFR(
            use_pagesjaunes=job.use_enrich,
            use_deep_email=job.use_deep_email,
            progress_callback=progress_callback,
        )

        try:
            professionals = enricher.search_and_enrich(
                keyword=keyword,
                pagesjaunes_keyword=pagesjaunes_keyword,
                naf_code=naf_code,
                location=job.location,
                max_results=job.max_results,
            )

            self._finalize_job(job, enricher, professionals, profession_name, "FR")

        except Exception as e:
            logger.exception(f"Job {job.id} failed: {e}")
            job.status = "error"
            job.error = str(e)
            job.completed_at = time.time()
            progress_callback("error", 0, 0, f"Erreur : {e}")

        finally:
            enricher.close()

    def _finalize_job(self, job: Job, enricher, professionals, profession_name, country):
        """Finalise un job (commun BE/FR)."""
        progress_callback = self._make_progress_callback(job)

        if not professionals:
            job.status = "completed"
            job.stats = enricher.get_stats()
            job.completed_at = time.time()
            progress_callback("done", 1, 1, "Aucun résultat trouvé.")
            return

        for prof in professionals:
            if not prof.profession:
                prof.profession = profession_name

        csv_path = export_csv(
            professionals,
            profession_name=profession_name,
            location=job.location,
            country=country,
        )

        job.results = professionals
        job.csv_path = csv_path
        job.stats = enricher.get_stats()
        job.email_stats = enricher.get_email_stats()
        job.status = "completed"
        job.completed_at = time.time()

        progress_callback(
            "done", 1, 1,
            f"Terminé ! {len(professionals)} professionnels trouvés."
        )

    def _cleanup_old_jobs(self):
        """Supprime les jobs de plus d'1h."""
        now = time.time()
        with self._lock:
            expired = [
                jid for jid, job in self._jobs.items()
                if now - job.created_at > JOB_TTL
            ]
            for jid in expired:
                del self._jobs[jid]
