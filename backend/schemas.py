"""
Schémas de validation des payloads pour les routes Flask actives
(/api/chat, /api/quartier-stats, /api/predict, /api/report/pdf).

Valident la forme (types) des champs avant tout traitement métier, sans
dupliquer les règles sémantiques déjà bien couvertes par les routes elles-
mêmes (ex : plage de valeurs pour /api/predict, gérée par services/predictor.py).
"""

from typing import List, Optional

from pydantic import BaseModel, ValidationError, field_validator

__all__ = [
    "ChatRequestSchema",
    "QuartierStatsRequestSchema",
    "PredictRequestSchema",
    "PdfReportRequestSchema",
    "ValidationError",
]


class ChatRequestSchema(BaseModel):
    message: str
    context: Optional[str] = ""

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value):
        if not value or not value.strip():
            raise ValueError("message vide")
        return value


class QuartierStatsRequestSchema(BaseModel):
    quartier: str
    type_local: Optional[str] = "Tout"
    # Optionnel pour compatibilité (client existant qui ne l'envoie pas) :
    # ville active dans le frontend (ex: "lyon", "lille"), utilisée pour
    # borner la recherche à cette ville et permettre une recherche par nom
    # de ville entière plutôt que par quartier (cf. app.py get_quartier_stats).
    ville: Optional[str] = None

    @field_validator("quartier")
    @classmethod
    def quartier_must_not_be_blank(cls, value):
        if not value or not value.strip():
            raise ValueError("quartier vide")
        return value


class PredictRequestSchema(BaseModel):
    # Champs volontairement optionnels ici : la présence/plage de valeurs
    # (surface > 0, quartier/type_local connus...) reste validée par
    # services/predictor.build_feature_row, avec des messages dédiés déjà
    # testés. Ce schéma ne fait que garantir la forme (types) des champs
    # fournis, avant que build_feature_row n'y accède.
    surface: Optional[float] = None
    quartier: Optional[str] = None
    type_local: Optional[str] = None
    type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    code_postal: Optional[float] = None


class FacteurSchema(BaseModel):
    categorie: str
    phrase: str


class PriceHistoryPointSchema(BaseModel):
    date: str
    prix_m2_moyen: float
    count: int


class ComparableSchema(BaseModel):
    type_local: Optional[str] = None
    prix: Optional[float] = None
    surface: Optional[float] = None


class PdfReportRequestSchema(BaseModel):
    # Reprend le résultat déjà affiché par ResultCard.jsx/PriceHistory.jsx
    # (ORA-121/ORA-122) : aucun recalcul côté serveur, seule la mise en page
    # PDF est nouvelle.
    quartier: str
    estimated_price: float
    prix_m2: Optional[float] = None
    confiance: Optional[str] = None
    count: Optional[int] = None
    type_local: Optional[str] = None
    facteurs: Optional[List[FacteurSchema]] = None
    historique: Optional[List[PriceHistoryPointSchema]] = None
    comparables: Optional[List[ComparableSchema]] = None

    @field_validator("quartier")
    @classmethod
    def quartier_must_not_be_blank(cls, value):
        if not value or not value.strip():
            raise ValueError("quartier vide")
        return value
