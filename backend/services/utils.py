import numpy as np

def format_prediction_response(estimated_price, price_m2, confidence="N/A"):
    """
    Formate la réponse JSON standardisée pour les prédictions.
    """
    return {
        "estimated_price": round(float(estimated_price), 0),
        "price_m2": round(float(price_m2), 0),
        "confiance": confidence
    }

def clean_input_data(data):
    """
    Nettoie les données entrantes.
    """
    cleaned = {}
    for k, v in data.items():
        try:
            cleaned[k] = float(v)
        except (ValueError, TypeError):
            cleaned[k] = v
    return cleaned

def guess_room_count_smart(surface):
    """
    Devine le type de logement (T1, T2...) basé sur la surface
    si l'information est manquante.
    """
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
    except (ValueError, TypeError):
        return 'Inconnu'