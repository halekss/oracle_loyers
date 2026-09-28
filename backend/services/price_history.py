import os

import pandas as pd

from services.quartier_search import resolve_quartier_filter

# Même mapping que /api/quartier-stats (app.py), dupliqué ici volontairement :
# ce module lit des snapshots historiques indépendamment du DataLoader en
# mémoire utilisé par la route quartier-stats.
TYPE_LOCAL_ALIASES = {
    "T1": ["Studio/T1", "Studio", "T1"],
    "T2": ["T2"],
    "T3": ["T3"],
    "T4+": ["Grand (T4+)", "T4", "T5", "Maison"],
}


def _filter_quartier(df, quartier, type_local, ville=None):
    df_clean = df.dropna(subset=['quartier', 'prix', 'surface'])

    # Même résolution partagée (bornage ville + matching flou, ORA-71/ORA-110)
    # que /api/quartier-stats, résolue indépendamment par snapshot puisque les
    # quartiers connus peuvent varier d'un snapshot à l'autre.
    filtered, match = resolve_quartier_filter(df_clean, quartier, ville)
    if not match["found"]:
        return df_clean.iloc[0:0]

    if type_local and type_local != 'Tout':
        types_cibles = TYPE_LOCAL_ALIASES.get(type_local, [type_local])
        filtered = filtered[filtered['type_local'].isin(types_cibles)]

    return filtered


def compute_price_history(quartier, type_local, snapshots_dir, manifest_path, ville=None):
    """Calcule l'évolution du prix moyen/m² pour `quartier` à travers tous les
    snapshots de données enregistrés (ORA-72), avec le même matching partagé
    (normalisation + fuzzy) que `/api/quartier-stats` (ORA-110), borné à
    `ville` si fournie (ORA-71).

    Renvoie (historique, status) :
    - status == "insufficient_history" (historique == []) si moins de 2
      snapshots existent au total — pas assez de recul pour une tendance.
    - status == "ok" sinon ; historique est une liste chronologique de
      `{date, prix_m2_moyen, count}`, un point par snapshot où `quartier` a
      au moins une annonce correspondante après filtrage.
    """
    if not os.path.exists(manifest_path):
        return [], "insufficient_history"

    manifest = pd.read_csv(manifest_path, encoding='utf-8-sig')
    if len(manifest) < 2:
        return [], "insufficient_history"

    historique = []
    for _, row in manifest.iterrows():
        snapshot_path = os.path.join(snapshots_dir, row['snapshot_file'])
        if not os.path.exists(snapshot_path):
            continue

        df = pd.read_csv(snapshot_path)
        filtered = _filter_quartier(df, quartier, type_local, ville)
        if filtered.empty:
            continue

        if 'prix_m2' in filtered.columns:
            prix_m2_moyen = filtered['prix_m2'].mean()
        else:
            prix_m2_moyen = (filtered['prix'] / filtered['surface']).mean()

        historique.append({
            'date': row['timestamp'],
            'prix_m2_moyen': round(float(prix_m2_moyen), 0),
            'count': int(len(filtered)),
        })

    return historique, "ok"


# --- ORA-182 : historique depuis master + archive (source alternative aux
# snapshots, cf. `source` de /api/quartier-historique) --------------------

def _read_listing_columns(path):
    """Ne lit que les colonnes utiles à l'historique (prix/quartier/dates) —
    `master_immo_final.csv`/`master_archive.csv` en portent une soixantaine
    (dont les colonnes cavaliers, dist_*/nb_*_500m), inutiles ici."""
    needed = ['quartier', 'ville', 'type_local', 'prix', 'surface', 'prix_m2', 'date_dernier_scan']
    if not os.path.exists(path):
        return None
    header = pd.read_csv(path, nrows=0).columns
    usecols = [c for c in needed if c in header]
    return pd.read_csv(path, usecols=usecols)


def compute_price_history_from_listings(quartier, type_local, master_path, archive_path, ville=None):
    """Calcule l'évolution du prix moyen/m² pour `quartier` depuis
    `master_immo_final.csv` + `backend/data/master_archive.csv` (ORA-182),
    une alternative aux snapshots périodiques (`compute_price_history`
    ci-dessus) : un point par date `date_dernier_scan` distincte trouvée dans
    l'un ou l'autre fichier, pas de rééchantillonnage par période.

    Limite connue (cf. ORA-182) : `master_immo_final.csv` ne contient que le
    dernier run (une seule date, toujours la plus récente — voir "master =
    dernier run seulement") ; toute la profondeur historique vient de
    `master_archive.csv` (une ligne par annonce à la date de sa sortie du
    master). Les variations de prix d'une annonce qui reste active d'un run à
    l'autre ne sont donc visibles ici qu'au moment où elle quitte le master —
    pour un suivi pendant qu'elle est encore active, seuls les snapshots
    (`compute_price_history`) en gardent la trace.

    Renvoie (historique, status) avec la même forme que `compute_price_history`
    (`status="insufficient_history"` si moins de 2 dates distinctes)."""
    frames = [df for df in (_read_listing_columns(master_path), _read_listing_columns(archive_path)) if df is not None]
    if not frames:
        return [], "insufficient_history"

    combined = pd.concat(frames, ignore_index=True)
    if 'date_dernier_scan' not in combined.columns:
        return [], "insufficient_history"
    combined = combined.dropna(subset=['date_dernier_scan'])

    # Comme compute_price_history (longueur du manifest) : "pas assez de recul
    # pour une tendance" se juge sur la profondeur historique globale des
    # données, avant filtrage par quartier — un quartier sans annonce
    # correspondante n'est pas "insuffisant", juste vide (statut "ok").
    if combined['date_dernier_scan'].nunique() < 2:
        return [], "insufficient_history"

    filtered = _filter_quartier(combined, quartier, type_local, ville)
    if filtered.empty:
        return [], "ok"

    if 'prix_m2' in filtered.columns and filtered['prix_m2'].notna().any():
        filtered = filtered.assign(_prix_m2=filtered['prix_m2'])
    else:
        filtered = filtered.assign(_prix_m2=filtered['prix'] / filtered['surface'])

    grouped = filtered.groupby('date_dernier_scan')['_prix_m2'].agg(['mean', 'count'])
    grouped = grouped.sort_index()

    historique = [
        {'date': date, 'prix_m2_moyen': round(float(row['mean']), 0), 'count': int(row['count'])}
        for date, row in grouped.iterrows()
    ]
    return historique, "ok"
