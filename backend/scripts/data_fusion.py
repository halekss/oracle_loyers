import pandas as pd
import re
import os
import json

# --- 0. CONFIGURATION DES CHEMINS ---
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')

# --- 1. FONCTIONS DE NETTOYAGE ---

def clean_price_integer(value):
    """Convertit en entier (supprime €, cc, espaces, points)."""
    if pd.isna(value): return None
    val_str = str(value).lower().replace('€', '').replace('eur', '').replace('cc', '').strip()
    chiffres = re.sub(r'[^\d]', '', val_str)
    if not chiffres: return None
    try:
        return int(chiffres)
    except:
        return None

def clean_surface(value):
    """Extrait le nombre avant 'm2'."""
    if pd.isna(value): return None
    val_str = str(value).replace(',', '.')
    match = re.search(r'(\d+(?:\.\d+)?)\s*m[2²]', val_str, re.IGNORECASE)
    return float(match.group(1)) if match else None

def extract_postal_code(text, default_cp="69000"):
    """Normalise le CP (69XXX ou 59XXX). `default_cp` est le repli utilisé
    quand aucun CP n'est trouvé dans le texte (ex: certains sites n'affichent
    que le département "59" pour Lille, sans code postal complet) : chaque
    ville doit passer son propre repli plutôt que de dépendre du défaut Lyon
    (`code_postal_defaut` dans scraping_config.json, cf. run_fusion())."""
    if pd.isna(text): return default_cp
    text = str(text).lower()
    match_zip = re.search(r'(69\d{3}|59\d{3})', text)
    if match_zip: return match_zip.group(1)
    match_arr = re.search(r'lyon\s*(\d{1,2})', text)
    if match_arr: return f"690{int(match_arr.group(1)):02d}"
    return default_cp

def postal_code_from_url(url):
    """CP encodé dans l'URL d'une annonce Orpi (`.../annonce-location-appartement-t3-lyon-8-69008-<uuid>/`),
    None si absent. Repli fiable quand le texte de la carte n'en donne pas."""
    match = re.search(r'-(69\d{3}|59\d{3})-', str(url))
    return match.group(1) if match else None

# Lieux réels observés dans le champ Lieu de SeLoger pour une recherche
# centrée sur Lille (le rayon de recherche du site déborde sur des communes
# limitrophes réelles, pas des communes associées comme Lomme/Hellemmes) :
# associés à leur vrai code postal, pour que clean_immo.py puisse les
# distinguer de Lille elle-même plutôt que de tout regrouper sous le CP
# générique 59000 (extract_postal_code ne trouve aucun chiffre à extraire
# dans un nom de commune, donc retombait silencieusement sur le défaut).
SELOGER_LIEU_TO_CP = {
    "lille": "59000",
    "lambersart": "59130",
    "la madeleine": "59110",
    "faches-thumesnil": "59155",
    "faches thumesnil": "59155",
    "villeneuve-d'ascq": "59650",
    "villeneuve d'ascq": "59650",
}


