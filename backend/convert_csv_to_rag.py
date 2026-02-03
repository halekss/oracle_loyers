import pandas as pd
import os

print("🔄 Conversion du CSV pour LM Studio RAG...")

# Chemin vers ton CSV
csv_path = "data/master_immo_final.csv"  # Ajuste si besoin

# Vérification
if not os.path.exists(csv_path):
    print(f"❌ ERREUR : Le fichier {csv_path} n'existe pas")
    print("👉 Place ton CSV dans le dossier 'data/' ou modifie le chemin ci-dessus")
    exit()

# Chargement
df = pd.read_csv(csv_path)
print(f"✅ {len(df)} annonces chargées")

# Création du fichier texte optimisé pour LM Studio
output_path = "data/base_connaissance_immo.txt"

with open(output_path, "w", encoding="utf-8") as f:
    for idx, row in df.iterrows():
        # Affichage progression
        if idx % 100 == 0:
            print(f"  → {idx}/{len(df)} annonces converties...")
        
        # Format optimisé pour le RAG
        f.write(f"""
═══════════════════════════════════════════════════════════════
ANNONCE #{row.get('id_annonce', idx)}
═══════════════════════════════════════════════════════════════

📍 LOCALISATION
Ville : {row.get('ville', 'N/A')}
Code postal : {row.get('code_postal', 'N/A')}
Quartier : {row.get('quartier', 'Non renseigné')}
Adresse : {row.get('adresse', 'Non renseignée')}
Coordonnées : {row.get('latitude', 'N/A')}, {row.get('longitude', 'N/A')}

🏠 CARACTÉRISTIQUES DU BIEN
Type : {row.get('type', 'Appartement')}
Surface : {row.get('surface', 'N/A')} m²
Nombre de pièces : {row.get('nb_pieces', 'N/A')}
Prix : {row.get('prix', 'N/A')} €/mois
Prix au m² : {row.get('prix_m2', 'N/A')} €/m²

📝 DESCRIPTION
{row.get('description', 'Pas de description disponible')}

🔊 ENVIRONNEMENT & NUISANCES

Discothèques :
- Distance la plus proche : {row.get('dist_nuisance_discothèque', 'N/A')} m
- Nombre dans un rayon de 500m : {row.get('nb_nuisance_discothèque_500m', 0)}

Écoles :
- Distance la plus proche : {row.get('dist_nuisance_école', 'N/A')} m
- Nombre dans un rayon de 500m : {row.get('nb_nuisance_école_500m', 0)}

Salles de concert :
- Distance la plus proche : {row.get('dist_nuisance_salle_de_concert', 'N/A')} m
- Nombre dans un rayon de 500m : {row.get('nb_nuisance_salle_de_concert_500m', 0)}

Pompes funèbres :
- Distance la plus proche : {row.get('dist_nuisance_pompe_funèbre', 'N/A')} m

🔗 LIEN ANNONCE
{row.get('url', 'Non disponible')}

""")

print(f"\n✅ CONVERSION TERMINÉE !")
print(f"📁 Fichier créé : {output_path}")
print(f"📊 Taille : {len(df)} annonces")
print(f"\n🎯 PROCHAINE ÉTAPE : Importer ce fichier dans LM Studio")