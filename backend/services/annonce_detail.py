from services.cavaliers_factors import detail_cavaliers


def enrich_annonce_detail(annonce, df):
    """ORA-174 (maquette 06, "Fiche annonce") : enrichit une annonce issue
    d'`annonces_store` (SQLite — titre/prix/surface/ville/quartier/url/date)
    avec les champs dérivés du dataset d'entraînement (master_immo_final.csv,
    `df` = `data_loader.get_data()`), qui n'y sont pas stockés :

    - `latitude`/`longitude`/`type_local`/`prix_m2` : la ligne du dataset
      correspondant à la même `url` (clé de jointure déjà utilisée par
      generate_map.py, ORA-107 — `get_annonce_by_url`).
    - `quartier_prix_m2_moyen` : moyenne du €/m² pour le même quartier et le
      même type_local (la "médiane" affichée par la maquette — cf. le même
      raccourci de vocabulaire que /api/quartier-stats, qui calcule une
      moyenne réelle plutôt qu'une vraie médiane).
    - `cavaliers_detail` : les 4 Cavaliers "autour de l'annonce", réutilisant
      les colonnes dist_*/nb_*_500m déjà précalculées pour CETTE ligne
      précise (pas un rayon recalculé à la volée) — cf. detail_cavaliers,
      ORA-172.

    Renvoie `annonce` inchangée (sans lever d'erreur) si `url` ne matche
    aucune ligne du dataset — une annonce peut être plus récente que le
    dernier snapshot d'entraînement, ou son statut a changé entre-temps.
    """
    url = annonce.get('url')
    if not url or df is None or df.empty or 'url' not in df.columns:
        return annonce

    matches = df[df['url'] == url]
    if matches.empty:
        return annonce

    row = matches.iloc[0]
    enriched = dict(annonce)

    for field in ('latitude', 'longitude', 'type_local', 'prix_m2'):
        if field in row.index and row[field] == row[field]:  # exclut NaN
            enriched[field] = row[field]

    type_local = row.get('type_local')
    quartier = row.get('quartier')
    if type_local == type_local and quartier == quartier:
        same_segment = df[(df['quartier'] == quartier) & (df['type_local'] == type_local) & df['prix_m2'].notna()]
        if not same_segment.empty:
            enriched['quartier_prix_m2_moyen'] = round(float(same_segment['prix_m2'].mean()), 1)

    enriched['cavaliers_detail'] = detail_cavaliers(matches)

    return enriched
