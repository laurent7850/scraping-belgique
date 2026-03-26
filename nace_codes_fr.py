"""Dictionnaire des codes NAF par catégorie de profession (France).

Chaque entrée contient :
- code NAF (équivalent français du NACE)
- description en français
- mot-clé correspondant pour la recherche Pages Jaunes
"""

NACE_CATEGORIES_FR = {
    # =========================================================================
    # SANTÉ
    # =========================================================================
    "sante": {
        "label": "Santé",
        "professions": {
            "medecin_generaliste": {
                "nace": "86.210",
                "naf": "86.21Z",
                "description": "Médecin généraliste",
                "pagesjaunes_keyword": "medecin generaliste",
            },
            "medecin_specialiste": {
                "nace": "86.220",
                "naf": "86.22Z",
                "description": "Médecin spécialiste",
                "pagesjaunes_keyword": "medecin specialiste",
            },
            "dentiste": {
                "nace": "86.230",
                "naf": "86.23Z",
                "description": "Dentiste / Chirurgien-dentiste",
                "pagesjaunes_keyword": "dentiste",
            },
            "kinesitherapeute": {
                "nace": "86.900",
                "naf": "86.90D",
                "description": "Kinésithérapeute",
                "pagesjaunes_keyword": "kinesitherapeute",
            },
            "pharmacien": {
                "nace": "47.730",
                "naf": "47.73Z",
                "description": "Pharmacie",
                "pagesjaunes_keyword": "pharmacie",
            },
            "infirmier": {
                "nace": "86.900",
                "naf": "86.90C",
                "description": "Infirmier",
                "pagesjaunes_keyword": "infirmier",
            },
            "psychologue": {
                "nace": "86.900",
                "naf": "86.90F",
                "description": "Psychologue",
                "pagesjaunes_keyword": "psychologue",
            },
            "veterinaire": {
                "nace": "75.000",
                "naf": "75.00Z",
                "description": "Vétérinaire",
                "pagesjaunes_keyword": "veterinaire",
            },
            "opticien": {
                "nace": "47.780",
                "naf": "47.78A",
                "description": "Opticien",
                "pagesjaunes_keyword": "opticien",
            },
            "osteopathe": {
                "nace": "86.900",
                "naf": "86.90F",
                "description": "Ostéopathe",
                "pagesjaunes_keyword": "osteopathe",
            },
        },
    },
    # =========================================================================
    # JURIDIQUE & COMPTABILITÉ
    # =========================================================================
    "juridique": {
        "label": "Juridique & Comptabilité",
        "professions": {
            "avocat": {
                "nace": "69.100",
                "naf": "69.10Z",
                "description": "Avocat",
                "pagesjaunes_keyword": "avocat",
            },
            "notaire": {
                "nace": "69.100",
                "naf": "69.10Z",
                "description": "Notaire",
                "pagesjaunes_keyword": "notaire",
            },
            "huissier": {
                "nace": "69.100",
                "naf": "69.10Z",
                "description": "Huissier de justice",
                "pagesjaunes_keyword": "huissier de justice",
            },
            "comptable": {
                "nace": "69.200",
                "naf": "69.20Z",
                "description": "Expert-comptable",
                "pagesjaunes_keyword": "expert comptable",
            },
            "commissaire_comptes": {
                "nace": "69.200",
                "naf": "69.20Z",
                "description": "Commissaire aux comptes",
                "pagesjaunes_keyword": "commissaire aux comptes",
            },
        },
    },
    # =========================================================================
    # BÂTIMENT & CONSTRUCTION
    # =========================================================================
    "batiment": {
        "label": "Bâtiment & Construction",
        "professions": {
            "plombier": {
                "nace": "43.220",
                "naf": "43.22A",
                "description": "Plombier",
                "pagesjaunes_keyword": "plombier",
            },
            "electricien": {
                "nace": "43.210",
                "naf": "43.21A",
                "description": "Électricien",
                "pagesjaunes_keyword": "electricien",
            },
            "chauffagiste": {
                "nace": "43.220",
                "naf": "43.22B",
                "description": "Chauffagiste",
                "pagesjaunes_keyword": "chauffagiste",
            },
            "peintre": {
                "nace": "43.340",
                "naf": "43.34Z",
                "description": "Peintre en bâtiment",
                "pagesjaunes_keyword": "peintre en batiment",
            },
            "couvreur": {
                "nace": "43.910",
                "naf": "43.91B",
                "description": "Couvreur",
                "pagesjaunes_keyword": "couvreur",
            },
            "menuisier": {
                "nace": "43.320",
                "naf": "43.32C",
                "description": "Menuisier",
                "pagesjaunes_keyword": "menuisier",
            },
            "carreleur": {
                "nace": "43.330",
                "naf": "43.33Z",
                "description": "Carreleur",
                "pagesjaunes_keyword": "carreleur",
            },
            "macon": {
                "nace": "43.110",
                "naf": "43.99A",
                "description": "Maçon",
                "pagesjaunes_keyword": "macon",
            },
            "architecte": {
                "nace": "71.110",
                "naf": "71.11Z",
                "description": "Architecte",
                "pagesjaunes_keyword": "architecte",
            },
            "geometre": {
                "nace": "71.120",
                "naf": "71.12B",
                "description": "Géomètre-expert",
                "pagesjaunes_keyword": "geometre expert",
            },
            "demenageur": {
                "nace": "49.420",
                "naf": "49.42Z",
                "description": "Déménageur",
                "pagesjaunes_keyword": "demenagement",
            },
            "serrurier": {
                "nace": "43.290",
                "naf": "43.29B",
                "description": "Serrurier",
                "pagesjaunes_keyword": "serrurier",
            },
        },
    },
    # =========================================================================
    # ALIMENTATION & RESTAURATION
    # =========================================================================
    "restauration": {
        "label": "Alimentation & Restauration",
        "professions": {
            "restaurant": {
                "nace": "56.100",
                "naf": "56.10A",
                "description": "Restaurant",
                "pagesjaunes_keyword": "restaurant",
            },
            "boulanger": {
                "nace": "10.710",
                "naf": "10.71C",
                "description": "Boulanger / Pâtissier",
                "pagesjaunes_keyword": "boulangerie patisserie",
            },
            "boucher": {
                "nace": "47.220",
                "naf": "47.22Z",
                "description": "Boucher / Charcutier",
                "pagesjaunes_keyword": "boucherie charcuterie",
            },
            "traiteur": {
                "nace": "56.210",
                "naf": "56.21Z",
                "description": "Traiteur",
                "pagesjaunes_keyword": "traiteur",
            },
            "cafe_bar": {
                "nace": "56.300",
                "naf": "56.30Z",
                "description": "Café / Bar",
                "pagesjaunes_keyword": "bar cafe",
            },
        },
    },
    # =========================================================================
    # COMMERCE
    # =========================================================================
    "commerce": {
        "label": "Commerce",
        "professions": {
            "fleuriste": {
                "nace": "47.760",
                "naf": "47.76Z",
                "description": "Fleuriste",
                "pagesjaunes_keyword": "fleuriste",
            },
            "coiffeur": {
                "nace": "96.020",
                "naf": "96.02A",
                "description": "Coiffeur",
                "pagesjaunes_keyword": "coiffeur",
            },
            "estheticienne": {
                "nace": "96.020",
                "naf": "96.02B",
                "description": "Institut de beauté",
                "pagesjaunes_keyword": "institut de beaute",
            },
            "garagiste": {
                "nace": "45.200",
                "naf": "45.20A",
                "description": "Garage automobile",
                "pagesjaunes_keyword": "garage automobile",
            },
            "agence_immobiliere": {
                "nace": "68.310",
                "naf": "68.31Z",
                "description": "Agence immobilière",
                "pagesjaunes_keyword": "agence immobiliere",
            },
            "assurance": {
                "nace": "66.220",
                "naf": "66.22Z",
                "description": "Agent d'assurances",
                "pagesjaunes_keyword": "assurance",
            },
        },
    },
    # =========================================================================
    # INFORMATIQUE & TECH
    # =========================================================================
    "informatique": {
        "label": "Informatique & Tech",
        "professions": {
            "developpeur": {
                "nace": "62.010",
                "naf": "62.01Z",
                "description": "Développeur / Programmeur",
                "pagesjaunes_keyword": "developpement informatique",
            },
            "consultant_it": {
                "nace": "62.020",
                "naf": "62.02A",
                "description": "Consultant informatique",
                "pagesjaunes_keyword": "conseil informatique",
            },
            "reparation_pc": {
                "nace": "95.110",
                "naf": "95.11Z",
                "description": "Réparation ordinateurs",
                "pagesjaunes_keyword": "depannage informatique",
            },
            "hebergement_web": {
                "nace": "63.110",
                "naf": "63.11Z",
                "description": "Hébergement web",
                "pagesjaunes_keyword": "hebergement internet",
            },
        },
    },
    # =========================================================================
    # SERVICES AUX ENTREPRISES
    # =========================================================================
    "services": {
        "label": "Services aux entreprises",
        "professions": {
            "nettoyage": {
                "nace": "81.210",
                "naf": "81.21Z",
                "description": "Nettoyage de bâtiments",
                "pagesjaunes_keyword": "nettoyage",
            },
            "securite": {
                "nace": "80.100",
                "naf": "80.10Z",
                "description": "Sécurité / Gardiennage",
                "pagesjaunes_keyword": "securite gardiennage",
            },
            "publicite": {
                "nace": "73.110",
                "naf": "73.11Z",
                "description": "Agence de publicité",
                "pagesjaunes_keyword": "agence publicite",
            },
            "traduction": {
                "nace": "74.300",
                "naf": "74.30Z",
                "description": "Traducteur / Interprète",
                "pagesjaunes_keyword": "traduction",
            },
            "photographe": {
                "nace": "74.200",
                "naf": "74.20Z",
                "description": "Photographe",
                "pagesjaunes_keyword": "photographe",
            },
        },
    },
    # =========================================================================
    # ENSEIGNEMENT & FORMATION
    # =========================================================================
    "enseignement": {
        "label": "Enseignement & Formation",
        "professions": {
            "auto_ecole": {
                "nace": "85.530",
                "naf": "85.53Z",
                "description": "Auto-école",
                "pagesjaunes_keyword": "auto ecole",
            },
            "formation_professionnelle": {
                "nace": "85.590",
                "naf": "85.59A",
                "description": "Formation professionnelle",
                "pagesjaunes_keyword": "formation professionnelle",
            },
            "cours_langues": {
                "nace": "85.590",
                "naf": "85.59A",
                "description": "Cours de langues",
                "pagesjaunes_keyword": "cours de langues",
            },
        },
    },
}


