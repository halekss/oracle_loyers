import logging
import pandas as pd
import os
from services.utils import guess_room_count_smart

logger = logging.getLogger(__name__)


class DataLoader:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None
        self.load_data()

    def load_data(self):
        """Charge le CSV en mémoire et applique un nettoyage de base."""
        if not os.path.exists(self.csv_path):
            logger.error("Fichier de données introuvable : %s", self.csv_path)
            return

        try:
            self.df = pd.read_csv(self.csv_path)
            
            # Nettoyage et conversion des types essentiels
            if 'surface' in self.df.columns:
                self.df['surface'] = pd.to_numeric(self.df['surface'], errors='coerce')
            
            if 'prix' in self.df.columns:
                self.df['prix'] = pd.to_numeric(self.df['prix'], errors='coerce')
                
            # Remplissage intelligent des types manquants
            if 'type_local' in self.df.columns and 'surface' in self.df.columns:
                # On applique la fonction seulement là où type_local est manquant
                mask_missing = self.df['type_local'].isna()
                self.df.loc[mask_missing, 'type_local'] = self.df.loc[mask_missing, 'surface'].apply(guess_room_count_smart)

            logger.info("Données chargées : %s annonces.", len(self.df))

        except Exception as e:
            logger.error(
                "Erreur lors du chargement des données (%s) : %s - %s",
                self.csv_path, type(e).__name__, e, exc_info=True,
            )

    def get_data(self):
        """Renvoie le DataFrame brut."""
        return self.df