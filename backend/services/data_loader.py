# backend/services/data_loader.py
import pandas as pd
import requests
import os
from services.utils import guess_room_count_smart

class DataLoader:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.immo_path = os.path.join(data_dir, "master_immo_final.csv")
        self.cav_path = os.path.join(data_dir, "cavaliers_lyon.csv")
        
        # Stockage (Cache)
        self.df_immo = pd.DataFrame()
        self.df_cav = pd.DataFrame()
        self.metro_geojson = None

    def load_csvs(self):
        """Charge les fichiers CSV locaux."""
        # 1. IMMO
        if os.path.exists(self.immo_path):
            self.df_immo = pd.read_csv(self.immo_path)
            for c in ['latitude', 'longitude', 'prix', 'surface']:
                if c not in self.df_immo.columns: self.df_immo[c] = 0
            self.df_immo = self.df_immo.fillna(0)
            self.df_immo['nb_pieces'] = self.df_immo.apply(guess_room_count_smart, axis=1)
            print(f"✅ Data: {len(self.df_immo)} annonces immo chargées.")
        else:
            print("⚠️ Data: Fichier Immo introuvable.")

        # 2. CAVALIERS
        if os.path.exists(self.cav_path):
            self.df_cav = pd.read_csv(self.cav_path)
            print(f"✅ Data: {len(self.df_cav)} lieux (Cavaliers) chargés.")
        else:
            print("⚠️ Data: Fichier Cavaliers introuvable.")

    def fetch_tcl_api(self):
        """Récupère le tracé métro via API."""
        print("📡 Data: Connexion API Grand Lyon...")
        url = "https://data.grandlyon.com/geoserver/sytral/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=tcl_sytral.tcllignemf&outputFormat=application/json"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                self.metro_geojson = r.json()
                print("✅ Data: Tracé Métro chargé.")
            else:
                print(f"⚠️ Data: Erreur API {r.status_code}")
        except Exception as e:
            print(f"❌ Data: Échec connexion API ({e})")