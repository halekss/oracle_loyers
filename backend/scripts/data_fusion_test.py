import pandas as pd
import re
import os

# ==============================================================================
# CONFIGURATION
# ==============================================================================
script_dir = os.path.dirname(os.path.abspath(__file__))
# On remonte d'un niveau pour trouver le dossier data
data_dir = os.path.join(script_dir, '..', 'data')

# ==============================================================================
# 1. MOTEUR D'EXTRACTION D'ADRESSE (Python Pur)
# ==============================================================================

def extract_address_smart(text):
    """
    Extrait l'adresse via des motifs stricts pour éviter les faux positifs.
    Fonctionne sans IA, instantané et déterministe.
    """
    if pd.isna(text) or text == "Description non trouvée":
        return ""
    
    # Nettoyage préalable
    text = str(text).replace('\n', ' ').replace('\r', '').strip()
    
    # 1. Définition des vocabulaires
    # Types de voies (complet)
    types_voies = r"(?:rue|avenue|av\.|boulevard|bd|place|cours|quai|montée|route|impasse|allée|chemin|grande rue|promenade|esplanade|passage)"
    
    # Mots d'arrêt (Dès qu'on croise ça, on coupe l'adresse)
    # Cela évite de prendre "Rue de la République proche métro" -> on s'arrête avant "proche"
    stop_words = r"(?:à|vers|proche|dans|tout|très|avec|comprenant|situé|proximité|métro|tram|bus|école|lycée|fac|université|gare|part-dieu|perrache|bellecour|hôtel|ville|lyon|villeurbanne|bron|venissieux|caluire|saint|ref|réf|au\s+coeur|idéalement)"

    # 2. MOTIF A : ADRESSE PRÉCISE (Numéro + Voie + Nom)
    # Ex: "12 rue de la Paix", "10 bis avenue Foch"
    # Structure : 
    #  - \b\d{1,4} : un nombre de 1 à 4 chiffres (bordure de mot)
    #  - (?:bis|ter|quater)? : suffixe optionnel
    #  - \s+ : espace
    #  - (?:types_voies) : le type de rue
    #  - .+? : le nom de la rue (non greedy)
    #  - (?=...) : Lookahead pour s'arrêter sur un stop_word ou une ponctuation
    regex_precise = r"\b(\d{1,4}(?:bis|ter|quater)?\s+(?:" + types_voies + r")\s+[^,.:;?!()]+?)(?=\s+(?:" + stop_words + r")\b|[,.:;?!()]|$)"
    
    match = re.search(regex_precise, text, re.IGNORECASE)
    if match:
        addr = match.group(1).strip()
        # Sécurité : une adresse ne doit pas être trop longue (sinon c'est une phrase)
        if len(addr) < 50: 
            return addr

    # 3. MOTIF B : ADRESSE CONTEXTUELLE (Sans numéro, mais introduite)
    # Ex: "Situé rue de la République", "Sise avenue Jean Jaurès"
    # On oblige un mot déclencheur avant (situé, sis, sur, dans) pour ne pas attraper "une rue calme".
    regex_context = r"(?:situé|sis|sise|au|en|sur|l\'|d\')\s+((?:" + types_voies + r")\s+[^,.:;?!()0-9]+?)(?=\s+(?:" + stop_words + r")\b|[,.:;?!()]|$)"
    
    match = re.search(regex_context, text, re.IGNORECASE)
    if match:
        addr = match.group(1).strip()
        if len(addr) < 50 and len(addr) > 5:
            return addr
            
    return ""

# ==============================================================================
# 2. FONCTIONS DE NETTOYAGE STANDARDS
# ==============================================================================

def clean_price_integer(value):
    if pd.isna(value): return None
    val_str = str(value).lower().replace('€', '').replace('eur', '').replace('cc', '').strip()
    chiffres = re.sub(r'[^\d]', '', val_str)
    if not chiffres: return None
    try: return int(chiffres)
    except: return None

