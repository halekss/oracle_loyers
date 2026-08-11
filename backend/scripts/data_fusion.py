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

def run_fusion():
    dfs = []
    print("\n🏗️  DÉMARRAGE DE LA FUSION...\n")
    villes = load_declared_villes()

    for slug, ville_config in villes.items():
        ville_nom = ville_config['nom']
        default_cp = resolve_default_cp(ville_config, ville_nom)

        # 1. FICHIERS CLASSIQUES
        for config in site_files_config(slug):
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
                new_df['type'] = full_desc.apply(extract_type)

                if config['site'] == 'Orpi':
                    new_df['surface'] = full_desc.apply(clean_surface)
                    new_df['code_postal'] = full_desc.apply(lambda t: extract_postal_code(t, default_cp))
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

                new_df = new_df.dropna(subset=['prix'])
                dfs.append(new_df)
                print(f"   ✅ Ajouté : {len(new_df)} annonces")

        # 2. VIZZIT (fichier GPS séparé)
        vizzit_file = os.path.join(data_dir, f'annonces_{slug}_vizzit_geoloc_complete.csv')
        if os.path.exists(vizzit_file):
            print(f"--- {ville_nom} / Vizzit (GPS) ---")
            df_v = pd.read_csv(vizzit_file)

            v_df = pd.DataFrame()
            v_df['site'] = ['Vizzit'] * len(df_v)
            v_df['url'] = df_v['Lien']
            v_df['image'] = df_v['Image'] if 'Image' in df_v.columns else ''
            v_df['date_dernier_scan'] = df_v['DerniereVue'] if 'DerniereVue' in df_v.columns else None
            v_df['prix'] = df_v['Prix'].apply(clean_price_integer)

            v_df['description_raw'] = df_v['Details']
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

        master_df = master_df.sort_values(by=['latitude', 'longitude'], na_position='last')
        colonnes_cles = ['prix', 'surface', 'prix_m2', 'type', 'code_postal']
        master_df = master_df.drop_duplicates(subset=colonnes_cles, keep='first')

        master_df.index = master_df.index + 1
        master_df.reset_index(inplace=True)
        master_df = master_df.rename(columns={'index': 'id_annonce'})

        cols = ['id_annonce', 'site', 'prix', 'surface', 'prix_m2', 'type', 'description', 'code_postal', 'ville', 'latitude', 'longitude', 'url', 'image', 'date_dernier_scan']
        master_df = master_df[cols]

        output_file = os.path.join(data_dir, 'base_de_donnees_immo_complet.csv')
        master_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        print("\n" + "="*50)
        print(f"🎉 FUSION TERMINÉE ! Fichier généré : {output_file}")
        print(f"📊 Total après dédoublonnage : {len(master_df)} annonces.")
        print("="*50)
    else:
        print("❌ Aucun fichier n'a été traité.")

if __name__ == "__main__":
    run_fusion()
