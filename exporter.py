"""Export des données professionnelles en CSV."""

import os
import re
from datetime import datetime

import pandas as pd

from config import OUTPUT_DIR
from models import Professional


# Ordre et noms des colonnes dans le CSV (Belgique)
CSV_COLUMNS_BE = {
    "nom": "Nom",
    "profession": "Profession",
    "description_activite": "Activité",
    "code_nace": "Code NACE",
    "numero_bce": "N° BCE",
    "adresse": "Adresse",
    "code_postal": "Code Postal",
    "ville": "Ville",
    "province": "Province",
    "telephone": "Téléphone",
    "email": "Email",
    "site_web": "Site Web",
    "horaires": "Horaires",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "forme_juridique": "Forme Juridique",
    "statut": "Statut",
    "sources": "Sources",
}

# Ordre et noms des colonnes dans le CSV (France)
CSV_COLUMNS_FR = {
    "nom": "Nom",
    "profession": "Profession",
    "description_activite": "Activité",
    "code_nace": "Code NAF",
    "numero_entreprise": "SIREN",
    "adresse": "Adresse",
    "code_postal": "Code Postal",
    "ville": "Ville",
    "province": "Région",
    "telephone": "Téléphone",
    "email": "Email",
    "site_web": "Site Web",
    "horaires": "Horaires",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "forme_juridique": "Forme Juridique",
    "statut": "Statut",
    "sources": "Sources",
}

# Rétrocompat
CSV_COLUMNS = CSV_COLUMNS_BE


def export_csv(
    professionals: list[Professional],
    profession_name: str = "",
    location: str = "",
    output_path: str = "",
    country: str = "BE",
) -> str:
    """Exporte les professionnels en fichier CSV.

    Args:
        professionals: Liste des professionnels à exporter
        profession_name: Nom de la profession (pour le nom du fichier)
        location: Localisation (pour le nom du fichier)
        output_path: Chemin complet du fichier (optionnel)
        country: "BE" ou "FR"

    Returns:
        Chemin du fichier CSV créé
    """
    if not professionals:
        return ""

    columns = CSV_COLUMNS_FR if country == "FR" else CSV_COLUMNS_BE

    # Construire le DataFrame — forcer toutes les colonnes en string
    data = [p.to_dict() for p in professionals]
    df = pd.DataFrame(data).astype(str)

    # Remplacer les "None", "nan", "NaN" par des chaînes vides
    df = df.replace({"None": "", "nan": "", "NaN": "", "none": ""})

    # Réordonner et renommer les colonnes
    existing_cols = [c for c in columns.keys() if c in df.columns]
    df = df[existing_cols]
    df = df.rename(columns=columns)

    # Corriger le code postal (retirer le ".0" des floats convertis)
    if "Code Postal" in df.columns:
        df["Code Postal"] = df["Code Postal"].apply(lambda v: _clean_postal_code(v, country))

    # Corriger les téléphones (retirer le ".0" et formater)
    if "Téléphone" in df.columns:
        clean_fn = _clean_phone_fr if country == "FR" else _clean_phone
        df["Téléphone"] = df["Téléphone"].apply(clean_fn)

    # Déterminer le chemin de sortie
    if not output_path:
        output_path = _generate_filename(profession_name, location)

    # Créer le dossier si nécessaire
    os.makedirs(os.path.dirname(output_path) or OUTPUT_DIR, exist_ok=True)

    # Exporter en CSV avec BOM pour Excel
    df.to_csv(output_path, index=False, encoding="utf-8-sig", sep=";")

    return output_path


def _generate_filename(profession_name: str, location: str) -> str:
    """Génère un nom de fichier automatique."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    parts = []
    if profession_name:
        slug = _slugify(profession_name)
        parts.append(slug)
    if location:
        slug = _slugify(location)
        parts.append(slug)

    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    parts.append(date_str)

    filename = "_".join(parts) + ".csv"
    return os.path.join(OUTPUT_DIR, filename)


def _clean_postal_code(val: str, country: str = "BE") -> str:
    """Nettoie un code postal (retire .0 des conversions float)."""
    val = str(val).strip()
    if not val:
        return ""
    # "5000.0" → "5000"
    if re.match(r"^\d+\.0$", val):
        return val.split(".")[0]
    # France : 5 chiffres
    if country == "FR":
        match = re.match(r"^(\d{5})", val)
        if match:
            return match.group(1)
    else:
        # Belgique : 4 chiffres
        match = re.match(r"^(\d{4})", val)
        if match:
            return match.group(1)
    return val


def _clean_phone(val: str) -> str:
    """Nettoie un numéro de téléphone (retire .0, formate en belge)."""
    val = str(val).strip()
    if not val:
        return ""
    # "499031667.0" → "0499031667" → "0499 03 16 67"
    if re.match(r"^\d+\.0$", val):
        val = val.split(".")[0]
    # Si déjà formaté avec des espaces, garder tel quel
    if " " in val and len(val) > 8:
        return val
    # Nettoyer
    digits = re.sub(r"[^\d+]", "", val)
    if not digits:
        return val
    # +32... → 0...
    if digits.startswith("+32"):
        digits = "0" + digits[3:]
    elif digits.startswith("32") and len(digits) >= 11:
        digits = "0" + digits[2:]
    # Ajouter le 0 si manquant (numéro belge à 9 chiffres)
    if len(digits) == 9 and digits[0] != "0":
        digits = "0" + digits
    # Formater selon le type de numéro belge
    if len(digits) == 10:
        # Mobile belge : 046x, 047x, 048x, 049x
        if digits[:3] in ("046", "047", "048", "049") or digits[:4] in ("0456", "0457", "0458"):
            return f"{digits[:4]} {digits[4:6]} {digits[6:8]} {digits[8:]}"
        # Fixe grands indicatifs (02, 03, 04-Liège, 09)
        elif digits[:2] in ("02", "03", "04", "09"):
            return f"{digits[:2]} {digits[2:5]} {digits[5:7]} {digits[7:]}"
        # Autres fixes à 3 chiffres (010-089)
        else:
            return f"{digits[:3]} {digits[3:5]} {digits[5:7]} {digits[7:]}"
    elif len(digits) == 9 and digits.startswith("0"):
        # Fixe belge court : 0xx xx xx xx (ex: 081 26 13 30)
        return f"{digits[:3]} {digits[3:5]} {digits[5:7]} {digits[7:]}"
    return val


def _clean_phone_fr(val: str) -> str:
    """Nettoie un numéro de téléphone français (groupes de 2)."""
    val = str(val).strip()
    if not val:
        return ""
    if re.match(r"^\d+\.0$", val):
        val = val.split(".")[0]
    # Si déjà formaté avec des espaces, garder tel quel
    if " " in val and len(val) > 8:
        return val
    # Nettoyer
    digits = re.sub(r"[^\d+]", "", val)
    if not digits:
        return val
    # +33... → 0...
    if digits.startswith("+33"):
        digits = "0" + digits[3:]
    elif digits.startswith("33") and len(digits) >= 11:
        digits = "0" + digits[2:]
    # Formater en groupes de 2 (format français : XX XX XX XX XX)
    if len(digits) == 10 and digits.startswith("0"):
        return f"{digits[0:2]} {digits[2:4]} {digits[4:6]} {digits[6:8]} {digits[8:10]}"
    return val


def _slugify(text: str) -> str:
    """Convertit un texte en slug pour nom de fichier."""
    text = text.lower().strip()
    text = re.sub(r"[àáâãäå]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text
