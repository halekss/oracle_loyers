# backend/services/utils.py
import math
import re

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance en mètres entre deux points GPS."""
    R = 6371000  # Rayon de la Terre en mètres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def guess_room_count_smart(row):
    """Devine le nombre de pièces depuis le titre ou la surface."""
    text = (str(row.get('titre', '')) + " " + str(row.get('description', ''))).lower()
    surface = float(row.get('surface', 0))
    
    if "studio" in text: return 1
    
    # Recherche "T2", "F3", etc.
    match_t = re.search(r'\b[tf](\d+)\b', text)
    if match_t: return int(match_t.group(1))
    
    # Fallback sur la surface
    if surface < 35: return 1
    if surface < 55: return 2
    if surface < 78: return 3
    if surface < 98: return 4
    return 5