def find_profession_fr(query: str) -> list[dict]:
    """Recherche une profession française par nom ou code NAF.

    Returns:
        Liste de dicts avec: key, nace, naf, description, pagesjaunes_keyword, category
    """
    query_lower = query.lower().strip()
    results = []

    for cat_key, cat_data in NACE_CATEGORIES_FR.items():
        for prof_key, prof_data in cat_data["professions"].items():
            match = (
                query_lower in prof_key
                or query_lower in prof_data["description"].lower()
                or query_lower == prof_data["naf"]
                or query_lower == prof_data["nace"]
                or query_lower in prof_data["pagesjaunes_keyword"]
            )
            if match:
                results.append({
                    "key": prof_key,
                    "nace": prof_data["nace"],
                    "naf": prof_data["naf"],
                    "description": prof_data["description"],
                    "pagesjaunes_keyword": prof_data["pagesjaunes_keyword"],
                    "category": cat_data["label"],
                })

    return results


def list_all_professions_fr() -> list[dict]:
    """Retourne toutes les professions françaises disponibles."""
    all_profs = []
    for cat_key, cat_data in NACE_CATEGORIES_FR.items():
        for prof_key, prof_data in cat_data["professions"].items():
            all_profs.append({
                "key": prof_key,
                "nace": prof_data["nace"],
                "naf": prof_data["naf"],
                "description": prof_data["description"],
                "pagesjaunes_keyword": prof_data["pagesjaunes_keyword"],
                "category": cat_data["label"],
            })
    return all_profs


def get_profession_fr_by_key(key: str) -> dict | None:
    """Retourne une profession française par sa clé exacte."""
    for cat_data in NACE_CATEGORIES_FR.values():
        if key in cat_data["professions"]:
            prof = cat_data["professions"][key]
            return {
                "key": key,
                "nace": prof["nace"],
                "naf": prof["naf"],
                "description": prof["description"],
                "pagesjaunes_keyword": prof["pagesjaunes_keyword"],
                "category": cat_data["label"],
            }
    return None