def normalize_lieu(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def resolve_seloger_lieu(lieu, infos, default_cp):
    """CP réel déduit du champ `Lieu` de SeLoger, ou du premier segment
    d'`Infos` ("Lieu - détails", même format structuré fourni par le site)
    si `Lieu` n'est pas un nom de lieu exploitable — constaté en conditions
    réelles : "Première occupation" et "logement étudiant" sont des
    attributs du bien, pas une localisation, mais le vrai lieu reste
    disponible en tête d'Infos pour ces annonces.

    Renvoie None si aucun lieu connu n'est trouvé ni dans l'un ni dans
    l'autre — l'appelant doit alors exclure l'annonce plutôt que de la
    localiser au hasard sur `default_cp`."""
    direct = SELOGER_LIEU_TO_CP.get(normalize_lieu(lieu))
    if direct:
        return direct

    if pd.notna(infos) and " - " in str(infos):
        premier_segment = str(infos).split(" - ", 1)[0]
        depuis_infos = SELOGER_LIEU_TO_CP.get(normalize_lieu(premier_segment))
        if depuis_infos:
            return depuis_infos

    return None


def extract_type(text):
    """Détermine le type de bien (Maison, Appartement, Studio, Coloc)."""
    if pd.isna(text): return "Appartement"
    text = str(text).lower()
    if 'colocation' in text: return 'Colocation'
    if 'maison' in text or 'villa' in text: return 'Maison'
    if 'studio' in text: return 'Studio'
    if 'parking' in text or 'garage' in text or 'box' in text: return 'Parking'
    if 'local' in text or 'bureau' in text or 'commercial' in text: return 'Local/Bureau'
    return 'Appartement'

def format_description(text):
    """Nettoie la description pour l'affichage final."""
    if pd.isna(text): return ""
    text = str(text).strip()
    prefix = []
    match_p = re.search(r'(T\d|\d+\s*pi[èe]ce)', text, re.IGNORECASE)
    if match_p: prefix.append(match_p.group(1).capitalize())
    match_ch = re.search(r'(\d+\s*chambre)', text, re.IGNORECASE)
    if match_ch: prefix.append(match_ch.group(1).lower())

    clean = re.sub(r'(?i)lyon|lille', '', text)
    clean = re.sub(r'69\d{3}|59\d{3}', '', clean)
    clean = re.sub(r'\b\d{1,2}(?:er|e|eme|ème)\b', '', clean)
    if match_p: clean = clean.replace(match_p.group(0), '')
    if match_ch: clean = clean.replace(match_ch.group(0), '')

    clean = clean.replace('Appartement', '').replace('Location', '').replace('à louer', '')
    clean = re.sub(r'\s+', ' ', clean).strip(' -.,')
    result = " - ".join(prefix + [clean]) if clean else " - ".join(prefix)
    return re.sub(r'\s*-\s*', ' - ', result).strip(' -')

# --- 2. CONFIGURATION ---

SCRAPING_CONFIG_PATH = os.path.join(script_dir, '..', '..', 'scripts', 'scraping_config.json')


def load_declared_villes(config_path=SCRAPING_CONFIG_PATH):
    """Villes déclarées dans scraping_config.json (ORA-71) : ajouter une ville
    au JSON suffit, `run_fusion()` la fusionne automatiquement sans changement
    de code ici."""
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    return config['villes']


def load_sites_actifs(config_path=SCRAPING_CONFIG_PATH):
    """Clés des sites actifs (`sites_actifs` de scraping_config.json), ou None si absente
    (= tous les sites). Utilisé comme valeur par défaut de `--sites` en CLI."""
    with open(config_path, encoding='utf-8') as f:
        sites = json.load(f).get('sites_actifs')
    return set(sites) if sites else None


CLES_DOUBLON = ['prix', 'surface', 'prix_m2', 'type', 'code_postal']
DISTANCE_DOUBLON_M = 30
LONGUEUR_MIN_SIGNATURE = 60


def _signature_texte(row):
    """Début du texte libre de l'annonce, normalisé (lettres/chiffres seuls), ou None s'il est
    trop court pour identifier une annonce (les « Details » Vizzit — surface, pièces — sont
    identiques d'un bien à l'autre de même clé : ils ne comptent pas)."""
    for col in ('description_detail', 'description_raw'):
        texte = re.sub(r'[^a-z0-9]', '', str(row.get(col) or '').lower())
        if len(texte) >= LONGUEUR_MIN_SIGNATURE:
            return texte[:80]
    return None


def _distance_m(lat1, lon1, lat2, lon2):
    return (((lat1 - lat2) * 111_000) ** 2 + ((lon1 - lon2) * 111_000 * 0.63) ** 2) ** 0.5  # cos(50,6°) ≈ 0,63


def _sont_doublons(a, b):
    """Même prix/surface/type/CP (déjà vrai ici) ET une preuve d'identité : même début de
    texte libre, même photo, ou positions GPS à moins de DISTANCE_DOUBLON_M m. Sans preuve
    (ex. fiches leboncoin sans texte ni position) : deux annonces distinctes."""
    sa, sb = _signature_texte(a), _signature_texte(b)
    if sa and sa == sb:
        return True
    if a.get('image') and a.get('image') == b.get('image'):
        return True
    coords = [a.get('latitude'), a.get('longitude'), b.get('latitude'), b.get('longitude')]
    if all(pd.notna(c) for c in coords):
        return _distance_m(*[float(c) for c in coords]) <= DISTANCE_DOUBLON_M
    return False


def dedoublonner(df):
    """Retire les vrais doublons (même clé prix/surface/prix_m2/type/CP + preuve d'identité,
    cf. _sont_doublons), en gardant en premier les lignes géolocalisées. Remplace l'ancien
    drop_duplicates sur la seule clé, qui écartait des annonces distinctes de même prix."""
    df = df.sort_values(by=['latitude', 'longitude'], na_position='last')
    gardees = []
    par_cle = {}
    for idx, row in zip(df.index, df.to_dict('records')):
        cle = tuple(row.get(c) if pd.notna(row.get(c)) else None for c in CLES_DOUBLON)
        if any(_sont_doublons(row, autre) for autre in par_cle.get(cle, [])):
            continue
        par_cle.setdefault(cle, []).append(row)
        gardees.append(idx)
    return df.loc[gardees]


def resolve_default_cp(ville_config, ville_nom):
    """CP de repli pour une ville (cf. extract_postal_code). Fail-fast plutôt
    que de retomber silencieusement sur celui de Lyon ("69000") si
    scraping_config.json oublie `code_postal_defaut` pour une ville déclarée
    : un oubli silencieux mélangerait ses annonces non résolues avec celles
    de Lyon sans que rien ne le signale."""
    if 'code_postal_defaut' not in ville_config:
        raise KeyError(
            f"scraping_config.json : 'code_postal_defaut' manquant pour la ville '{ville_nom}'"
        )
    return ville_config['code_postal_defaut']


def site_files_config(slug):
    """Config des fichiers 'classiques' (hors Vizzit) pour une ville donnée,
    à partir de son slug (`scraping_config.json`)."""
    return [
        { 'file': f'annonces_{slug}_century21.csv', 'site': 'Century 21', 'col_prix': 'Prix', 'col_surf': 'Lieu_Surface', 'text_cols': ['Titre', 'Lieu_Surface'], 'col_cp': 'Lieu_Surface', 'col_url': 'Lien' },
        { 'file': f'annonces_{slug}_orpi.csv', 'site': 'Orpi', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre_Lieu', 'Infos'], 'col_cp': 'Titre_Lieu', 'col_url': 'Lien' },
        { 'file': f'annonces_{slug}_pap.csv', 'site': 'PAP', 'col_prix': 'Prix', 'col_surf': 'Détails', 'text_cols': ['Détails'], 'col_cp': 'Lieu', 'col_url': 'Lien' },
        { 'file': f'annonces_{slug}_paruvendu.csv', 'site': 'ParuVendu', 'col_prix': 'Prix', 'col_surf': 'Titre', 'text_cols': ['Titre'], 'col_cp': 'Titre', 'col_url': 'Lien' },
        { 'file': f'annonces_{slug}_seloger.csv', 'site': 'SeLoger', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre', 'Infos'], 'col_cp': 'Lieu', 'col_url': 'Lien' },
    ]

def site_key(nom):
    """'Century 21' -> 'century21' : clé de l'option --sites."""
    return nom.lower().replace(' ', '')


def run_fusion(ville_slug=None, sites=None):
    """Fusionne les CSV scrapés en base_de_donnees_immo_complet.csv.

    Par défaut (`ville_slug=None`), reconstruit le fichier combiné à partir
    de TOUTES les villes déclarées (comportement historique, utilisé par les
    tests et les runs manuels toutes villes confondues).

    Avec `ville_slug`, ne retraite QUE cette ville (ORA-153 : chaque DAG
    annonces tourne désormais indépendamment par ville) — les annonces des
    autres villes déjà présentes dans le fichier combiné sont préservées
    plutôt qu'écrasées.

    `sites` (ensemble de clés `site_key`, ex. {'century21', 'orpi', 'vizzit'}) restreint
    la fusion à ces sites ; None = tous."""
    dfs = []
    print("\n🏗️  DÉMARRAGE DE LA FUSION...\n")
    villes = load_declared_villes()
    if ville_slug is not None:
        villes = {ville_slug: villes[ville_slug]}

    for slug, ville_config in villes.items():
        ville_nom = ville_config['nom']
        default_cp = resolve_default_cp(ville_config, ville_nom)

        # 1. FICHIERS CLASSIQUES
        for config in site_files_config(slug):
            if sites is not None and site_key(config['site']) not in sites:
                continue
            fichier = os.path.join(data_dir, config['file'])
            if os.path.exists(fichier):
                df = pd.read_csv(fichier)
                print(f"--- {ville_nom} / {config['site']} ---")

                new_df = pd.DataFrame()
                new_df['site'] = [config['site']] * len(df)
                new_df['url'] = df[config['col_url']]
                new_df['image'] = df['Image'] if 'Image' in df.columns else ''
                # ORA-134 (TTL par re-scraping) : absente des CSV écrits avant l'ajout
                # de cette colonne aux 6 scrapers, d'où le fallback défensif.
                new_df['date_dernier_scan'] = df['DerniereVue'] if 'DerniereVue' in df.columns else None
                new_df['prix'] = df[config['col_prix']].apply(clean_price_integer)

                full_desc = df[config['text_cols'][0]].fillna('')
                if len(config['text_cols']) > 1:
                    for col in config['text_cols'][1:]:
                        full_desc += " " + df[col].fillna('')
                new_df['description_raw'] = full_desc
                # ORA-161 : texte libre de la page détail (colonne `Description` des CSV
                # scrapés, absente des CSV plus anciens ou de sites sans page détail
                # scrapée : Orpi, Vizzit) ; distincte de `description`, qui reste le
                # texte de carte nettoyé servant à la classification.
                new_df['description_detail'] = df['Description'].fillna('') if 'Description' in df.columns else ''
                new_df['type'] = full_desc.apply(extract_type)

                if config['site'] == 'Orpi':
                    new_df['surface'] = full_desc.apply(clean_surface)
                    new_df['code_postal'] = [
                        extract_postal_code(t, postal_code_from_url(u) or default_cp)
                        for t, u in zip(full_desc, new_df['url'])
                    ]
                elif config['site'] == 'SeLoger':
                    new_df['surface'] = df[config['col_surf']].apply(clean_surface)
                    # Le champ Lieu de SeLoger est parfois un vrai nom de
                    # commune limitrophe (Lambersart, La Madeleine...), pas
                    # seulement Lille — resolve_seloger_lieu() le résout vers
                    # son CP réel (ou None si ni Lieu ni Infos ne donnent de
                    # lieu exploitable, cf. dropna(subset=['code_postal'])
                    # ci-dessous qui exclut alors l'annonce plutôt que de la
                    # localiser au hasard).
                    new_df['code_postal'] = df.apply(
                        lambda row: resolve_seloger_lieu(row[config['col_cp']], row.get('Infos'), default_cp),
                        axis=1,
                    )
                else:
                    new_df['surface'] = df[config['col_surf']].apply(clean_surface)
                    new_df['code_postal'] = df[config['col_cp']].apply(lambda t: extract_postal_code(t, default_cp))

                new_df['ville'] = ville_nom
                new_df['description'] = new_df['description_raw'].apply(format_description)

                new_df['latitude'] = None
                new_df['longitude'] = None

                if config['site'] == 'Century 21':
                    new_df = new_df.drop_duplicates(subset=['prix', 'surface', 'description_raw'])
                else:
                    new_df = new_df.drop_duplicates(subset=['url'])

                new_df = new_df.dropna(subset=['prix', 'code_postal'])
                dfs.append(new_df)
                print(f"   ✅ Ajouté : {len(new_df)} annonces")

        # 2. VIZZIT (fichier GPS séparé)
        vizzit_file = os.path.join(data_dir, f'annonces_{slug}_vizzit_geoloc_complete.csv')
        if os.path.exists(vizzit_file) and (sites is None or 'vizzit' in sites):
            print(f"--- {ville_nom} / Vizzit (GPS) ---")
            df_v = pd.read_csv(vizzit_file)

            v_df = pd.DataFrame()
            v_df['site'] = ['Vizzit'] * len(df_v)
            v_df['url'] = df_v['Lien']
            v_df['image'] = df_v['Image'] if 'Image' in df_v.columns else ''
            v_df['date_dernier_scan'] = df_v['DerniereVue'] if 'DerniereVue' in df_v.columns else None
            v_df['prix'] = df_v['Prix'].apply(clean_price_integer)

            v_df['description_raw'] = df_v['Details']
            # ORA-161/ORA-180 : le fichier GPS n'a pas la page détail ; on la reprend du
            # CSV de scraping (même `Lien`). Absent → '' comme avant.
            v_df['description_detail'] = ''
            vizzit_detail_file = os.path.join(data_dir, f'annonces_{slug}_vizzit.csv')
            if os.path.exists(vizzit_detail_file):
                detail = pd.read_csv(vizzit_detail_file)
                if 'Description' in detail.columns:
                    par_url = detail.drop_duplicates('Lien').set_index('Lien')['Description']
                    v_df['description_detail'] = df_v['Lien'].map(par_url).fillna('')
            v_df['type'] = df_v['Details'].apply(extract_type)
            v_df['surface'] = df_v['Details'].apply(clean_surface)
            v_df['code_postal'] = df_v['Lieu'].apply(lambda t: extract_postal_code(t, default_cp))
            v_df['ville'] = ville_nom
            v_df['description'] = df_v['Details'].apply(format_description)

            v_df['latitude'] = df_v['Lat']
            v_df['longitude'] = df_v['Lon']

            v_df = v_df.drop_duplicates(subset=['url'])
            v_df = v_df.dropna(subset=['prix'])

            dfs.append(v_df)
            print(f"   ✅ Ajouté : {len(v_df)} annonces (avec GPS)")

    # --- 3. FUSION ET EXPORT ---
    if dfs:
        master_df = pd.concat(dfs, ignore_index=True)

        master_df = master_df[master_df['prix'] < 3500]
        condition_coloc = (master_df['prix'] < 800) & (master_df['surface'] > 60)
        master_df = master_df[~condition_coloc]
        master_df = master_df[master_df['surface'] > 9]

        master_df['prix_m2'] = master_df.apply(
            lambda row: round(row['prix'] / row['surface'], 2) if row['surface'] and row['surface'] > 9 else None, axis=1
        )

        cols = ['site', 'prix', 'surface', 'prix_m2', 'type', 'description', 'description_raw', 'description_detail', 'code_postal', 'ville', 'latitude', 'longitude', 'url', 'image', 'date_dernier_scan']
        master_df['description_detail'] = master_df['description_detail'].fillna('')
        # Texte non nettoyé : `description` a perdu « Lyon 3e »/« Lille »/CP
        # (format_description), or clean_immo.step_geocoding en a besoin.
        master_df['description_raw'] = master_df['description_raw'].fillna('')
        master_df = master_df[cols]

        output_file = os.path.join(data_dir, 'base_de_donnees_immo_complet.csv')

        if ville_slug is not None and os.path.exists(output_file):
            # Fusion partielle (une seule ville) : préserve les annonces des
            # autres villes déjà présentes dans le fichier combiné plutôt que
            # de les écraser (ORA-153).
            existing = pd.read_csv(output_file)
            existing = existing.drop(columns=['id_annonce'], errors='ignore')
            ville_nom = villes[ville_slug]['nom']
            existing = existing[existing['ville'] != ville_nom]
            master_df = pd.concat([existing, master_df], ignore_index=True)

        avant = len(master_df)
        master_df = dedoublonner(master_df)
        print(f"   🧹 {avant - len(master_df)} vrai(s) doublon(s) retiré(s) (même clé + même texte, photo ou position).")

        master_df.index = master_df.index + 1
        master_df.reset_index(inplace=True)
        master_df = master_df.rename(columns={'index': 'id_annonce'})
        master_df = master_df[['id_annonce'] + cols]

        master_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        print("\n" + "="*50)
        print(f"🎉 FUSION TERMINÉE ! Fichier généré : {output_file}")
        print(f"📊 Total après dédoublonnage : {len(master_df)} annonces.")
        print("="*50)
    else:
        print("❌ Aucun fichier n'a été traité.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fusionne les CSV d'annonces scrapées en un fichier combiné.")
    parser.add_argument('--ville', default=None, help="Slug de la ville (cf. scraping_config.json). Par défaut : toutes les villes déclarées.")
    parser.add_argument('--sites', default=None, help="Sites à fusionner, séparés par des virgules (ex: century21,orpi,vizzit). Par défaut : `sites_actifs` de scraping_config.json.")
    args = parser.parse_args()

    run_fusion(args.ville, set(args.sites.split(',')) if args.sites else load_sites_actifs())
