import pandas as pd
import re
import os
import glob
import hashlib

# --- CONFIGURATION ---
SEARCH_DIRS = ["src/scrapers", "src/scraping", "csv_data"]
OUTPUT_FILE = "master_immo_final.csv"

# --- UTILITAIRES ---

def get_ville_from_cp(cp):
    """Déduit le nom de la ville/arrondissement depuis le CP"""
    if not cp or not cp.startswith("690"):
        return "Lyon"
    try:
        arr = int(cp[-2:])
        if 1 <= arr <= 9:
            return f"Lyon {arr}er" if arr == 1 else f"Lyon {arr}ème"
        elif arr > 9: # Lyon 10+ (rare)
             return f"Lyon {arr}ème"
    except:
        pass
    return "Lyon"

def generate_id(source, url, titre):
    """Génère un ID unique court basé sur le contenu"""
    raw = f"{source}{url}{titre}".encode('utf-8')
    return hashlib.md5(raw).hexdigest()[:12]

# --- EXTRACTION ---

def commando_extract(row_values):
    values_clean = [str(v) if pd.notna(v) else "" for v in row_values]
    full_text = " ".join(values_clean)
    
    # NETTOYAGE
    text_clean = full_text.lower().replace(',', '.').replace('\xa0', ' ').replace('\u202f', ' ')
    
    # SURFACE
    surface = 0.0
    match_surf = re.search(r"(\d+(?:\.\d+)?)\s*(?:m\s*2|m²|m\s*carr)", text_clean)
    if match_surf:
        try: surface = float(match_surf.group(1))
        except: pass

    # PRIX
    text_price = text_clean.replace(' ', '') 
    price = 0
    match_euro = re.search(r"(\d{3,5})€", text_price)
    if match_euro:
        price = int(match_euro.group(1).replace('.', ''))
    else:
        match_loyer = re.search(r"loyer.*?(\d{3,5})", text_clean)
        if match_loyer:
             price = int(match_loyer.group(1).replace('.', ''))
        else:
            candidates = re.findall(r"(\d{3,4})", text_clean.replace('.', ''))
            for c in candidates:
                val = int(c)
                if 200 <= val <= 8000:
                    price = val
                    break

    # CP
    cp = "69000"
    match_zip = re.search(r"(69\d{3})", text_clean)
    if match_zip:
        cp = match_zip.group(1)
    else:
        match_lyon = re.search(r"lyon\s*(\d{1,2})", text_clean)
        if match_lyon:
            arr = int(match_lyon.group(1))
            cp = f"6900{arr}" if arr < 10 else f"690{arr}"

    # URL
    url = ""
    for val in values_clean:
        if "http" in val:
            url = val
            break
            
    # DESCRIPTION (On prend le début du texte brut propre)
    description = full_text[:150].replace('\n', ' ').strip()
    
    return description, price, surface, cp, url

# --- MOTEUR ---

def main():
    print("🏗️  Construction de la structure finale...")
    
    all_files = []
    for folder in SEARCH_DIRS:
        all_files.extend(glob.glob(os.path.join(folder, "*.csv")))
    
    if not all_files:
        local_files = glob.glob("*.csv")
        all_files = [f for f in local_files if "master" not in f]

    all_rows = []

    for filepath in all_files:
        filename = os.path.basename(filepath)
        site_name = filename.split('_')[1] if '_' in filename else filename.split('.')[0]
        
        try:
            df = pd.read_csv(filepath, sep=None, engine='python')
            
            for index, row in df.iterrows():
                desc, price, surface, cp, url = commando_extract(row.values)
                
                # Calculs dérivés
                prix_m2 = round(price / surface, 2) if surface > 0 else 0
                ville = get_ville_from_cp(cp)
                id_annonce = generate_id(site_name, url, desc)
                
                if len(desc) > 5:
                    all_rows.append({
                        "id_annonce": id_annonce,
                        "site": site_name,
                        "prix": price,
                        "surface": surface,
                        "prix_m2": prix_m2,
                        "description": desc,
                        "cp": cp,
                        "ville": ville,
                        "url": url,
                        # Métadonnée interne pour le tri
                        "_status": "OK" if price > 0 and surface > 0 else "PARTIAL" 
                    })
                    
        except Exception as e:
            print(f"❌ Erreur sur {filename}: {e}")

    # --- SAUVEGARDE ---
    if all_rows:
        master_df = pd.DataFrame(all_rows)
        
        # Tri : Les annonces complètes d'abord
        master_df.sort_values(by="_status", ascending=False, inplace=True)
        
        # Suppression doublons et colonne temporaire
        master_df = master_df.drop_duplicates(subset=['prix', 'surface', 'description'])
        master_df = master_df.drop(columns=['_status'])
        
        # Réorganisation des colonnes dans l'ordre demandé
        cols_order = ['id_annonce', 'site', 'prix', 'surface', 'prix_m2', 'description', 'cp', 'ville', 'url']
        master_df = master_df[cols_order]
        
        master_df.to_csv(OUTPUT_FILE, index=False)
        
        print("\n" + "="*40)
        print(f"✅ FICHIER GÉNÉRÉ : {OUTPUT_FILE}")
        print(f"📊 {len(master_df)} annonces formatées.")
        print("-" * 40)
        print(master_df.head(3).to_string()) # Aperçu
    else:
        print("❌ Aucune donnée.")

if __name__ == "__main__":
    main()