def clean_surface(value):
    if pd.isna(value): return None
    val_str = str(value).replace(',', '.')
    match = re.search(r'(\d+(?:\.\d+)?)\s*m[2²]', val_str, re.IGNORECASE)
    return float(match.group(1)) if match else None

def extract_postal_code(text):
    if pd.isna(text): return "69000"
    text = str(text).lower()
    match_zip = re.search(r'(69\d{3})', text)
    if match_zip: return match_zip.group(1)
    match_arr = re.search(r'lyon\s*(\d{1,2})', text)
    if match_arr: return f"690{int(match_arr.group(1)):02d}"
    return "69000"

def extract_type(text):
    if pd.isna(text): return "Appartement"
    text = str(text).lower()
    if 'colocation' in text: return 'Colocation'
    if 'maison' in text or 'villa' in text: return 'Maison'
    if 'studio' in text: return 'Studio'
    return 'Appartement'

def format_description_general(text):
    if pd.isna(text): return ""
    text = str(text).strip()
    prefix = []
    match_p = re.search(r'(T\d|\d+\s*pi[èe]ce)', text, re.IGNORECASE)
    if match_p: prefix.append(match_p.group(1).capitalize())
    clean = re.sub(r'(?i)lyon', '', text)
    clean = re.sub(r'69\d{3}', '', clean)
    clean = clean.replace('Appartement', '').replace('Location', '').replace('à louer', '')
    clean = re.sub(r'\s+', ' ', clean).strip(' -.,')
    result = " - ".join(prefix + [clean]) if clean else " - ".join(prefix)
    return re.sub(r'\s*-\s*', ' - ', result).strip(' -')

# ==============================================================================
# 3. PIPELINE DE FUSION
# ==============================================================================

fichiers_config = [
    { 'file': 'annonces_lyon_century21.csv', 'site': 'Century 21', 'col_prix': 'Prix', 'col_surf': 'Lieu_Surface', 'text_cols': ['Titre', 'Lieu_Surface'], 'col_cp': 'Lieu_Surface', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_orpi.csv', 'site': 'Orpi', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre_Lieu', 'Infos'], 'col_cp': 'Titre_Lieu', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_pap.csv', 'site': 'PAP', 'col_prix': 'Prix', 'col_surf': 'Détails', 'text_cols': ['Détails'], 'col_cp': 'Lieu', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_paruvendu.csv', 'site': 'ParuVendu', 'col_prix': 'Prix', 'col_surf': 'Titre', 'text_cols': ['Titre'], 'col_cp': 'Titre', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_seloger.csv', 'site': 'SeLoger', 'col_prix': 'Prix', 'col_surf': 'Infos', 'text_cols': ['Titre', 'Infos'], 'col_cp': 'Lieu', 'col_url': 'Lien' },
    { 'file': 'annonces_lyon_vizzit.csv', 'site': 'Vizzit', 'col_url': 'Lien', 'col_prix': 'Prix', 'is_vizzit': True }
]

