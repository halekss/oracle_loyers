import pandas as pd
import spacy
import re

# ---------------------------------------------------------
# 1. CHARGEMENT DU MODÈLE NLP
# ---------------------------------------------------------
print("Chargement du modèle SpaCy (fr_core_news_lg)...")
try:
    nlp = spacy.load("fr_core_news_lg")
except OSError:
    print("Modèle 'lg' non trouvé, essai avec 'sm'...")
    nlp = spacy.load("fr_core_news_sm")

# ---------------------------------------------------------
# 2. CONFIGURATION DES MOTS-CLÉS & REGEX
# ---------------------------------------------------------
# Vocabulaire élargi pour aider le filtre post-NER
street_keywords = [
    "rue", "avenue", "boulevard", "bd", "place", "allée", "cours", "chemin", 
    "montée", "route", "quai", "impasse", "passage", "esplanade", "promenade", 
    "grande rue", "faubourg", "villa", "cité", "ruelle", "corniche"
]

# Regex strict (le même qu'avant, mais avec le vocabulaire enrichi)
way_pattern = "|".join([re.escape(k) for k in street_keywords] + [r"r\.", r"av\.", r"pl\.", r"bd\."])
regex_full = rf"\b(?P<num>\d+(?:bis|ter|[a-z])?)[\s,]+(?P<type>{way_pattern})\s+(?P<name>[A-ZÀ-Ÿ0-9].*?)(?=[,.]|$|\s(?:au|à|en|dans|proche|situé))"

# Mots d'exclusion contextuelle (pour éviter "Proche de la rue X")
forbidden_context = ["proche", "près", "angle", "vue sur", "face à", "quartier", "secteur", "métro", "tram", "gare"]

# ---------------------------------------------------------
# 3. FONCTIONS D'EXTRACTION
# ---------------------------------------------------------

def is_context_safe(text, start_index):
    """Vérifie si le texte précédant l'adresse contient des mots interdits (proche, vue, etc.)"""
    window = text[max(0, start_index-30):start_index].lower()
    
    # Vérification des distances (ex: "à 5 min")
    if re.search(r"à\s+\d+\s*(?:min|m\b)", window):
        return False
        
    for word in forbidden_context:
        # Vérifie si le mot interdit est juste avant (ex: "proche du")
        if re.search(rf"{word}\s*(?:du|de|des|le|la|l')?\s*$", window):
            return False
    return True

def extract_address_hybrid(text):
    if pd.isna(text):
        return "NaN"
    
    clean_text = re.sub(r'\s+', ' ', text) # Nettoyage espaces
    
    # --- PHASE 1 : REGEX STRICT (Haute Précision) ---
    match = re.search(regex_full, clean_text, re.IGNORECASE)
    if match:
        if is_context_safe(clean_text, match.start()):
            return match.group(0).strip()
    
    # --- PHASE 2 : NLP SPACY (Rattrapage Intelligent) ---
    # Si le regex n'a rien trouvé, on lance l'IA
    doc = nlp(clean_text)
    
    candidate_addresses = []
    
    for ent in doc.ents:
        # On ne s'intéresse qu'aux Lieux (LOC)
        if ent.label_ == "LOC":
            ent_text = ent.text.strip()
            ent_lower = ent_text.lower()
            
            # FILTRE 1 : Doit contenir un mot-clé de rue (pour éviter "Lyon", "Rhône", "Part-Dieu")
            # Ou commencer par un chiffre (ex: "12 Gambetta")
            has_street_keyword = any(k in ent_lower for k in street_keywords)
            starts_with_digit = re.match(r"^\d+", ent_text)
            
            if (has_street_keyword or starts_with_digit) and len(ent_text) > 4:
                # FILTRE 2 : Vérification contextuelle (pas de "proche de", "vue sur")
                # On cherche la position de l'entité dans le texte original
                start_idx = clean_text.find(ent.text)
                if start_idx != -1 and is_context_safe(clean_text, start_idx):
                     # FILTRE 3 : Exclusion des noms trop génériques ou villes seules
                    if ent_lower not in ["lyon", "villeurbanne", "le rhône", "france"]:
                        candidate_addresses.append(ent_text)

    # Si on a trouvé des candidats via NLP, on prend le premier (souvent le plus pertinent)
    if candidate_addresses:
        return candidate_addresses[0]

    return "NaN"

# ---------------------------------------------------------
# 4. EXÉCUTION
# ---------------------------------------------------------
print("Lecture du CSV...")
df = pd.read_csv('data/annonces_lyon_vizzit.csv') # Utilise le fichier original

print("Extraction des adresses en cours (ça peut prendre un peu de temps avec le NLP)...")
df['Adresse_Extraite'] = df['Description_A_Propos'].apply(extract_address_hybrid)

# Stats
missing = df['Adresse_Extraite'].value_counts().get("NaN", 0)
print(f"Lignes traitées : {len(df)}")
print(f"Adresses manquantes (NaN) : {missing}")
print(f"Taux de succès : {((len(df)-missing)/len(df))*100:.2f}%")

# Sauvegarde
df.to_csv('annonces_lyon_vizzit_cleaned_nlp.csv', index=False)
print("Fichier sauvegardé : annonces_lyon_vizzit_cleaned_nlp.csv")