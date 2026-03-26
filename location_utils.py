"""Utilities for Belgian and French location handling.

Provides city-to-postal-code mapping and location-based filtering
to ensure scraping results match the requested city.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Major Belgian cities with their postal code ranges
# Format: city_name_lower -> list of postal codes (or ranges)
BELGIAN_CITY_POSTCODES: dict[str, list[str]] = {
    # Bruxelles-Capitale (1000-1299)
    "bruxelles": ["1000", "1020", "1030", "1040", "1050", "1060", "1070", "1080", "1081", "1082", "1083", "1090"],
    "brussels": ["1000", "1020", "1030", "1040", "1050", "1060", "1070", "1080", "1081", "1082", "1083", "1090"],
    "brussel": ["1000", "1020", "1030", "1040", "1050", "1060", "1070", "1080", "1081", "1082", "1083", "1090"],
    "schaerbeek": ["1030"],
    "schaarbeek": ["1030"],
    "etterbeek": ["1040"],
    "ixelles": ["1050"],
    "elsene": ["1050"],
    "saint-gilles": ["1060"],
    "sint-gillis": ["1060"],
    "anderlecht": ["1070"],
    "molenbeek": ["1080"],
    "molenbeek-saint-jean": ["1080"],
    "koekelberg": ["1081"],
    "berchem-sainte-agathe": ["1082"],
    "ganshoren": ["1083"],
    "jette": ["1090"],
    "laeken": ["1020"],
    "neder-over-heembeek": ["1120"],
    "haren": ["1130"],
    "evere": ["1140"],
    "woluwe-saint-pierre": ["1150"],
    "sint-pieters-woluwe": ["1150"],
    "auderghem": ["1160"],
    "oudergem": ["1160"],
    "woluwe-saint-lambert": ["1200"],
    "sint-lambrechts-woluwe": ["1200"],
    "saint-josse-ten-noode": ["1210"],
    "sint-joost-ten-node": ["1210"],
    "uccle": ["1180"],
    "ukkel": ["1180"],
    "watermael-boitsfort": ["1170"],
    "watermaal-bosvoorde": ["1170"],
    "forest": ["1190"],
    "vorst": ["1190"],
    # Brabant wallon
    "wavre": ["1300"],
    "ottignies": ["1340"],
    "ottignies-louvain-la-neuve": ["1340", "1348"],
    "louvain-la-neuve": ["1348"],
    "nivelles": ["1400"],
    "braine-l'alleud": ["1420"],
    "braine-le-comte": ["7090"],
    "waterloo": ["1410"],
    "tubize": ["1480"],
    "rixensart": ["1330"],
    "la hulpe": ["1310"],
    # Brabant flamand
    "leuven": ["3000", "3001", "3010", "3012", "3018"],
    "louvain": ["3000", "3001", "3010", "3012", "3018"],
    "vilvoorde": ["1800"],
    "vilvorde": ["1800"],
    "halle": ["1500"],
    "hal": ["1500"],
    "zaventem": ["1930"],
    "tervuren": ["3080"],
    "tienen": ["3300"],
    "tirlemont": ["3300"],
    "diest": ["3290"],
    "aarschot": ["3200"],
    # Anvers
    "antwerpen": ["2000", "2018", "2020", "2030", "2040", "2050", "2060"],
    "anvers": ["2000", "2018", "2020", "2030", "2040", "2050", "2060"],
    "mechelen": ["2800"],
    "malines": ["2800"],
    "turnhout": ["2300"],
    "lier": ["2500"],
    "herentals": ["2200"],
    "mol": ["2400"],
    "boom": ["2850"],
    "mortsel": ["2640"],
    "schoten": ["2900"],
    "brasschaat": ["2930"],
    "kontich": ["2550"],
    "edegem": ["2650"],
    # Flandre orientale
    "gent": ["9000", "9030", "9040", "9050", "9051", "9052"],
    "gand": ["9000", "9030", "9040", "9050", "9051", "9052"],
    "aalst": ["9300"],
    "alost": ["9300"],
    "sint-niklaas": ["9100"],
    "saint-nicolas": ["9100"],
    "dendermonde": ["9200"],
    "termonde": ["9200"],
    "lokeren": ["9160"],
    "wetteren": ["9230"],
    "zele": ["9240"],
    "geraardsbergen": ["9500"],
    "grammont": ["9500"],
    "eeklo": ["9900"],
    # Flandre occidentale
    "brugge": ["8000", "8200", "8310", "8380"],
    "bruges": ["8000", "8200", "8310", "8380"],
    "oostende": ["8400"],
    "ostende": ["8400"],
    "kortrijk": ["8500"],
    "courtrai": ["8500"],
    "roeselare": ["8800"],
    "roulers": ["8800"],
    "ieper": ["8900"],
    "ypres": ["8900"],
    "knokke-heist": ["8300", "8301"],
    "blankenberge": ["8370"],
    "waregem": ["8790"],
    "torhout": ["8820"],
    # Hainaut
    "mons": ["7000", "7010", "7011", "7012"],
    "bergen": ["7000", "7010", "7011", "7012"],
    "charleroi": ["6000", "6010", "6020", "6030", "6040", "6041", "6042", "6044"],
    "tournai": ["7500"],
    "doornik": ["7500"],
    "la louviere": ["7100"],
    "la louvière": ["7100"],
    "mouscron": ["7700"],
    "ath": ["7800"],
    "soignies": ["7060"],
    "binche": ["7130"],
    "enghien": ["7850"],
    "edingen": ["7850"],
    "comines": ["7780"],
    "frameries": ["7080"],
    "quaregnon": ["7390"],
    "manage": ["7170"],
    "braine-le-comte": ["7090"],
    "lessines": ["7860"],
    "lessen": ["7860"],
    "fleurus": ["6220"],
    "chatelet": ["6200"],
    "châtelet": ["6200"],
    "fontaine-l'eveque": ["6140"],
    "fontaine-l'évêque": ["6140"],
    # Liège
    "liege": ["4000", "4020", "4030", "4031", "4032"],
    "liège": ["4000", "4020", "4030", "4031", "4032"],
    "luik": ["4000", "4020", "4030", "4031", "4032"],
    "verviers": ["4800"],
    "herstal": ["4040"],
    "seraing": ["4100"],
    "eupen": ["4700"],
    "spa": ["4900"],
    "huy": ["4500"],
    "hoei": ["4500"],
    "waremme": ["4300"],
    "borgworm": ["4300"],
    "vise": ["4600"],
    "visé": ["4600"],
    "malmedy": ["4960"],
    "stavelot": ["4970"],
    # Namur
    "namur": ["5000", "5001", "5002", "5003", "5004", "5020", "5021", "5022", "5024"],
    "namen": ["5000", "5001", "5002", "5003", "5004", "5020", "5021", "5022", "5024"],
    "dinant": ["5500"],
    "andenne": ["5300"],
    "gembloux": ["5030"],
    "sambreville": ["5060"],
    "ciney": ["5590"],
    "rochefort": ["5580"],
    "couvin": ["5660"],
    "philippeville": ["5600"],
    # Luxembourg
    "arlon": ["6700"],
    "aarlen": ["6700"],
    "bastogne": ["6600"],
    "marche-en-famenne": ["6900"],
    "virton": ["6760"],
    "neufchateau": ["6840"],
    "neufchâteau": ["6840"],
    "bouillon": ["6830"],
    "durbuy": ["6940"],
    "libramont": ["6800"],
    "saint-hubert": ["6870"],
    # Limbourg
    "hasselt": ["3500"],
    "genk": ["3600"],
    "beringen": ["3580"],
    "sint-truiden": ["3800"],
    "saint-trond": ["3800"],
    "tongeren": ["3700"],
    "tongres": ["3700"],
    "lommel": ["3920"],
    "maasmechelen": ["3630"],
    "bilzen": ["3740"],
    "heusden-zolder": ["3550"],
}


def resolve_location(location: str) -> tuple[str, list[str]]:
    """Resolve a location string to a city name and list of postal codes.

    Args:
        location: City name, postal code, or empty string

    Returns:
        Tuple of (city_name, list_of_postal_codes).
        If input is a postal code, returns (location, [location]).
        If input is a known city, returns (location, [postal_codes]).
        If unknown, returns (location, []).
    """
    if not location:
        return ("", [])

    location = location.strip()

    # Already a postal code
    if re.match(r"^\d{4}$", location):
        return (location, [location])

    # Try to find in our mapping
    key = location.lower().strip()
    if key in BELGIAN_CITY_POSTCODES:
        return (location, BELGIAN_CITY_POSTCODES[key])

    # Try without accents as fallback
    key_no_accent = _remove_accents(key)
    for city, codes in BELGIAN_CITY_POSTCODES.items():
        if _remove_accents(city) == key_no_accent:
            return (location, codes)

    logger.info(f"Location '{location}' not found in postal code mapping — no post-filtering will be applied")
    return (location, [])


def get_primary_postal_code(location: str) -> str:
    """Get the primary (first) postal code for a location.

    Used for KBO searches that need a single postal code.
    """
    _, codes = resolve_location(location)
    return codes[0] if codes else ""


def filter_by_location(
    professionals: list,
    location: str,
    postal_codes: list[str],
) -> list:
    """Filter professionals to keep only those matching the requested location.

    Matching rules (in order):
    1. If professional has a postal code, check if it's in the allowed list
    2. If professional has a city name, check if it matches (case-insensitive)
    3. If professional has no location data, keep it (benefit of the doubt)

    Args:
        professionals: List of Professional objects
        location: Original location string from user
        postal_codes: List of valid postal codes for this location

    Returns:
        Filtered list of professionals
    """
    if not location or not postal_codes:
        return professionals

    location_lower = location.lower().strip()
    # Build a set of all city names that map to any of our postal codes
    allowed_cities = set()
    for city, codes in BELGIAN_CITY_POSTCODES.items():
        if any(c in postal_codes for c in codes):
            allowed_cities.add(city)
    allowed_cities.add(location_lower)

    filtered = []
    removed = 0

    for prof in professionals:
        # Rule 1: check postal code
        if prof.code_postal:
            if prof.code_postal in postal_codes:
                filtered.append(prof)
                continue
            else:
                removed += 1
                logger.debug(
                    f"Filtered out '{prof.nom}' — postal code {prof.code_postal} "
                    f"not in {location} ({postal_codes[:3]}...)"
                )
                continue

        # Rule 2: check city name
        if prof.ville:
            prof_city = prof.ville.lower().strip()
            if prof_city in allowed_cities or location_lower in prof_city or prof_city in location_lower:
                filtered.append(prof)
                continue
            else:
                removed += 1
                logger.debug(f"Filtered out '{prof.nom}' — city '{prof.ville}' doesn't match '{location}'")
                continue

        # Rule 3: no location data — keep
        filtered.append(prof)

    if removed > 0:
        logger.info(f"Location filter: kept {len(filtered)}/{len(professionals)} results for '{location}' (removed {removed})")

    return filtered


def _remove_accents(text: str) -> str:
    """Remove common French accents for fuzzy matching."""
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ç": "c",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
