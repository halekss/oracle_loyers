import pandas as pd
import os
import re

# --- CONFIGURATION ---
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(base_dir, 'data', 'master_immo_final.csv')

def determine_type_local(row):
    """
    Détermine le type de bien (T1, T2...) en analysant la description
    ou en déduisant via la surface.
    """
    # 1. On concatène type et description pour chercher partout (en minuscule)
    text = (str(row['type']) + " " + str(row['description'])).lower()
    surface = row['surface']

    # --- ÉTAPE A : RECHERCHE PAR MOTS-CLÉS (REGEX) ---
    
    # Grand (T4+ et Maisons)
    # On cherche T4, F4, T5, Maison...
    if re.search(r'\b(t[4-9]|f[4-9]|[4-9]\s*pièce|maison)\b', text):
        return 'Grand (T4+)'
    
    # T3
    if re.search(r'\b(t3|f3|3\s*pièce)\b', text):
        return 'T3'
    
    # T2
    if re.search(r'\b(t2|f2|2\s*pièce)\b', text):
        return 'T2'
    
    # Studio / T1
    if re.search(r'\b(t1|f1|1\s*pièce|studio)\b', text):
        return 'Studio/T1'

    # --- ÉTAPE B : DÉDUCTION PAR SURFACE (Si pas de mots-clés) ---
    # C'est ici que ParuVendu sera géré
    try:
        s = float(surface)
        if s < 35:
            return 'Studio/T1'
        elif s < 55:
            return 'T2'
        elif s < 75:
            return 'T3'
        else:
            return 'Grand (T4+)'
    except:
        return 'Inconnu' # Sécurité ultime

# --- EXÉCUTION ---
print("🕵️  Analyse des types de logements en cours...")

try:
    # Chargement
    df = pd.read_csv(csv_path)
    
    # Application de la fonction ligne par ligne
    df['type_local'] = df.apply(determine_type_local, axis=1)
    
    # Sauvegarde (on écrase le fichier pour le mettre à jour)
    df.to_csv(csv_path, index=False)
    
    print("✅ Succès ! La colonne 'type_local' a été ajoutée.")
    print("\n📊 Répartition des biens trouvés :")
    print(df['type_local'].value_counts())

except Exception as e:
    print(f"❌ Erreur : {e}")