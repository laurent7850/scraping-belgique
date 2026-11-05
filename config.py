"""Configuration globale de l'outil de scraping."""

import os
import random

# --- Chemins ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# --- Rate Limiting ---
# Délai entre les requêtes (en secondes)
PAGESDOR_DELAY_MIN = 2.0
PAGESDOR_DELAY_MAX = 5.0
KBO_DELAY_MIN = 1.0
KBO_DELAY_MAX = 3.0
CBEAPI_DAILY_LIMIT = 2500

# France
PAGESJAUNES_DELAY_MIN = 2.0
PAGESJAUNES_DELAY_MAX = 5.0
ENTREPRISES_API_DELAY_MIN = 0.3
ENTREPRISES_API_DELAY_MAX = 1.0

# Enrichissement email (délais supplémentaires)
WEBSITE_CRAWL_DELAY_MIN = 0.5
WEBSITE_CRAWL_DELAY_MAX = 1.5
WEBSITE_CRAWL_TIMEOUT = 6  # secondes
GOOGLE_SEARCH_DELAY_MIN = 2.0
GOOGLE_SEARCH_DELAY_MAX = 4.0
GOOGLE_MAPS_DELAY_MIN = 1.0
GOOGLE_MAPS_DELAY_MAX = 2.5

# --- URLs Belgique ---
KBO_SEARCH_URL = "https://kbopub.economie.fgov.be/kbopub/zoeknummerform.html"
KBO_RESULT_URL = "https://kbopub.economie.fgov.be/kbopub/zoekwoordenform.html"
PAGESDOR_BASE_URL = "https://www.pagesdor.be"
PAGESDOR_SEARCH_URL = "https://www.pagesdor.be/trouvez/{keyword}/{location}/"
CBEAPI_BASE_URL = "https://cbeapi.be/api/v1"

# --- URLs France ---
ENTREPRISES_API_URL = "https://recherche-entreprises.api.gouv.fr/search"
PAGESJAUNES_BASE_URL = "https://www.pagesjaunes.fr"

# --- CBEAPI Credentials ---
CBEAPI_APP_ID = os.getenv("CBEAPI_APP_ID", "")
CBEAPI_SECRET = os.getenv("CBEAPI_SECRET", "")

# --- Résultats ---
DEFAULT_MAX_RESULTS = 100
DEFAULT_PAGE_SIZE = 20

# --- Régions/Provinces ---
BELGIAN_PROVINCES = [
    "Bruxelles", "Brabant wallon", "Brabant flamand",
    "Hainaut", "Liège", "Luxembourg", "Namur",
    "Anvers", "Flandre occidentale", "Flandre orientale", "Limbourg",
]

FRENCH_REGIONS = [
    "Île-de-France", "Auvergne-Rhône-Alpes", "Nouvelle-Aquitaine",
    "Occitanie", "Hauts-de-France", "Provence-Alpes-Côte d'Azur",
    "Grand Est", "Pays de la Loire", "Bretagne", "Normandie",
    "Bourgogne-Franche-Comté", "Centre-Val de Loire", "Corse",
]

# --- User Agents ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)


def get_headers(country: str = "BE") -> dict:
    lang = "fr-BE,fr;q=0.9,en;q=0.5" if country == "BE" else "fr-FR,fr;q=0.9,en;q=0.5"
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": lang,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }


def get_random_delay(source: str = "pagesdor") -> float:
    if source == "pagesdor":
        return random.uniform(PAGESDOR_DELAY_MIN, PAGESDOR_DELAY_MAX)
    elif source == "kbo":
        return random.uniform(KBO_DELAY_MIN, KBO_DELAY_MAX)
    elif source == "pagesjaunes":
        return random.uniform(PAGESJAUNES_DELAY_MIN, PAGESJAUNES_DELAY_MAX)
    elif source == "entreprises_api":
        return random.uniform(ENTREPRISES_API_DELAY_MIN, ENTREPRISES_API_DELAY_MAX)
    elif source == "website":
        return random.uniform(WEBSITE_CRAWL_DELAY_MIN, WEBSITE_CRAWL_DELAY_MAX)
    elif source == "google":
        return random.uniform(GOOGLE_SEARCH_DELAY_MIN, GOOGLE_SEARCH_DELAY_MAX)
    elif source == "google_maps":
        return random.uniform(GOOGLE_MAPS_DELAY_MIN, GOOGLE_MAPS_DELAY_MAX)
    return random.uniform(1.0, 2.0)
