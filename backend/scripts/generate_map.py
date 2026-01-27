import folium
import pandas as pd
import os
import json

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Fichiers
IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')
OUTPUT_HTML = os.path.join(DATA_DIR, 'map_pings_lyon_calques.html')

print("🛑 DEBUT GENERATION CARTE...")

# 1. Chargement IMMO
try:
    df_immo = pd.read_csv(IMMO_CSV)
    print(f"✅ IMMO : {len(df_immo)} annonces chargées.")
except Exception as e:
    print(f"❌ IMMO ERREUR : {e}")
    df_immo = pd.DataFrame()

# 2. Chargement CAVALIERS (POI)
try:
    df_poi = pd.read_csv(POI_CSV)
    
    # Harmonisation des noms de colonnes (type vs type_local)
    if 'type' not in df_poi.columns and 'type_local' in df_poi.columns:
        df_poi['type'] = df_poi['type_local']
    
    # DEBUG : Affiche les types trouvés pour être sûr qu'on a les bons noms
    types_trouves = df_poi['type'].unique().tolist() if 'type' in df_poi.columns else []
    print(f"✅ CAVALIERS : {len(df_poi)} lieux chargés.")
    print(f"ℹ️ Types trouvés dans le CSV : {types_trouves[:10]} ...") 
    
except Exception as e:
    print(f"❌ CAVALIERS ERREUR : {e}")
    print(f"⚠️ Vérifie que {POI_CSV} existe bien !")
    df_poi = pd.DataFrame()

# 3. Création de la Carte
m = folium.Map(
    location=[45.7640, 4.8357], 
    zoom_start=13, 
    tiles='CartoDB dark_matter', 
    zoom_control=False # On cache le zoom
)

# 4. Création des Groupes (Noms EXACTS pour React)
fg_immo = folium.FeatureGroup(name='Immo', show=True)
fg_metro = folium.FeatureGroup(name='Metro', show=True)
fg_vice = folium.FeatureGroup(name='Vice', show=True)
fg_gentri = folium.FeatureGroup(name='Gentrification', show=False)
fg_nuisance = folium.FeatureGroup(name='Nuisance', show=False)
fg_superstition = folium.FeatureGroup(name='Superstition', show=False)

# --- A. IMMO (POINTS SIMPLES - PAS DE CLUSTER) ---
print("👉 Ajout des points Immo...")
for _, row in df_immo.iterrows():
    if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
        # Popup simple
        popup_txt = f"{row.get('type_local', 'Bien')} - {row.get('prix', '?')} €"
        
        # On utilise CircleMarker pour des points légers et SANS CLUSTER
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=3,               # Taille du point
            color='#22c55e',        # Contour Vert
            fill=True,
            fill_color='#22c55e',   # Remplissage Vert
            fill_opacity=0.8,
            popup=folium.Popup(popup_txt, max_width=200)
        ).add_to(fg_immo) # Ajout direct au groupe (pas de cluster)

# --- B. MÉTRO ---
if os.path.exists(METRO_JSON):
    print("👉 Ajout du Métro...")
    try:
        with open(METRO_JSON, 'r', encoding='utf-8') as f:
            folium.GeoJson(
                json.load(f), 
                name='Lignes',
                style_function=lambda x: {'color': '#ef4444', 'weight': 3, 'opacity': 0.7}
            ).add_to(fg_metro)
    except Exception as e:
        print(f"⚠️ Erreur JSON Métro : {e}")

# --- C. CAVALIERS (POIs) ---
print("👉 Ajout des Cavaliers...")

