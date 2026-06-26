import requests
import json

# L'adresse de ton serveur Flask (vérifie le port, 5000 ou 8000)
# Dans ton app.py tu as mis port=8000 à la fin, donc on utilise 8000
API_URL = "http://127.0.0.1:8000/api/predict"

print(f"📡 Test de connexion vers {API_URL}...")

# 1. On prépare une fausse recherche (comme si on venait de React)
payload = {
    "surface": 45,
    "latitude": 45.7640,  # Quartier Hotel de Ville
    "longitude": 4.8357
}

try:
    # 2. On envoie la demande au serveur
    response = requests.post(API_URL, json=payload)

    # 3. On regarde la réponse
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCÈS ! Immotep a répondu :")
        print("="*40)
        print(f"💰 Loyer Estimé : {data['estimated_price']} {data['currency']}")
        print(f"📐 Prix au m²   : {data['stats']['prix_m2']} €/m²")
        print(f"🧠 Analyse      : {data['analysis']}")
        print(f"🏘️ Type Devinée : {data['details']['type_estime']}")
        print("="*40)
    else:
        print(f"\n❌ ERREUR API (Code {response.status_code}) :")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("\n❌ IMPOSSIBLE DE SE CONNECTER.")
    print("👉 Vérifie que tu as bien lancé 'python backend/app.py' dans un autre terminal !")
