"""Dictionnaire des codes NACE-BEL par catégorie de profession.

Chaque entrée contient :
- code NACE
- description en français
- mot-clé correspondant pour la recherche Pages d'Or
"""

NACE_CATEGORIES = {
    # =========================================================================
    # SANTÉ
    # =========================================================================
    "sante": {
        "label": "Santé",
        "professions": {
            "medecin_generaliste": {
                "nace": "86.210",
                "description": "Médecin généraliste",
                "pagesdor_keyword": "medecin-generaliste",
            },
            "medecin_specialiste": {
                "nace": "86.220",
                "description": "Médecin spécialiste",
                "pagesdor_keyword": "medecin-specialiste",
            },
            "dentiste": {
                "nace": "86.230",
                "description": "Dentiste",
                "pagesdor_keyword": "dentiste",
            },
            "kinesitherapeute": {
                "nace": "86.901",
                "description": "Kinésithérapeute",
                "pagesdor_keyword": "kinesitherapeute",
            },
            "pharmacien": {
                "nace": "47.730",
                "description": "Pharmacien",
                "pagesdor_keyword": "pharmacie",
            },
            "infirmier": {
                "nace": "86.901",
                "description": "Infirmier à domicile",
                "pagesdor_keyword": "infirmier",
            },
            "psychologue": {
                "nace": "86.909",
                "description": "Psychologue",
                "pagesdor_keyword": "psychologue",
            },
            "veterinaire": {
                "nace": "75.000",
                "description": "Vétérinaire",
                "pagesdor_keyword": "veterinaire",
            },
            "opticien": {
                "nace": "47.782",
                "description": "Opticien",
                "pagesdor_keyword": "opticien",
            },
            "osteopathe": {
                "nace": "86.909",
                "description": "Ostéopathe",
                "pagesdor_keyword": "osteopathe",
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
                "nace": "69.101",
                "description": "Avocat",
                "pagesdor_keyword": "avocat",
            },
            "notaire": {
                "nace": "69.102",
                "description": "Notaire",
                "pagesdor_keyword": "notaire",
            },
            "huissier": {
                "nace": "69.109",
                "description": "Huissier de justice",
                "pagesdor_keyword": "huissier-de-justice",
            },
            "comptable": {
                "nace": "69.200",
                "description": "Comptable / Expert-comptable",
                "pagesdor_keyword": "comptable",
            },
            "reviseur": {
                "nace": "69.201",
                "description": "Réviseur d'entreprises",
                "pagesdor_keyword": "reviseur-entreprises",
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
                "nace": "43.221",
                "description": "Plombier / Installateur sanitaire",
                "pagesdor_keyword": "plombier",
            },
            "electricien": {
                "nace": "43.211",
                "description": "Électricien",
                "pagesdor_keyword": "electricien",
            },
            "chauffagiste": {
                "nace": "43.222",
                "description": "Chauffagiste / HVAC",
                "pagesdor_keyword": "chauffagiste",
            },
            "peintre": {
                "nace": "43.341",
                "description": "Peintre en bâtiment",
                "pagesdor_keyword": "peintre-batiment",
            },
            "couvreur": {
                "nace": "43.910",
                "description": "Couvreur",
                "pagesdor_keyword": "couvreur",
            },
            "menuisier": {
                "nace": "43.320",
                "description": "Menuisier",
                "pagesdor_keyword": "menuisier",
            },
            "carreleur": {
                "nace": "43.330",
                "description": "Carreleur",
                "pagesdor_keyword": "carreleur",
            },
            "macon": {
                "nace": "43.110",
                "description": "Maçon",
                "pagesdor_keyword": "macon",
            },
            "architecte": {
                "nace": "71.111",
                "description": "Architecte",
                "pagesdor_keyword": "architecte",
            },
            "geometre": {
                "nace": "71.121",
                "description": "Géomètre-expert",
                "pagesdor_keyword": "geometre",
            },
            "demenageur": {
                "nace": "49.420",
                "description": "Déménageur",
                "pagesdor_keyword": "demenagement",
            },
            "serrurier": {
                "nace": "43.290",
                "description": "Serrurier",
                "pagesdor_keyword": "serrurier",
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
                "nace": "56.101",
                "description": "Restaurant",
                "pagesdor_keyword": "restaurant",
            },
            "boulanger": {
                "nace": "10.710",
                "description": "Boulanger / Pâtissier",
                "pagesdor_keyword": "boulangerie",
            },
            "boucher": {
                "nace": "47.221",
                "description": "Boucher / Charcutier",
                "pagesdor_keyword": "boucherie",
            },
            "traiteur": {
                "nace": "56.210",
                "description": "Traiteur",
                "pagesdor_keyword": "traiteur",
            },
            "cafe_bar": {
                "nace": "56.301",
                "description": "Café / Bar",
                "pagesdor_keyword": "cafe",
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
                "nace": "47.761",
                "description": "Fleuriste",
                "pagesdor_keyword": "fleuriste",
            },
            "coiffeur": {
                "nace": "96.021",
                "description": "Coiffeur",
                "pagesdor_keyword": "coiffeur",
            },
            "estheticienne": {
                "nace": "96.022",
                "description": "Esthéticienne / Institut de beauté",
                "pagesdor_keyword": "institut-de-beaute",
            },
            "garagiste": {
                "nace": "45.201",
                "description": "Garagiste / Réparation automobile",
                "pagesdor_keyword": "garage-automobile",
            },
            "agence_immobiliere": {
                "nace": "68.311",
                "description": "Agence immobilière",
                "pagesdor_keyword": "agence-immobiliere",
            },
            "assurance": {
                "nace": "66.220",
                "description": "Courtier en assurances",
                "pagesdor_keyword": "assurance",
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
                "description": "Développeur / Programmeur",
                "pagesdor_keyword": "informatique-developpement",
            },
            "consultant_it": {
                "nace": "62.020",
                "description": "Consultant IT",
                "pagesdor_keyword": "consultant-informatique",
            },
            "reparation_pc": {
                "nace": "95.110",
                "description": "Réparation ordinateurs",
                "pagesdor_keyword": "reparation-ordinateur",
            },
            "hebergement_web": {
                "nace": "63.110",
                "description": "Hébergement web",
                "pagesdor_keyword": "hebergement-web",
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
                "description": "Nettoyage de bâtiments",
                "pagesdor_keyword": "nettoyage",
            },
            "securite": {
                "nace": "80.100",
                "description": "Sécurité / Gardiennage",
                "pagesdor_keyword": "securite-gardiennage",
            },
            "publicite": {
                "nace": "73.110",
                "description": "Agence de publicité",
                "pagesdor_keyword": "agence-publicite",
            },
            "traduction": {
                "nace": "74.300",
                "description": "Traducteur / Interprète",
                "pagesdor_keyword": "traduction",
            },
            "photographe": {
                "nace": "74.201",
                "description": "Photographe",
                "pagesdor_keyword": "photographe",
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
                "description": "Auto-école",
                "pagesdor_keyword": "auto-ecole",
            },
            "formation_professionnelle": {
                "nace": "85.592",
                "description": "Formation professionnelle",
                "pagesdor_keyword": "formation-professionnelle",
            },
            "cours_langues": {
                "nace": "85.591",
                "description": "Cours de langues",
                "pagesdor_keyword": "cours-de-langues",
            },
        },
    },
}


