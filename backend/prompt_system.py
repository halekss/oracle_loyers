"""
Système de prompts optimisé pour éviter les hallucinations du chatbot.
"""

def build_constrained_prompt(user_message, context=None, history=None, quartiers_data=None):
    """
    Construit un prompt qui force le chatbot à ne dire QUE ce qu'il sait.
    
    Args:
        user_message: Question de l'utilisateur
        context: Contexte ML (prix estimé, etc.)
        history: Historique de conversation
        quartiers_data: Données réelles sur les quartiers de Lyon
    """
    
    # PARTIE 1 : RÈGLES STRICTES
    system_rules = """TU ES L'ORACLE DE LYON - EXPERT IMMOBILIER

🚨 RÈGLES ABSOLUES (NON NÉGOCIABLES):
1. Tu ne DOIS parler QUE de ce qui est dans [DONNÉES FOURNIES]
2. Si une info n'est PAS dans [DONNÉES FOURNIES], tu dis "Je n'ai pas cette info précise"
3. JAMAIS inventer de chiffres, jamais inventer de faits
4. Si on te demande quelque chose hors contexte immobilier Lyon, tu rediriges poliment
5. Tes réponses font MAXIMUM 3-4 phrases courtes

STYLE:
- Cynique mais sympathique
- Argot lyonnais occasionnel (gone, mâchon, bouchon)
- Direct et cash, pas de langue de bois
"""

    # PARTIE 2 : DONNÉES FIABLES
    data_section = "\n[DONNÉES FOURNIES - TA SEULE SOURCE DE VÉRITÉ]\n"
    
    # Ajouter le contexte ML si disponible
    if context:
        data_section += f"""
📊 ESTIMATION ACTUELLE:
{context}
"""
    
    # Ajouter les données des quartiers si disponibles
    if quartiers_data:
        data_section += f"""
📍 DONNÉES QUARTIERS LYON (Prix moyens au m²):
{format_quartiers_data(quartiers_data)}
"""
    
    # Ajouter l'historique de conversation
    if history:
        data_section += f"""
💬 HISTORIQUE CONVERSATION:
{history}
"""
    
    # PARTIE 3 : EXEMPLES DE BONNES/MAUVAISES RÉPONSES
    examples = """
[EXEMPLES - COMMENT RÉPONDRE]

❌ MAUVAIS (Hallucination):
User: "C'est cher la Croix-Rousse ?"
Oracle: "Oui, environ 4200€/m² en moyenne, c'est le quartier le plus cher après le 6ème."
→ PROBLÈME: Invente des chiffres non fournis

✅ BON (Factuel):
User: "C'est cher la Croix-Rousse ?"
Oracle: "Je peux te scanner une zone précise pour te donner le prix exact. Sélectionne sur la carte ou donne-moi une surface."
→ OK: Redirige vers les données réelles

❌ MAUVAIS (Hors sujet):
User: "Quel est le meilleur restaurant de Lyon ?"
Oracle: "Paul Bocuse bien sûr ! Le restaurant 3 étoiles..."
→ PROBLÈME: Hors contexte immobilier

✅ BON (Recentrage):
User: "Quel est le meilleur restaurant de Lyon ?"
Oracle: "Héhé, je suis l'Oracle de l'immo, pas Gault & Millau ! Cherches-tu plutôt un quartier avec pleins de restos ?"
→ OK: Redirige vers l'immobilier avec humour
"""

    # PARTIE 4 : QUESTION UTILISATEUR
    user_section = f"""
[QUESTION DE L'UTILISATEUR]
{user_message}

[TA RÉPONSE - MAX 4 PHRASES]
"""

    # ASSEMBLAGE FINAL
    full_prompt = system_rules + data_section + examples + user_section
    
    return full_prompt


