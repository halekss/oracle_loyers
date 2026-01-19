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

# --- VALEURS DE SECOURS ---
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
    
    print(f"🚜 Scan des dossiers dans : {SRC_DIR}")
    csv_files = glob.glob(os.path.join(SRC_DIR, "**", "*.csv"), recursive=True)
    
    if not csv_files:
        print("⚠️ ALERTE : Aucun fichier .csv trouvé !")
        return

    print(f"📄 {len(csv_files)} fichiers CSV trouvés. Analyse en cours...")

    temp_data = {}
    total_annonces = 0
    
    # Compteurs pour comprendre les pertes
    skipped_price = 0
    skipped_location = 0
    skipped_low_price = 0

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                first = f.readline()
                f.seek(0)
                sep = ';' if ';' in first else ','
                
                reader = csv.DictReader(f, delimiter=sep)
                reader.fieldnames = [n.strip() for n in reader.fieldnames]

                for row in reader:
                    try:
                        # 1. Nettoyage Prix
                        p_key = next((k for k in row.keys() if k and "prix" in k.lower()), None)
                        if not p_key: 
                            skipped_price += 1
                            continue
                        
                        raw = row.get(p_key, "0").replace("€", "").replace("CC*", "").replace(" ", "").replace("\u00a0", "").strip()
                        if not raw: 
                            skipped_price += 1
                            continue
                        
                        price = float(raw)
                        
                        # FILTRE PRIX : On abaisse la limite à 100€ pour être sûr
                        if price < 100: 
                            skipped_low_price += 1
                            # print(f"📉 Rejet Prix Bas ({price}€) : {row.get('Titre', 'Sans titre')}")
                            continue 

                        # 2. Localisation (REGEX AMÉLIORÉE)
                        t_key = next((k for k in row.keys() if k and "titre" in k.lower()), None)
                        titre = row.get(t_key, "")
                        
                        # Nouvelle Regex plus large :
                        # Accepte "Lyon 1", "Lyon 01", "Lyon 1er", "Lyon 1ere", "69001", "Lyon-1"
                        # Elle cherche soit "690XX" soit "Lyon...chiffre"
                        match_cp = re.search(r"6900(\d)", titre) # Cherche code postal direct
                        match_lyon = re.search(r"Lyon\D*(\d{1,2})", titre, re.IGNORECASE) # Cherche Lyon + n'importe quoi + chiffre

                        arr = None
                        if match_cp:
                            arr = int(match_cp.group(1))
                        elif match_lyon:
                            arr = int(match_lyon.group(1))

                        if arr and 1 <= arr <= 9:
                            cp = f"690{arr:02d}"
                            
                            # 3. Surface
                            match_m2 = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:m²|m2)", titre, re.IGNORECASE)
                            surface = float(match_m2.group(1).replace(",", ".")) if match_m2 else None

                            if cp not in temp_data: temp_data[cp] = {"prices": [], "m2_rates": []}
                            temp_data[cp]["prices"].append(price)
                            
                            if surface and surface > 9:
                                m2_price = price / surface
                                if 10 < m2_price < 100: 
                                    temp_data[cp]["m2_rates"].append(m2_price)
                                    
                            total_annonces += 1
                        else:
                            skipped_location += 1
                            # Décommenter la ligne suivante pour voir les titres rejetés dans le terminal
                            # print(f"📍 Rejet Localisation : {titre}")

                    except Exception as e:
                        continue
        except Exception as e:
            print(f"❌ Erreur lecture {filename}: {e}")

    # Calcul moyennes
    for cp, d in temp_data.items():
        avg_p = int(mean(d["prices"])) if d["prices"] else 0
        avg_m = round(mean(d["m2_rates"]), 1) if d["m2_rates"] else 0
        MARKET_DATA[cp] = {"price": avg_p, "m2": avg_m, "count": len(d["prices"])}

    print(f"✅ BASE DE DONNÉES PRÊTE : {total_annonces} annonces indexées.")
    if (skipped_location + skipped_price + skipped_low_price) > 0:
        print(f"⚠️  REJETS : {skipped_location} Localisation inconnue | {skipped_low_price} Prix <100€ | {skipped_price} Erreur format")
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
    m = re.search(r"690\d{2}", p.address)
    if m: cp = m.group(0)
    if not cp: cp = get_zip_from_gps(p.lat, p.lon)
    
    if not cp: 
        cp = "69002"
        print("⚠️ Zone inconnue. Utilisation par défaut : 69002")

    # 2. Récupération Prix
    estimated_price = 0
    price_m2 = 0
    note = ""

    if cp in MARKET_DATA:
        data = MARKET_DATA[cp]
        estimated_price = data["price"]
        price_m2 = data["m2"]
        note = f"{price_m2} €/m² (Basé sur {data['count']} annonces)"
        print(f"✅ Source : CSV ({data['count']} annonces)")
    else:
        estimated_price = FALLBACK_PRICES.get(cp, 1200)
        price_m2 = FALLBACK_M2.get(cp, 20.0)
        note = f"{price_m2} €/m² (Estimation Secteur)"
        print(f"⚠️ Source : FALLBACK (Pas d'annonces pour {cp})")

    return {
        "score": 0,
        "message": f"Analyse locative pour le {cp}.",
        "estimated_price": estimated_price,
        "price_note": note,
        "cavaliers": {"gentrification":0, "vice":0, "nuisance":0, "superstition":0},
        "details": {}
    }