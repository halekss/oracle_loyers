import requests as r
import json

URL = "http://127.0.0.1:5000/api/predict"

# Simulation : L'utilisateur a tapé "Part Dieu", le React a trouvé ces coordonnées
payload = {
    "latitude": 45.760, 
    "longitude": 4.855,
    "surface": 40
}

print("🌍 Envoi d'une position (Part Dieu)...")
rep = r.post(URL, json=payload)

if rep.status_code == 200:
    data = rep.json()
    print(f"\n💰 Loyer estimé : {data['estimated_price']} €")
    print(f"📏 Prix m² : {data['price_m2']} €/m²")
    print("\n💬 L'IA te parle :")
    for msg in data['analysis']:
        print(f"   {msg}")
    print(f"\n(Debug: {data['info_debug']})")
else:
    print("Erreur:", rep.text)