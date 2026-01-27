import pandas as pd
import os

# Chemins
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
csv_path = os.path.join(base_dir, 'data', 'master_immo_final.csv')

print("🔧 Réparation des IDs en cours...")

# Chargement
df = pd.read_csv(csv_path)
print(f"Avant : {len(df)} annonces, l'ID max est {df['id_annonce'].max()}")

# Réinitialisation (de 1 à N)
df['id_annonce'] = range(1, len(df) + 1)

# Sauvegarde
df.to_csv(csv_path, index=False)
print(f"✅ Après : {len(df)} annonces, l'ID max est bien {df['id_annonce'].max()} !")