def format_quartiers_data(quartiers_data):
    """
    Formate les données des quartiers pour le prompt.
    """
    formatted = ""
    for quartier, info in quartiers_data.items():
        formatted += f"- {quartier}: {info['prix_m2']}€/m² | {info['description']}\n"
    return formatted


# DONNÉES RÉELLES SUR LYON (à mettre à jour avec vos vraies données)
LYON_QUARTIERS = {
    "1er arrondissement (Pentes/Terreaux)": {
        "prix_m2": 4500,
        "description": "Centre historique, vivant, touristique"
    },
    "2ème arrondissement (Presqu'île)": {
        "prix_m2": 4800,
        "description": "Luxueux, Bellecour, boutiques haut de gamme"
    },
    "3ème arrondissement (Part-Dieu/Guillotière)": {
        "prix_m2": 3600,
        "description": "Gare, bureaux, multiculturel"
    },
    "4ème arrondissement (Croix-Rousse)": {
        "prix_m2": 4200,
        "description": "Bohème, village, pentes, canuts"
    },
    "5ème arrondissement (Vieux-Lyon/Fourvière)": {
        "prix_m2": 4100,
        "description": "Médiéval, touristique, cathédrale"
    },
    "6ème arrondissement (Foch/Tête d'Or)": {
        "prix_m2": 5200,
        "description": "Bourgeois, parc, le plus cher"
    },
    "7ème arrondissement (Gerland/Jean Macé)": {
        "prix_m2": 3800,
        "description": "Moderne, ancien site industriel, stade"
    },
    "8ème arrondissement (Monplaisir/États-Unis)": {
        "prix_m2": 3400,
        "description": "Résidentiel, calme, familial"
    },
    "9ème arrondissement (Vaise/Gorge de Loup)": {
        "prix_m2": 3200,
        "description": "En développement, gare, nouveaux quartiers"
    }
}


# FONCTION POUR DÉTECTER LES QUESTIONS HORS CONTEXTE
def is_off_topic(message):
    """
    Détecte si la question est hors sujet immobilier.
    """
    off_topic_keywords = [
        'restaurant', 'manger', 'sortir', 'cinéma', 'film',
        'météo', 'politique', 'football', 'rugby', 'recette',
        'code', 'programmation', 'mathématiques'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in off_topic_keywords)


# FONCTION POUR EXTRAIRE LES MENTIONS DE QUARTIERS
def extract_quartiers_mentioned(message):
    """
    Trouve les quartiers mentionnés dans le message.
    """
    message_lower = message.lower()
    mentioned = []
    
    keywords = {
        "croix-rousse": "4ème arrondissement (Croix-Rousse)",
        "croix rousse": "4ème arrondissement (Croix-Rousse)",
        "presqu'île": "2ème arrondissement (Presqu'île)",
        "presquile": "2ème arrondissement (Presqu'île)",
        "bellecour": "2ème arrondissement (Presqu'île)",
        "vieux lyon": "5ème arrondissement (Vieux-Lyon/Fourvière)",
        "fourvière": "5ème arrondissement (Vieux-Lyon/Fourvière)",
        "part-dieu": "3ème arrondissement (Part-Dieu/Guillotière)",
        "part dieu": "3ème arrondissement (Part-Dieu/Guillotière)",
        "guillotière": "3ème arrondissement (Part-Dieu/Guillotière)",
        "tête d'or": "6ème arrondissement (Foch/Tête d'Or)",
        "tete d'or": "6ème arrondissement (Foch/Tête d'Or)",
        "foch": "6ème arrondissement (Foch/Tête d'Or)",
        "gerland": "7ème arrondissement (Gerland/Jean Macé)",
        "jean macé": "7ème arrondissement (Gerland/Jean Macé)",
        "vaise": "9ème arrondissement (Vaise/Gorge de Loup)",
    }
    
    for keyword, quartier in keywords.items():
        if keyword in message_lower:
            mentioned.append(quartier)
    
    return list(set(mentioned))  # Dédupliquer