import pandas as pd
import re
import os

# --- 0. CONFIGURATION DES CHEMINS ---
# Le script est dans backend/scripts/
# On remonte d'un niveau (..) pour aller dans backend/data/
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

def extract_postal_code(text):
    """Normalise le CP (6900X)."""
    if pd.isna(text): return "69000"
    text = str(text).lower()
    match_zip = re.search(r'(69\d{3})', text)
    if match_zip: return match_zip.group(1)
    match_arr = re.search(r'lyon\s*(\d{1,2})', text)
    if match_arr: return f"690{int(match_arr.group(1)):02d}"
    return "69000"

def extract_type(text):
    """Détermine le type de bien (Maison, Appartement, Studio, Coloc)."""
    if pd.isna(text): return "Appartement" # Valeur par défaut statistique
    text = str(text).lower()
    
    # Ordre de priorité important (Coloc avant Appartement par ex)
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
    
    # Extraction Pièces / Chambres
    prefix = []
    match_p = re.search(r'(T\d|\d+\s*pi[èe]ce)', text, re.IGNORECASE)
    if match_p: prefix.append(match_p.group(1).capitalize())
    
    match_ch = re.search(r'(\d+\s*chambre)', text, re.IGNORECASE)
    if match_ch: prefix.append(match_ch.group(1).lower())
    
    # Nettoyage geo
    clean = re.sub(r'(?i)lyon', '', text)
    clean = re.sub(r'69\d{3}', '', clean)
    clean = re.sub(r'\b\d{1,2}(?:er|e|eme|ème)\b', '', clean)
    if match_p: clean = clean.replace(match_p.group(0), '')
    if match_ch: clean = clean.replace(match_ch.group(0), '')
    
    # Finition
    clean = clean.replace('Appartement', '').replace('Location', '').replace('à louer', '')
    clean = re.sub(r'\s+', ' ', clean).strip(' -.,')
    
    result = " - ".join(prefix + [clean]) if clean else " - ".join(prefix)
    return re.sub(r'\s*-\s*', ' - ', result).strip(' -')

# --- 2. CONFIGURATION ---

fichiers_config = [
    { 'file': 'annonces_lyon_century21.csv', 'site': 'Century 21', 'col_prix': 'Prix', 'col_surf': 'Lieu_Surface', 'text_cols': ['Titre', 'Lieu_Surface'], 'col_cp': 'Lieu_Surface', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_orpi.csv', 'site': 'Orpi', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre_Lieu', 'Infos'], 'col_cp': 'Titre_Lieu', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_pap.csv', 'site': 'PAP', 'col_prix': 'Prix', 'col_surf': 'Détails', 'text_cols': ['Détails'], 'col_cp': 'Lieu', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_paruvendu.csv', 'site': 'ParuVendu', 'col_prix': 'Prix', 'col_surf': 'Titre', 'text_cols': ['Titre'], 'col_cp': 'Titre', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_seloger.csv', 'site': 'SeLoger', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre', 'Infos'], 'col_cp': 'Lieu', 'col_url': 'Lien' }
]

def run_fusion():
    dfs = []
    print("\n🏗️  DÉMARRAGE DE LA FUSION...\n")

    for config in fichiers_config:
        # Construction du chemin absolu pour chaque fichier
        fichier = os.path.join(data_dir, config['file'])
        
        if os.path.exists(fichier):
            df = pd.read_csv(fichier)
            print(f"--- {config['site']} ---")

            # A. Création des colonnes standardisées
            new_df = pd.DataFrame()
            new_df['site'] = [config['site']] * len(df)
            new_df['url'] = df[config['col_url']]
            new_df['prix'] = df[config['col_prix']].apply(clean_price_integer)
            
            # Concaténation Description pour analyse
            full_desc = df[config['text_cols'][0]].fillna('')
            if len(config['text_cols']) > 1:
                for col in config['text_cols'][1:]:
                    full_desc += " " + df[col].fillna('')
            new_df['description_raw'] = full_desc
            
            # Détection du TYPE
            new_df['type'] = full_desc.apply(extract_type)
            
            # Surface & CP
            if config['site'] == 'Orpi':
                new_df['surface'] = full_desc.apply(clean_surface)
                new_df['code_postal'] = full_desc.apply(extract_postal_code)
            else:
                new_df['surface'] = df[config['col_surf']].apply(clean_surface)
                new_df['code_postal'] = df[config['col_cp']].apply(extract_postal_code)
                
            new_df['ville'] = 'Lyon'
            new_df['description'] = new_df['description_raw'].apply(format_description)

            # B. Dédoublonnage Spécifique
            nb_avant = len(new_df)
            
            if config['site'] == 'Century 21':
                new_df = new_df.drop_duplicates(subset=['prix', 'surface', 'description_raw'])
            elif config['site'] == 'Orpi':
                new_df = new_df.drop_duplicates(subset=['url'])
            else:
                new_df = new_df.drop_duplicates(subset=['url'])
                
            diff = nb_avant - len(new_df)
            if diff > 0: print(f"   ✂️  {diff} doublons supprimés.")

            # C. Nettoyage final
            new_df = new_df.dropna(subset=['prix'])
            
            dfs.append(new_df)
            print(f"   ✅ Ajouté : {len(new_df)} annonces")

        else:
            print(f"❌ Fichier introuvable : {fichier}")

    # --- 3. FUSION ET EXPORT (C'est la partie qu'il te manquait) ---
    if dfs:
        master_df = pd.concat(dfs, ignore_index=True)
        
        # Calcul Prix m2
        master_df['prix_m2'] = master_df.apply(
            lambda row: round(row['prix'] / row['surface'], 2) if row['surface'] and row['surface'] > 9 else None, axis=1
        )

        # ID Unique
        master_df.index = master_df.index + 1
        master_df.reset_index(inplace=True)
        master_df = master_df.rename(columns={'index': 'id_annonce'})

        # ORDRE DES COLONNES
        cols = ['id_annonce', 'site', 'prix', 'surface', 'prix_m2', 'type', 'description', 'code_postal', 'ville', 'url']
        master_df = master_df[cols]

        # SAUVEGARDE DU FICHIER FINAL
        output_file = os.path.join(data_dir, 'base_de_donnees_immo_lyon_complet.csv')
        master_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print("\n" + "="*50)
        print(f"🎉 FUSION TERMINÉE ! Fichier généré : {output_file}")
        print(f"📊 Total : {len(master_df)} annonces.")
        print("="*50)
    else:
        print("❌ Aucun fichier n'a été traité, aucune fusion effectuée.")

if __name__ == "__main__":
    run_fusion()