def find_profession(query: str) -> list[dict]:
    """Recherche une profession par nom ou code NACE.

    Returns:
        Liste de dicts avec: key, nace, description, pagesdor_keyword, category
    """
    query_lower = query.lower().strip()
    results = []

    for cat_key, cat_data in NACE_CATEGORIES.items():
        for prof_key, prof_data in cat_data["professions"].items():
            match = (
                query_lower in prof_key
                or query_lower in prof_data["description"].lower()
                or query_lower == prof_data["nace"]
                or query_lower in prof_data["pagesdor_keyword"]
            )
            if match:
                results.append({
                    "key": prof_key,
                    "nace": prof_data["nace"],
                    "description": prof_data["description"],
                    "pagesdor_keyword": prof_data["pagesdor_keyword"],
                    "category": cat_data["label"],
                })

    return results


def list_all_professions() -> list[dict]:
    """Retourne toutes les professions disponibles."""
    all_profs = []
    for cat_key, cat_data in NACE_CATEGORIES.items():
        for prof_key, prof_data in cat_data["professions"].items():
            all_profs.append({
                "key": prof_key,
                "nace": prof_data["nace"],
                "description": prof_data["description"],
                "pagesdor_keyword": prof_data["pagesdor_keyword"],
                "category": cat_data["label"],
            })
    return all_profs


def get_profession_by_key(key: str) -> dict | None:
    """Retourne une profession par sa clé exacte."""
    for cat_data in NACE_CATEGORIES.values():
        if key in cat_data["professions"]:
            prof = cat_data["professions"][key]
            return {
                "key": key,
                "nace": prof["nace"],
                "description": prof["description"],
                "pagesdor_keyword": prof["pagesdor_keyword"],
                "category": cat_data["label"],
            }
    return None
