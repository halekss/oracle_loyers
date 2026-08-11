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
