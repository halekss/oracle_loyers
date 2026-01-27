# backend/services/utils.py
import re

def guess_room_count_smart(row):
    """Devine le nombre de pièces depuis la description."""
    text = (str(row.get('titre', '')) + " " + str(row.get('description', ''))).lower()
    surface = float(row.get('surface', 0))
    
    if "studio" in text: return 1
    
    match_t = re.search(r'\b[tf](\d+)\b', text)
    if match_t: return int(match_t.group(1))
    
    if surface < 35: return 1
    if surface < 55: return 2
    if surface < 78: return 3
    if surface < 98: return 4
    return 5