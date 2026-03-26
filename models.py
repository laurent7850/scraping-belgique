"""Modèle de données pour les professionnels."""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Professional:
    """Représente un professionnel/entreprise."""

    # Identité
    nom: str = ""
    numero_bce: str = ""          # Belgique : BCE 10 chiffres
    numero_entreprise: str = ""   # France : SIREN/SIRET
    pays: str = ""                # "BE" ou "FR"

    # Adresse
    adresse: str = ""
    code_postal: str = ""
    ville: str = ""
    province: str = ""

    # Contact
    telephone: str = ""
    email: str = ""
    site_web: str = ""

    # Activité
    profession: str = ""
    code_nace: str = ""
    description_activite: str = ""

    # Enrichi
    horaires: str = ""
    facebook: str = ""
    instagram: str = ""
    linkedin: str = ""

    # Administratif
    forme_juridique: str = ""
    statut: str = ""

    # Métadonnées
    sources: str = ""
    detail_url: str = ""  # URL de la page détail (Pages d'Or, etc.)

    def to_dict(self) -> dict:
        return asdict(self)

    def merge(self, other: "Professional") -> None:
        """Fusionne les données d'un autre Professional (remplit les champs vides)."""
        for fld in self.__dataclass_fields__:
            current = getattr(self, fld)
            new_val = getattr(other, fld)
            if not current and new_val:
                setattr(self, fld, new_val)
        # Combiner les sources
        if other.sources and other.sources not in self.sources:
            self.sources = f"{self.sources},{other.sources}" if self.sources else other.sources

    @property
    def has_contact(self) -> bool:
        return bool(self.telephone or self.email)

    @property
    def completeness(self) -> float:
        """Score de complétude (0.0 à 1.0)."""
        fields_to_check = [
            "nom", "adresse", "code_postal", "ville",
            "telephone", "email", "site_web", "profession",
        ]
        filled = sum(1 for f in fields_to_check if getattr(self, f))
        return filled / len(fields_to_check)
