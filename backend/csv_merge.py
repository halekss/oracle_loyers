import pandas as pd
import re

# Chargement des fichiers
# Remplace par tes vrais noms de fichiers
df_regex = pd.read_csv('annonces_lyon_vizzit_cleaned.csv')  # Ton fichier Regex (~269 adresses)
df_nlp = pd.read_csv('annonces_lyon_vizzit_cleaned_nlp.csv') # Ton fichier NLP (~214 adresses)

# On renomme pour éviter les confusions
df_regex = df_regex.rename(columns={'Adresse_Extraite': 'Addr_Regex'})
df_nlp = df_nlp.rename(columns={'Adresse_Extraite': 'Addr_NLP'})

# Fusion (on suppose que l'ordre des lignes est identique)
# Si l'ordre a changé, il faut fusionner sur une clé unique comme le 'Lien' ou l'index
df_final = df_regex.copy()
df_final['Addr_NLP'] = df_nlp['Addr_NLP']

# Fonction pour évaluer la "force" d'une adresse
def is_precise(addr):
    if pd.isna(addr): return False
    # Une adresse qui commence par un chiffre (ex: "12 Rue...") est jugée plus précise
    return bool(re.match(r"^\d+", str(addr).strip()))

def merge_logic(row):
    reg = row['Addr_Regex']
    nlp = row['Addr_NLP']
    
    # 1. Si les deux sont vides
    if pd.isna(reg) and pd.isna(nlp):
        return None
        
    # 2. Si une seule existe, on la garde
    if pd.isna(reg): return nlp
    if pd.isna(nlp): return reg
    
    # 3. Conflit : Les deux existent. Qui gagne ?
    # Règle : Si NLP a un numéro de rue et Regex non, on prend NLP.
    # Sinon, on garde Regex (souvent plus propre sur le nom de rue).
    if is_precise(nlp) and not is_precise(reg):
        return nlp
        
    return reg

# Application de la fusion
df_final['Adresse_Finale'] = df_final.apply(merge_logic, axis=1)

# Statistiques
total = len(df_final)
found = df_final['Adresse_Finale'].notna().sum()
missing = total - found

print(f"Total lignes : {total}")
print(f"Adresses trouvées après fusion : {found} ({(found/total)*100:.1f}%)")
print(f"Adresses encore manquantes : {missing}")

# Sauvegarde du fichier complet
df_final.to_csv('annonces_lyon_final.csv', index=False)

# Sauvegarde des échecs pour traitement manuel ou LLM
df_missing = df_final[df_final['Adresse_Finale'].isna()]
df_missing[['Description_A_Propos', 'Lien']].to_csv('a_traiter_avec_prompt.csv', index=False)
print("Fichiers 'annonces_lyon_final.csv' et 'a_traiter_avec_prompt.csv' générés.")