# Configuration des couleurs et icones
# Clé = le contenu de la colonne 'type' dans ton CSV (en minuscule)
mapping = {
    # VICE (Rouge)
    'bar': (fg_vice, 'red', 'beer'),
    'sex-shop': (fg_vice, 'red', 'heart'),
    'casino': (fg_vice, 'red', 'star'),
    'tabac': (fg_vice, 'red', 'fire'),
    'cbd_shop': (fg_vice, 'red', 'leaf'),
    
    # GENTRIFICATION (Bleu)
    'salle_sport': (fg_gentri, 'blue', 'heartbeat'),
    'yoga': (fg_gentri, 'blue', 'leaf'),
    'crèche': (fg_gentri, 'blue', 'child'),
    'épicerie_fine': (fg_gentri, 'blue', 'shopping-cart'),
    'torréfacteur': (fg_gentri, 'blue', 'coffee'),
    'atelier_vélo': (fg_gentri, 'blue', 'bicycle'),
    'fleuriste': (fg_gentri, 'blue', 'leaf'),
    'concept store': (fg_gentri, 'blue', 'star'),

    # NUISANCE (Orange)
    'école': (fg_nuisance, 'orange', 'book'),
    'aire de jeux': (fg_nuisance, 'orange', 'futbol-o'), # Attention aux espaces
    'aire_de_jeux': (fg_nuisance, 'orange', 'futbol-o'),
    'salle de concert': (fg_nuisance, 'orange', 'music'),
    'discothèque': (fg_nuisance, 'orange', 'glass'),
    'station service': (fg_nuisance, 'orange', 'car'),
    'station_service': (fg_nuisance, 'orange', 'car'),

    # SUPERSTITION (Violet)
    'pompes funèbres': (fg_superstition, 'purple', 'plus'),
    'pompes_funèbres': (fg_superstition, 'purple', 'plus'),
    'cimetière': (fg_superstition, 'purple', 'plus-square'),
    'lieu de culte': (fg_superstition, 'purple', 'bell'),
    'église': (fg_superstition, 'purple', 'bell'),
}

count_added = 0
for _, row in df_poi.iterrows():
    # Nettoyage du type (minuscule, sans espace inutile)
    raw_type = str(row.get('type', '')).lower().strip()
    
    if raw_type in mapping and pd.notnull(row.get('latitude')):
        group, color, icon_name = mapping[raw_type]
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"<b>{row.get('nom', raw_type)}</b>",
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(group)
        count_added += 1

print(f"✅ {count_added} points d'intérêts placés.")

# --- 5. FINALISATION (HACK JS) ---
fg_immo.add_to(m)
fg_metro.add_to(m)
fg_vice.add_to(m)
fg_gentri.add_to(m)
fg_nuisance.add_to(m)
fg_superstition.add_to(m)

# Ajout du contrôle natif (pour que le JS puisse cliquer dessus)
folium.LayerControl(collapsed=False).add_to(m)

html = m.get_root().render()

# CSS pour cacher le menu blanc + JS pour écouter React
hack_code = """
<style>
    /* On cache le menu moche de Folium */
    .leaflet-control-layers { display: none !important; }
</style>
<script>
    console.log("🗺️ Carte Oracle chargée. Écoute des messages React...");
    window.addEventListener("message", function(e) {
        if (e.data.type === 'TOGGLE_LAYER') {
            console.log("Message reçu pour : " + e.data.name + " -> " + e.data.show);
            var labels = document.getElementsByTagName('label');
            for (var i=0; i<labels.length; i++) {
                // On cherche le label qui contient le nom (ex: "Vice")
                if (labels[i].textContent.trim().includes(e.data.name)) {
                    var box = labels[i].querySelector('input');
                    // Si l'état de la checkbox est différent de l'ordre reçu, on clique
                    if (box && box.checked !== e.data.show) {
                        box.click();
                    }
                    break;
                }
            }
        }
    });
</script>
</body>
"""

html = html.replace('</body>', hack_code)

# Suppression de l'ancien fichier avant écriture (pour être sûr !)
if os.path.exists(OUTPUT_HTML):
    os.remove(OUTPUT_HTML)

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"🎉 TERMINÉ : Carte générée dans {OUTPUT_HTML}")