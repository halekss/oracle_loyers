import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6371000

TYPE_LOCAL_ALIASES = {
    "STUDIO/T1": "Studio/T1",
    "STUDIO": "Studio/T1",
    "T1": "Studio/T1",
    "T2": "T2",
    "T3": "T3",
    "T4": "Grand (T4+)",
    "T4+": "Grand (T4+)",
    "T5": "Grand (T4+)",
    "GRAND (T4+)": "Grand (T4+)",
    "MAISON": "Grand (T4+)",
}

TYPE_BIEN_CANONICAL = ["Appartement", "Maison", "Studio"]


def normalize_type_local(value):
    """Normalise un type de bien utilisateur (T1, studio, T4+...) vers une catégorie du modèle."""
    if not value:
        return None
    return TYPE_LOCAL_ALIASES.get(str(value).strip().upper())


def normalize_type_bien(value):
    """Normalise le type de bien brut (Appartement/Maison/Studio), 'Appartement' par défaut."""
    if not value:
        return "Appartement"
    candidate = str(value).strip().capitalize()
    return candidate if candidate in TYPE_BIEN_CANONICAL else "Appartement"


def resolve_quartier(quartier_input, known_quartiers):
    """Résout un nom de quartier saisi vers son libellé canonique (recherche textuelle souple)."""
    if not quartier_input:
        return None
    needle = str(quartier_input).strip().lower()
    if not needle:
        return None
    for candidate in known_quartiers:
        candidate_lower = str(candidate).lower()
        if needle in candidate_lower or candidate_lower in needle:
            return candidate
    return None


def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Distance haversine (mètres) entre un point (lat1, lon1) et un ou plusieurs points (lat2, lon2)."""
    lat1_r, lon1_r, lat2_r, lon2_r = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2.0) ** 2
    return EARTH_RADIUS_M * 2 * np.arcsin(np.sqrt(a))


def compute_distance_features(latitude, longitude, cavaliers_df):
    """Distance (m) au point le plus proche de chaque catégorie de cavalier, même logique que clean_immo.py."""
    features = {}
    for category, subset in cavaliers_df.groupby("categorie_cavalier"):
        clean_name = category.replace(" - ", "_").replace(" ", "_").lower()
        dists = haversine_distance_m(
            latitude, longitude, subset["latitude"].values, subset["longitude"].values
        )
        if len(dists):
            features[f"dist_{clean_name}"] = float(np.min(dists))
    return features


def estimate_confidence(df, quartier, type_local):
    """Niveau de confiance basé sur le nombre de comparables réels (quartier + type) dans le dataset."""
    if df is None or df.empty:
        return "Faible", 0

    mask = (df["quartier"] == quartier) & (df["type_local"] == type_local)
    count = int(mask.sum())
    if count >= 20:
        return "Élevée", count
    if count >= 5:
        return "Moyenne", count
    return "Faible", count


def build_feature_row(payload, df, cavaliers_df, feature_names):
    """
    Construit le vecteur de features attendu par le modèle à partir du payload utilisateur.
    Renvoie (features_df, infos) en cas de succès, ou (None, [messages d'erreur]) sinon.
    """
    errors = []

    surface = None
    try:
        surface = float(payload.get("surface"))
        if surface <= 0:
            errors.append("surface doit être un nombre strictement positif")
            surface = None
    except (TypeError, ValueError):
        errors.append("surface est requise et doit être numérique")

    type_local = normalize_type_local(payload.get("type_local"))
    if not type_local:
        errors.append("type_local invalide (attendu : Studio/T1, T2, T3 ou Grand (T4+))")

    known_quartiers = df["quartier"].dropna().unique().tolist() if df is not None else []
    quartier = resolve_quartier(payload.get("quartier"), known_quartiers)
    if not quartier:
        errors.append("quartier inconnu ou non fourni")

    if errors:
        return None, errors

    type_bien = normalize_type_bien(payload.get("type"))
    quartier_rows = df[df["quartier"] == quartier]

    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    if latitude is None or longitude is None:
        coords = quartier_rows.dropna(subset=["latitude", "longitude"])
        if not coords.empty:
            latitude = float(coords["latitude"].mean())
            longitude = float(coords["longitude"].mean())
        else:
            latitude, longitude = 0.0, 0.0
    else:
        latitude, longitude = float(latitude), float(longitude)

    code_postal = payload.get("code_postal")
    if code_postal is None:
        cp_series = pd.to_numeric(quartier_rows["code_postal"], errors="coerce").dropna()
        code_postal = float(cp_series.mode().iloc[0]) if not cp_series.empty else 69000.0
    else:
        code_postal = float(code_postal)

    row = dict.fromkeys(feature_names, 0.0)
    row["surface"] = surface
    row["code_postal"] = code_postal
    row["latitude"] = latitude
    row["longitude"] = longitude

    if cavaliers_df is not None and not cavaliers_df.empty:
        for name, value in compute_distance_features(latitude, longitude, cavaliers_df).items():
            if name in row:
                row[name] = value

    for column in (f"type_{type_bien}", f"type_local_{type_local}", f"quartier_{quartier}"):
        if column in row:
            row[column] = 1.0

    features_df = pd.DataFrame([row], columns=feature_names)
    infos = {"quartier": quartier, "type_local": type_local, "type": type_bien, "surface": surface}
    return features_df, infos
