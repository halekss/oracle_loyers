# backend/services/data_loader.py
import pandas as pd
import os
import requests
from services.utils import guess_room_count_smart

class DataLoader:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.immo_path = os.path.join(data_dir, "master_immo_final.csv")
        self.cav_path = os.path.join(data_dir, "cavaliers_lyon.csv")
        
        # Dataframes en mémoire
        self.df_immo = pd.DataFrame()
        self.df_cav = pd.DataFrame()

    def load_csvs(self):
        print("📂 Chargement des fichiers CSV...")
        
        # 1. IMMOBILIER
        if os.path.exists(self.immo_path):
            try:
                df = pd.read_csv(self.immo_path)
                # Nettoyage et typage
                for c in ['latitude', 'longitude', 'prix', 'surface']:
                    if c not in df.columns: df[c] = 0
                
                # On retire les points sans coordonnées (Océan)
                df = df[(df['latitude'] != 0) & (df['longitude'] != 0)]
                
                # Calcul pièces intelligent
                df['nb_pieces'] = df.apply(guess_room_count_smart, axis=1)
                
                self.df_immo = df
                print(f"✅ Immo: {len(self.df_immo)} annonces chargées.")
            except Exception as e:
                print(f"❌ Erreur CSV Immo: {e}")
        else:
            print("⚠️ CSV Immo introuvable.")

        # 2. CAVALIERS
        if os.path.exists(self.cav_path):
            try:
                self.df_cav = pd.read_csv(self.cav_path)
                self.df_cav = self.df_cav[(self.df_cav['latitude'] != 0)]
                print(f"✅ Cavaliers: {len(self.df_cav)} lieux chargés.")
            except Exception as e:
                print(f"❌ Erreur CSV Cavaliers: {e}")