def run_fusion():
    # Déclaration global pour modifier la variable définie plus haut
    global data_dir 
    
    dfs = []
    print("\n🏗️  DÉMARRAGE DE LA FUSION (Mode Regex Chirurgicale)...")

    # Vérification dossier (gestion fallback si lancé depuis un autre endroit)
    if not os.path.exists(data_dir):
        local_fallback = os.path.join(script_dir, 'backend', 'data')
        if os.path.exists(local_fallback):
            data_dir = local_fallback
        elif os.path.exists(os.path.join(script_dir, 'data')):
            data_dir = os.path.join(script_dir, 'data')
        else:
            print(f"❌ Dossier data introuvable : {data_dir}")
            return
    
    print(f"📂 Dossier données : {os.path.abspath(data_dir)}\n")

    for config in fichiers_config:
        path = os.path.join(data_dir, config['file'])
        
        if os.path.exists(path):
            try: df = pd.read_csv(path, encoding='utf-8-sig')
            except: df = pd.read_csv(path, encoding='latin-1')
            
            print(f"--- {config['site']} ({len(df)}) ---")
            new_df = pd.DataFrame()
            new_df['site'] = [config['site']] * len(df)
            new_df['url'] = df[config['col_url']]
            new_df['prix'] = df[config['col_prix']].apply(clean_price_integer)

            if config.get('is_vizzit'):
                # === TRAITEMENT VIZZIT ===
                # Extraction intelligente de l'adresse
                if 'Description_A_Propos' in df.columns:
                    # On applique notre moteur Regex
                    adresses = df['Description_A_Propos'].apply(extract_address_smart)
                else:
                    adresses = pd.Series([""] * len(df))
                
                # Construction Description
                final_descs = []
                for det, addr in zip(df['Details'].fillna(''), adresses):
                    if addr: final_descs.append(f"{det} - Adresse: {addr}")
                    else: final_descs.append(det)
                
                new_df['description_raw'] = final_descs
                new_df['type'] = df['Details'].apply(extract_type)
                new_df['surface'] = df['Details'].apply(clean_surface)
                new_df['code_postal'] = df['Lieu'].apply(extract_postal_code)
                new_df['ville'] = 'Lyon'
                new_df['description'] = new_df['description_raw'] # Pas de formatage destructif pour Vizzit
                
            else:
                # === TRAITEMENT CLASSIQUE ===
                full_desc = df[config['text_cols'][0]].fillna('')
                if len(config['text_cols']) > 1:
                    for col in config['text_cols'][1:]: full_desc += " " + df[col].fillna('')
                
                new_df['description_raw'] = full_desc
                new_df['type'] = full_desc.apply(extract_type)
                if config['site'] == 'Orpi':
                    new_df['surface'] = full_desc.apply(clean_surface)
                    new_df['code_postal'] = full_desc.apply(extract_postal_code)
                else:
                    new_df['surface'] = df[config['col_surf']].apply(clean_surface)
                    new_df['code_postal'] = df[config['col_cp']].apply(extract_postal_code)
                
                new_df['ville'] = 'Lyon'
                new_df['description'] = new_df['description_raw'].apply(format_description_general)

            # Dédoublonnage
            if config['site'] == 'Century 21':
                new_df = new_df.drop_duplicates(subset=['prix', 'surface', 'description_raw'])
            else:
                new_df = new_df.drop_duplicates(subset=['url'])
            
            new_df = new_df.dropna(subset=['prix'])
            dfs.append(new_df)
            print(f"   ✅ {len(new_df)} annonces traitées.")
        else:
            print(f"⚠️ Fichier absent : {config['file']}")

    if dfs:
        master_df = pd.concat(dfs, ignore_index=True)
        
        # Filtres finaux
        master_df = master_df[master_df['prix'] < 5000]
        master_df = master_df[~((master_df['prix'] < 800) & (master_df['surface'] > 70))]
        master_df = master_df[master_df['surface'] > 8]
        
        # Calcul Prix m2
        master_df['prix_m2'] = master_df.apply(lambda r: round(r['prix']/r['surface'], 2) if r['surface'] else 0, axis=1)
        
        # Indexation
        master_df.index = master_df.index + 1
        master_df.reset_index(inplace=True)
        master_df = master_df.rename(columns={'index': 'id_annonce'})

        # Colonnes finales
        cols = ['id_annonce', 'site', 'prix', 'surface', 'prix_m2', 'type', 'description', 'code_postal', 'ville', 'url']
        master_df = master_df[cols]
        
        out_file = os.path.join(data_dir, 'base_de_donnees_immo_lyon_complet.csv')
        master_df.to_csv(out_file, index=False, encoding='utf-8-sig')
        print(f"\n🎉 SUCCÈS : Fichier généré dans {out_file}")
    else:
        print("❌ ECHEC : Aucun fichier fusionné.")

if __name__ == "__main__":
    run_fusion()