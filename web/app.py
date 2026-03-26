"""Application Flask pour le scraping des professions (Belgique + France)."""

import json
import os
import sys
import time
import logging

from flask import Flask, render_template, request, jsonify, Response, send_file

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nace_codes import NACE_CATEGORIES, list_all_professions
from nace_codes_fr import NACE_CATEGORIES_FR, list_all_professions_fr
from config import BELGIAN_PROVINCES, FRENCH_REGIONS
from web.job_manager import JobManager

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Crée l'application Flask."""
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )
    app.config["SECRET_KEY"] = "scraping-pro-2026"

    # Gestionnaire de jobs partagé
    job_manager = JobManager()

    # --- Routes ---

    @app.route("/")
    def index():
        """Page principale."""
        return render_template(
            "index.html",
            categories_be=NACE_CATEGORIES,
            categories_fr=NACE_CATEGORIES_FR,
            provinces_be=BELGIAN_PROVINCES,
            regions_fr=FRENCH_REGIONS,
        )

    @app.route("/api/professions")
    @app.route("/api/professions/<country>")
    def api_professions(country="BE"):
        """Liste des professions pour l'autocomplétion."""
        if country == "FR":
            professions = list_all_professions_fr()
        else:
            professions = list_all_professions()
        return jsonify(professions)

    @app.route("/api/search", methods=["POST"])
    def api_search():
        """Lance une recherche de scraping."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "Données manquantes"}), 400

        profession = data.get("profession", "").strip()
        if not profession:
            return jsonify({"error": "Profession requise"}), 400

        location = data.get("location", "").strip()
        max_results = min(int(data.get("max_results", 100)), 500)
        use_enrich = data.get("use_enrich", True)
        use_deep_email = data.get("use_deep_email", False)
        country = data.get("country", "BE").upper()
        if country not in ("BE", "FR"):
            country = "BE"

        job_id = job_manager.create_job(
            profession=profession,
            location=location,
            max_results=max_results,
            use_enrich=use_enrich,
            use_deep_email=use_deep_email,
            country=country,
        )

        return jsonify({"job_id": job_id})

    @app.route("/api/progress/<job_id>")
    def api_progress(job_id: str):
        """SSE stream de progression du job."""

        def generate():
            last_index = 0

            while True:
                job = job_manager.get_job(job_id)
                if not job:
                    yield f"data: {json.dumps({'error': 'Job introuvable'})}\n\n"
                    break

                # Envoyer les nouvelles entrées de progression
                new_entries = job.progress[last_index:]
                for entry in new_entries:
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                last_index = len(job.progress)

                # Si terminé, envoyer le statut final
                if job.status in ("completed", "error"):
                    final = {
                        "status": job.status,
                        "stats": job.stats,
                        "email_stats": job.email_stats,
                        "result_count": len(job.results),
                        "error": job.error,
                    }
                    yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"
                    break

                time.sleep(0.5)

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.route("/api/results/<job_id>")
    def api_results(job_id: str):
        """Retourne les résultats JSON d'un job terminé."""
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job introuvable"}), 404

        if job.status != "completed":
            return jsonify({"error": "Job pas encore terminé", "status": job.status}), 202

        results = []
        for prof in job.results:
            results.append(prof.to_dict())

        return jsonify({
            "results": results,
            "stats": job.stats,
            "email_stats": job.email_stats,
            "csv_path": job.csv_path,
        })

    @app.route("/api/download/<job_id>")
    def api_download(job_id: str):
        """Télécharge le fichier CSV d'un job."""
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job introuvable"}), 404

        if not job.csv_path or not os.path.exists(job.csv_path):
            return jsonify({"error": "Fichier CSV non disponible"}), 404

        return send_file(
            job.csv_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name=os.path.basename(job.csv_path),
        )

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
