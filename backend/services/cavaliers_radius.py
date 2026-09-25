import os

import numpy as np
import pandas as pd

from services.cavaliers_factors import ABSENCE_PHRASES, CATEGORY_LABELS, CATEGORY_ORDER, phrase_for
from services.predictor import haversine_distance_m

# Seuls rayons acceptés par /api/cavaliers — le sélecteur front (300 m/
# 500 m/1 km) n'en propose pas d'autres.
ALLOWED_RADII_M = (300, 500, 1000)
DEFAULT_RADIUS_M = 500

CAVALIERS_CSV_COLUMNS = ['categorie_cavalier', 'type_osm', 'nom_lieu', 'latitude', 'longitude']


def _parse_categorie_cavalier(raw):
    """"Vice - Sex-shop" -> ("vice", "sex-shop") — même normalisation que
    predictor.compute_distance_features (`clean_name`), pour retomber sur les
    mêmes clés que POI_PHRASES (cavaliers_factors.py)."""
    clean = str(raw).replace(' - ', '_').replace(' ', '_').lower()
    category, _, poi = clean.partition('_')
    return category, poi


class CavaliersRadiusService:
    """Calcule en direct (haversine, sans passer par les colonnes
    précalculées à 500m de master_immo_final.csv) le détail des 4 cavaliers
    autour d'un point donné, pour un rayon choisi (300/500/1000m) — alimente
    GET /api/cavaliers (vue "Calques" du rail, sélecteur de rayon).

    Charge cavaliers_lyon.csv/cavaliers_lille.csv une seule fois à la
    construction (comme services.data_loader.DataLoader), pas à chaque
    requête — l'instance vit pour la durée du process Flask (app.py)."""

    def __init__(self, lyon_csv_path, lille_csv_path):
        self._by_ville = {
            'lyon': self._load(lyon_csv_path),
            'lille': self._load(lille_csv_path),
        }

    @staticmethod
    def _load(path):
        """Lit un CSV cavaliers_<ville>.csv en utf-8-sig (BOM déjà rencontré
        sur le fichier Lille en production) et ajoute les colonnes
        `categorie`/`poi` parsées depuis `categorie_cavalier`."""
        if not path or not os.path.exists(path):
            return pd.DataFrame(columns=CAVALIERS_CSV_COLUMNS + ['categorie', 'poi'])

        df = pd.read_csv(path, encoding='utf-8-sig')
        if df.empty or 'categorie_cavalier' not in df.columns:
            df['categorie'] = []
            df['poi'] = []
            return df

        parsed = df['categorie_cavalier'].apply(_parse_categorie_cavalier)
        df['categorie'] = parsed.apply(lambda pair: pair[0])
        df['poi'] = parsed.apply(lambda pair: pair[1])
        return df

    @staticmethod
    def category(result, categorie_label):
        """Raccourci pratique (tests) : l'entrée de `result["cavaliers_detail"]`
        dont `categorie` vaut `categorie_label` (ex. "Vice")."""
        return next(d for d in result['cavaliers_detail'] if d['categorie'] == categorie_label)

    def _family_dataframe(self, ville, category):
        df = self._by_ville.get((ville or '').strip().lower())
        if df is None or df.empty:
            return None
        subset = df[df['categorie'] == category]
        return subset if not subset.empty else None

    def compute(self, lat, lng, ville, radius_m=DEFAULT_RADIUS_M):
        """Détail (`cavaliers_detail`, même forme que
        cavaliers_factors.detail_cavaliers) + phrases (`facteurs`, même forme
        que cavaliers_factors.summarize_cavaliers) pour (lat, lng, ville),
        au rayon `radius_m`."""
        detail = []
        facteurs = []

        for category in CATEGORY_ORDER:
            df_family = self._family_dataframe(ville, category)
            label = CATEGORY_LABELS[category]

            if df_family is None:
                # Catégorie totalement absente des données de cette ville —
                # même convention que detail_cavaliers (on ne l'affiche pas).
                continue

            dists = haversine_distance_m(
                lat, lng, df_family['latitude'].values, df_family['longitude'].values,
            )
            df_family = df_family.assign(_dist_m=dists)

            nearest_idx = int(np.argmin(dists))
            nearest_dist_m = round(float(dists[nearest_idx]))
            nearest_nom = df_family.iloc[nearest_idx]['nom_lieu']
            nearest_poi_display = df_family.iloc[nearest_idx]['poi'].replace('_', ' ').capitalize()

            items = []
            for poi_raw, group in df_family.groupby('poi'):
                count_in_radius = int((group['_dist_m'] <= radius_m).sum())
                if count_in_radius <= 0:
                    continue
                items.append({
                    'poi_raw': poi_raw,
                    'poi': poi_raw.replace('_', ' ').capitalize(),
                    'count': count_in_radius,
                    'dist_m': round(float(group['_dist_m'].min())),
                })
            items.sort(key=lambda item: item['count'], reverse=True)
            total = sum(item['count'] for item in items)

            empty_message = None
            if not items:
                empty_message = (
                    f"Rien dans le rayon. {nearest_poi_display} les plus proches à {nearest_dist_m} m."
                )
                phrase = ABSENCE_PHRASES[category].format(rayon=radius_m)
            else:
                best = items[0]
                phrase = phrase_for(category, best['poi_raw'], best['count'], best['dist_m'], rayon=radius_m)

            detail.append({
                'categorie': label,
                'total': total,
                'items': [
                    {'poi': it['poi'], 'count': it['count'], 'dist_m': it['dist_m']} for it in items
                ],
                'empty_message': empty_message,
                'nearest': {'nom': nearest_nom, 'dist_m': nearest_dist_m},
            })
            facteurs.append({'categorie': label, 'phrase': phrase})

        return {'cavaliers_detail': detail, 'facteurs': facteurs}
