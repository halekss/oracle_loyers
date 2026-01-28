import pandas as pd
import joblib
import os
import random
import numpy as np

# --- CONFIGURATION ---
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, '..', 'models', 'price_predictor.pkl')
data_path = os.path.join(script_dir, '..', 'data', 'master_immo_final.csv')

# --- CHARGEMENT ---
print("🔮 Chargement de l'Oracle (XGBoost)...")
if not os.path.exists(model_path):
    print("❌ Modèle introuvable ! Lancez train_model.py d'abord.")
    exit()

model = joblib.load(model_path)
df = pd.read_csv(data_path)

# --- PRÉPARATION DES DONNÉES DE TEST ---
# On doit faire subir au fichier de test la même torture qu'au fichier d'entraînement

# 1. On nettoie les colonnes inutiles (Texte descriptif)
features_to_drop = ['id_annonce', 'site', 'prix', 'prix_m2', 'url', 'description', 'ville', 'titre', 'date']
X = df.drop(columns=features_to_drop, errors='ignore')

# 2. On supprime les 'nb_'
cols_nb = [c for c in X.columns if c.startswith('nb_')]
X = X.drop(columns=cols_nb)

# 3. ENCODAGE (La partie qui manquait !)
# On transforme le texte en colonnes (One-Hot)
# Cela va créer 'type_local_T2', 'type_Maison', etc.
X = pd.get_dummies(X, drop_first=True)

# 4. ALIGNEMENT MAGIQUE (Le secret pour éviter les bugs)
# Le modèle attend une liste précise de colonnes.
# Si le test n'a pas 'type_Maison' (car pas de maison dans l'échantillon), on crée la colonne avec des 0.
cols_model = model.feature_names_in_
X = X.reindex(columns=cols_model, fill_value=0)

# --- LE JEU DE LA DIVINATION ---
print("\n🎲 Pioche de 5 appartements au hasard...")
random_indices = random.sample(range(len(df)), 5)

for i in random_indices:
    # On récupère la ligne préparée (X) pour la prédiction
    row_encoded = X.iloc[[i]]
    
    # On récupère les infos brutes (df) pour l'affichage humain
    row_raw = df.iloc[i]
    
    # Prédiction
    try:
        prix_estime = model.predict(row_encoded)[0]
    except Exception as e:
        print(f"❌ Erreur : {e}")
        continue

    # Affichage
    vrai_prix = row_raw['prix']
    ecart = prix_estime - vrai_prix
    ecart_percent = (abs(ecart) / vrai_prix) * 100 if vrai_prix > 0 else 0
    
    # On gère l'affichage du type proprement
    type_aff = row_raw.get('type_local', row_raw.get('type', '?'))

    print(f"\n🏠 {type_aff} à {row_raw.get('ville', 'Lyon')} ({row_raw['surface']} m²)")
    print(f"   💰 Vrai Loyer      : {vrai_prix:.0f} €")
    print(f"   🤖 Loyer Estimé    : {prix_estime:.0f} €")
    
    if abs(ecart_percent) < 10:
        print(f"   ✅ Bravo ! (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    elif abs(ecart_percent) < 20:
        print(f"   ⚠️ Pas mal... (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")
    else:
        print(f"   ❌ Aïe, raté. (Écart : {ecart:+.0f} € / {ecart_percent:.1f}%)")

print("\n✨ Fin du test.")