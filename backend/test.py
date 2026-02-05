import pandas as pd
import re

# Chargement
df = pd.read_csv('data/annonces_lyon_vizzit.csv')

# Configuration
# Ajout du 'r' devant les abréviations qui contiennent un '\'
way_types = [
    "Rue", r"R\.", "Avenue", r"Av\.", "Boulevard", "Bd", "Place", r"Pl\.",
    "Allée", "Cours", "Chemin", "Montée", "Route", "Quai", "Impasse"
]
way_types_pattern = "|".join(way_types)

# Mots déclenchant l'exclusion (s'ils précèdent l'adresse)
forbidden_prefixes = ["proche", "près", "angle", "vue sur", "donnant sur", "côté", "face à", "quartier", "secteur"]

# Mots marquant la fin de l'adresse (stop words)
stop_words_list = [
    r"\.", r",", r";", r":", r"!", r"\?", r"\(", r"\)", 
    r"\slyon\b", r"\svilleurbanne\b", r"\s69\d{3}", 
    r"\sau\s", r"\sà\s", r"\sen\s", r"\sdans\s", r"\savec\s", r"\spour\s", r"\set\s", 
    r"\sproche\s", r"\ssitué\s", r"\sface\s", r"\sdonnant\s", r"\svue\s", r"\scôté\s", 
    r"\smétro\s", r"\stram\s", r"\sbus\s", r"\scommerces\s", r"\srefait\s", 
    r"\st[1-9]\b", r"\sf[1-9]\b", r"\sdispo", r"\sloyer", r"\s\-\s"
]
stop_words_pattern = re.compile("|".join(stop_words_list), re.IGNORECASE)

def extract_address_v3(text):
    if pd.isna(text):
        return "NaN"
    
    text_clean = re.sub(r'\s+', ' ', text)
    
    # 1. Trouver le DÉBUT d'une adresse potentielle : (Numéro optionnel) + Type de voie
    # Ex: "12 Rue", "Boulevard", "10 bis Avenue"
    start_pattern = rf"\b(?:(?P<num>\d+(?:bis|ter|quater|[a-z])?)[\s,]+)?(?P<type>{way_types_pattern})\b"
    
    for match in re.finditer(start_pattern, text_clean, re.IGNORECASE):
        start_idx = match.start()
        end_idx = match.end()
        
        # 2. Vérification du contexte (Exclusion)
        # On regarde les 40 caractères précédents pour voir s'il y a une mention interdite
        preceding = text_clean[max(0, start_idx-40):start_idx].lower()
        is_forbidden = False
        
        # Cas : "à 5 min", "à 100 m"
        if re.search(r"à\s+\d+\s*(?:min|m\b|km)", preceding):
            is_forbidden = True
            
        if not is_forbidden:
            for prefix in forbidden_prefixes:
                # Vérifie si le texte précédent FINIT par le préfixe interdit
                # (ex: "proche du ", "angle de la ")
                if re.search(rf"{re.escape(prefix)}\s*(?:du|de|des|le|la|l'|d')?\s*$", preceding):
                    is_forbidden = True
                    break
        
        if is_forbidden:
            continue
            
        # 3. Extraction du Nom de la voie
        # On prend le texte après le type de voie et on coupe au premier "stop word"
        rest_of_text = text_clean[end_idx:]
        if not rest_of_text:
            continue
            
        split_match = stop_words_pattern.search(rest_of_text)
        if split_match:
            name_part = rest_of_text[:split_match.start()]
        else:
            name_part = rest_of_text
            
        name_part = name_part.strip()
        
        # Validation finale (longueur min/max)
        if len(name_part) < 2 or len(name_part) > 50:
            continue
            
        return f"{match.group(0).strip()} {name_part}"
        
    return "NaN"

# Application
df['Adresse_Extraite'] = df['Description_A_Propos'].apply(extract_address_v3)
df.to_csv('annonces_lyon_vizzit_cleaned.csv', index=False)