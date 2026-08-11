import numpy as np
import pandas as pd

from services.text_matching import resolve_quartier

EARTH_RADIUS_M = 6371000

# Un loyer prédit ne peut physiquement pas être nul ou négatif. Une valeur
# <= 0 signale presque toujours une incohérence modèle/environnement (ex.
# ORA-152 : pickle XGBoost désérialisé avec une version incompatible de
# celle utilisée à l'entraînement) plutôt qu'une vraie estimation basse —
# on la traite comme une erreur explicite plutôt que de la renvoyer telle
# quelle au frontend.
MIN_PLAUSIBLE_PRICE = 0


def is_physically_implausible_price(estimated_price):
    """True si `estimated_price` ne peut pas être un loyer réel (<= 0 €)."""
    return estimated_price is None or estimated_price <= MIN_PLAUSIBLE_PRICE

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


def scope_cavaliers_to_ville(cavaliers_df, ville):
    """Cavaliers de la ville donnée uniquement (même convention que
    clean_immo.build_shapes_from_cavaliers/step_features : `code_postal`
    renseigné = cavalier Lyon, absent = cavalier Lille) — évite qu'une
    prédiction Lille calcule ses distances aux POI par rapport à des
    cavaliers Lyon (et inversement). Renvoie `cavaliers_df` inchangé si la
    ville est inconnue ou si la colonne `code_postal` est absente."""
    if cavaliers_df is None or cavaliers_df.empty or "code_postal" not in cavaliers_df.columns:
        return cavaliers_df
    if ville == "Lyon":
        return cavaliers_df[cavaliers_df["code_postal"].notna()]
    if ville == "Lille":
        return cavaliers_df[cavaliers_df["code_postal"].isna()]
    return cavaliers_df


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
    elif f"quartier_{quartier}" not in feature_names:
        # Régression réelle (ORA-99 follow-up) : un quartier peut exister dans
        # les données réelles (df) sans jamais avoir été vu par le modèle
        # actif (ex: tout Lille, tant que le garde-fou de promotion rejette un
        # réentraînement combiné) — sans ce contrôle, la colonne one-hot
        # correspondante est silencieusement ignorée plus bas et le modèle
        # prédit à l'aveugle, tout en affichant un niveau de confiance basé
        # sur les vraies annonces comparables : trompeur. Le frontend a déjà
        # un repli silencieux sur la moyenne réelle du secteur quand cet
        # appel échoue (cf. App.jsx handleScan).
        errors.append(
            f"Le modèle actif n'a pas de données d'entraînement pour le quartier '{quartier}' "
            "— prédiction non fiable pour cette zone."
        )

    if errors:
        return None, errors

    type_bien = normalize_type_bien(payload.get("type"))
    quartier_rows = df[df["quartier"] == quartier]

    ville_annonce = None
    if "ville" in quartier_rows.columns:
        villes_connues = quartier_rows["ville"].dropna()
        if not villes_connues.empty:
            ville_annonce = villes_connues.mode().iloc[0]

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

    cavaliers_scoped = scope_cavaliers_to_ville(cavaliers_df, ville_annonce)
    if cavaliers_scoped is not None and not cavaliers_scoped.empty:
        for name, value in compute_distance_features(latitude, longitude, cavaliers_scoped).items():
            if name in row:
                row[name] = value

    for column in (f"type_{type_bien}", f"type_local_{type_local}", f"quartier_{quartier}"):
        if column in row:
            row[column] = 1.0

    features_df = pd.DataFrame([row], columns=feature_names)
    infos = {"quartier": quartier, "type_local": type_local, "type": type_bien, "surface": surface}
    return features_df, infos
