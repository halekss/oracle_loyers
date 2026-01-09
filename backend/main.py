from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import csv
import re
import glob
from statistics import mean

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# On pointe vers le dossier src pour chercher large
SRC_DIR = os.path.join(BASE_DIR, "src")

# Outil GPS
try:
    import requests
except ImportError:
    requests = None

app = FastAPI(title="Oracle Immo - Data Engine V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- VALEURS DE SECOURS (SI CSV VIDE OU BUG) ---
FALLBACK_PRICES = {
    "69001": 1350, "69002": 1450, "69003": 1150,
    "69004": 1250, "69005": 1200, "69006": 1300,
    "69007": 1100, "69008": 1050, "69009": 1000
}
FALLBACK_M2 = {
    "69001": 22.5, "69002": 24.0, "69003": 19.0,
    "69004": 20.5, "69005": 19.5, "69006": 21.0,
    "69007": 18.0, "69008": 17.0, "69009": 16.5
}

# --- MOTEUR D'INGESTION DATA ---
MARKET_DATA = {}

def load_real_estate_data():
    global MARKET_DATA
    MARKET_DATA = {}
    
    # RECHERCHE RÉCURSIVE : Cherche tous les CSV dans src/ et ses sous-dossiers
    print(f"🚜 Scan des dossiers dans : {SRC_DIR}")
    csv_files = glob.glob(os.path.join(SRC_DIR, "**", "*.csv"), recursive=True)
    
    if not csv_files:
        print("⚠️ ALERTE : Aucun fichier .csv trouvé ! Les prix de secours seront utilisés.")
        return

    print(f"📄 {len(csv_files)} fichiers CSV trouvés. Analyse en cours...")

    temp_data = {}
    total_annonces = 0

    for file_path in csv_files:
        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                # Détection séparateur
                first = f.readline()
                f.seek(0)
                sep = ';' if ';' in first else ','
                
                reader = csv.DictReader(f, delimiter=sep)
                reader.fieldnames = [n.strip() for n in reader.fieldnames]

                for row in reader:
                    try:
                        # 1. Nettoyage Prix
                        p_key = next((k for k in row.keys() if k and "prix" in k.lower()), None)
                        if not p_key: continue
                        
                        raw = row.get(p_key, "0").replace("€", "").replace("CC*", "").replace(" ", "").replace("\u00a0", "").strip()
                        if not raw: continue
                        price = float(raw)
                        if price < 200: continue # Filtre parking

                        # 2. Localisation
                        t_key = next((k for k in row.keys() if k and "titre" in k.lower()), None)
                        titre = row.get(t_key, "")
                        
                        # Regex pour trouver Lyon 1, Lyon 01, Lyon 1er...
                        match = re.search(r"Lyon\s+(\d{1,2})(?:er)?", titre, re.IGNORECASE)
                        if match:
                            arr = int(match.group(1))
                            cp = f"690{arr:02d}"
                            
                            # 3. Surface (m2) dans le titre
                            match_m2 = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:m²|m2)", titre, re.IGNORECASE)
                            surface = float(match_m2.group(1).replace(",", ".")) if match_m2 else None

                            if cp not in temp_data: temp_data[cp] = {"prices": [], "m2_rates": []}
                            temp_data[cp]["prices"].append(price)
                            
                            if surface and surface > 9:
                                m2_price = price / surface
                                if 10 < m2_price < 100: # Filtre aberrations
                                    temp_data[cp]["m2_rates"].append(m2_price)
                                    
                            total_annonces += 1
                    except: continue
        except Exception as e:
            print(f"❌ Erreur lecture {file_path}: {e}")

    # Calcul moyennes
    for cp, d in temp_data.items():
        avg_p = int(mean(d["prices"])) if d["prices"] else 0
        avg_m = round(mean(d["m2_rates"]), 1) if d["m2_rates"] else 0
        MARKET_DATA[cp] = {"price": avg_p, "m2": avg_m, "count": len(d["prices"])}

    print(f"✅ BASE DE DONNÉES PRÊTE : {total_annonces} annonces indexées.")
    print(f"📊 Zones couvertes : {list(MARKET_DATA.keys())}")

load_real_estate_data()

# --- UTILITAIRES ---
def get_zip_from_gps(lat, lon):
    if not requests or not lat: return None
    try:
        url = f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}"
        r = requests.get(url, timeout=2)
        if r.ok and r.json()['features']:
            return r.json()['features'][0]['properties']['postcode']
    except: pass
    return None

class Payload(BaseModel):
    address: str
    lat: float = 0.0
    lon: float = 0.0

@app.post("/api/analyze/vice")
def analyze(p: Payload):
    print(f"🔮 ANALYSE : {p.address}")

    # 1. Identification Zone (CP)
    cp = None
    # A. Via texte
    m = re.search(r"690\d{2}", p.address)
    if m: cp = m.group(0)
    # B. Via GPS
    if not cp: cp = get_zip_from_gps(p.lat, p.lon)
    
    # Si toujours inconnu -> Par défaut Lyon 2
    if not cp: 
        cp = "69002"
        print("⚠️ Zone inconnue. Utilisation par défaut : 69002")

    # 2. Récupération Prix (Priorité: CSV > Fallback)
    estimated_price = 0
    price_m2 = 0
    note = ""

    if cp in MARKET_DATA:
        # Données réelles
        data = MARKET_DATA[cp]
        estimated_price = data["price"]
        price_m2 = data["m2"]
        note = f"{price_m2} €/m² (Basé sur {data['count']} annonces)"
        print(f"✅ Source : CSV ({data['count']} annonces)")
    else:
        # Données de secours
        estimated_price = FALLBACK_PRICES.get(cp, 1200)
        price_m2 = FALLBACK_M2.get(cp, 20.0)
        note = f"{price_m2} €/m² (Estimation Secteur)"
        print(f"⚠️ Source : FALLBACK (Pas d'annonces pour {cp})")

    # 3. Réponse
    return {
        "score": 0,
        "message": f"Analyse locative pour le {cp}.",
        "estimated_price": estimated_price,
        "price_note": note,
        "cavaliers": {"gentrification":0, "vice":0, "nuisance":0, "superstition":0},
        "details": {}
    }