# Scrapping

## Description
Service de web scraping (codes NACE, données entreprises).

## Stack
- **Langage** : Python 3
- **Web** : Flask + Gunicorn
- **Scraping** : BeautifulSoup4, Requests
- **Data** : Pandas
- **Déploiement** : Docker

## Structure
- `main.py` — Point d'entrée
- `scrapers/` — Modules de scraping
- `models.py` — Modèles de données
- `exporter.py` — Export des résultats
- `config.py` — Configuration

## Commandes
```bash
python main.py               # Lancer localement
docker compose up -d          # Via Docker
```
