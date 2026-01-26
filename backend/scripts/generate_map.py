import pandas as pd
import folium
import os

def generate_map():
    print("--- Démarrage de la génération de la carte par calques ---")

    # ==========================================
    # 1. GESTION DES CHEMINS (MODIFIÉ)
    # ==========================================
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1.1 Localisation des données (CSV)
    # On suppose que les données sont dans ../data ou au même endroit
    data_dir = os.path.join(script_dir, '..', 'data')
    if not os.path.exists(data_dir):
        data_dir = script_dir # Fallback au dossier courant

    path_cavaliers = os.path.join(data_dir, "cavaliers_lyon.csv")
    path_immo = os.path.join(data_dir, "master_immo_final.csv")

    # 1.2 Localisation de la sortie (Dossier Public React)
    # C'est ici qu'on change la destination pour viser le frontend
    react_public_dir = os.path.join(script_dir, '..', '..', 'frontend', 'public')

    if os.path.exists(react_public_dir):
        output_dir = react_public_dir
        print(f"✅ Dossier React 'public' trouvé : {output_dir}")
    else:
        print(f"⚠️ Dossier React 'public' introuvable (chemin testé : {react_public_dir})")
        print(f"   -> Sauvegarde par défaut dans : {data_dir}")
        output_dir = data_dir

    path_output = os.path.join(output_dir, "map_pings_lyon_calques.html")

    # ==========================================
    # 2. CHARGEMENT
    # ==========================================
    if not os.path.exists(path_cavaliers):
        print(f"❌ Fichier introuvable : {path_cavaliers}")
        return

    df_cavaliers = pd.read_csv(path_cavaliers)
    
    df_immo = pd.DataFrame()
    if os.path.exists(path_immo):
        df_immo = pd.read_csv(path_immo)

    # ==========================================
    # 3. INITIALISATION DE LA CARTE
    # ==========================================
    center_lat = df_cavaliers['latitude'].mean()
    center_lon = df_cavaliers['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles='CartoDB positron')

    # ==========================================
    # 4. CRÉATION DES GROUPES (CALQUES)
    # ==========================================
    layers = {
        'Vice': folium.FeatureGroup(name="🔴 Vice (Bars, Sex-shops...)"),
        'Gentrification': folium.FeatureGroup(name="🔵 Gentrification (Bio, Yoga...)"),
        'Nuisance': folium.FeatureGroup(name="🟠 Nuisance (Bruit, Pollution)"),
        'Superstition': folium.FeatureGroup(name="🟣 Superstition (Cimetières...)"),
        'Autre': folium.FeatureGroup(name="⚪ Autre")
    }

    def get_style_info(category_str):
        cat = str(category_str).lower()
        if 'vice' in cat:
            return '#e74c3c', 'Vice'          # Rouge
        elif 'gentrification' in cat:
            return '#3498db', 'Gentrification' # Bleu
        elif 'nuisance' in cat:
            return '#f39c12', 'Nuisance'       # Orange
        elif 'superstition' in cat:
            return '#9b59b6', 'Superstition'   # Violet
        else:
            return '#95a5a6', 'Autre'         # Gris

    # ==========================================
    # 5. AJOUT DES POINTS DANS LES BONS CALQUES
    # ==========================================
    print("Répartition des cavaliers dans les calques...")
    
    for _, row in df_cavaliers.iterrows():
        cat = row['categorie_cavalier']
        nom = row['nom_lieu']
        
        color, group_name = get_style_info(cat)
        
        popup_html = f"""
        <div style="font-family: sans-serif; width: 180px;">
            <b>{nom}</b><br>
            <span style="color:{color};">{cat}</span>
        </div>
        """
        
        marker = folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{nom}"
        )
        
        marker.add_to(layers[group_name])

    for layer in layers.values():
        layer.add_to(m)

    # ==========================================
    # 6. AJOUT IMMOBILIER (CALQUE SÉPARÉ)
    # ==========================================
    if not df_immo.empty:
        fg_immo = folium.FeatureGroup(name="🏠 Immobilier", show=False)
        for _, row in df_immo.iterrows():
            try:
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=3,
                    color='#2ecc71',
                    fill=True,
                    fill_opacity=0.6,
                    weight=0,
                    popup=f"Prix: {row.get('prix','?')} €<br>{row.get('surface','?')} m²",
                    tooltip="Annonce"
                ).add_to(fg_immo)
            except: pass
        fg_immo.add_to(m)

    # ==========================================
    # 7. FINALISATION
    # ==========================================
    folium.LayerControl(collapsed=False).add_to(m)
    
    m.save(path_output)
    print(f"🎉 Carte générée avec succès dans : {path_output}")

if __name__ == "__main__":
    generate_map()