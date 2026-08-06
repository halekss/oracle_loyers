import folium
import pandas as pd
import os
import random
import json
import html
import logging
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("generate_map")

# --- 1. CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BACKEND_DIR, 'data')
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DATA_DIR = os.path.join(PROJECT_ROOT, 'frontend', 'public', 'data')
OUTPUT_HTML = os.path.join(FRONTEND_DATA_DIR, 'map_pings_lyon_calques.html')
METADATA_JSON = os.path.join(FRONTEND_DATA_DIR, 'map_metadata.json')

IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
POI_CSV = os.path.join(DATA_DIR, 'cavaliers_lyon.csv')
METRO_JSON = os.path.join(DATA_DIR, 'metro_lyon.json')

# --- 2. DATA & COULEURS ---
COLORS = {
    'Vice': '#e74c3c', 'Gentrification': '#3b82f6',
    'Nuisance': '#f59e0b', 'Superstition': '#9333ea',
    'Immo': '#22c55e'
}

METRO_COLORS = {
    'A': '#e9003a', 'B': '#0073ba',
    'C': '#f78e1e', 'D': '#009e49',
    'F1': '#888888', 'F2': '#888888'
}


def sanitize_listing_url(url):
    """Ne garde que les URL http(s) valides issues des données scrapées externes."""
    if not isinstance(url, str):
        return None
    candidate = url.strip()
    if not candidate:
        return None
    lowered = candidate.lower()
    if lowered.startswith('http://') or lowered.startswith('https://'):
        return candidate
    return None


def sanitize_image_url(url):
    """Ne garde que les URL http(s) valides pour l'attribut src de l'image (même
    logique que `sanitize_listing_url`) : évite d'interpoler un `javascript:`/
    `data:` arbitraire venu du scraping dans le HTML généré."""
    if not isinstance(url, str):
        return None
    candidate = url.strip()
    if not candidate:
        return None
    lowered = candidate.lower()
    if lowered.startswith('http://') or lowered.startswith('https://'):
        return candidate
    return None


def build_immo_popup_html(type_local, prix, quartier, listing_url=None, image_url=None):
    """Contenu du popup affiché au clic sur un marker d'annonce (ORA-90).

    Affiche la photo d'annonce scrapée telle quelle (hotlink direct vers le
    site source, jamais téléchargée ni re-hébergée sur notre infra) : décision
    ORA-94 (LEGAL_DECISIONS.md) explicitement révisée pour autoriser ce mode
    d'affichage, cf. section "SUPERSEDED" du document.
    """
    safe_type = html.escape(str(type_local))
    safe_prix = html.escape(str(prix))
    safe_quartier = html.escape(str(quartier))

    link_html = ""
    if listing_url:
        safe_link_url = html.escape(listing_url, quote=True)
        link_html = (
            f"<a href='{safe_link_url}' target='_blank' rel='noopener noreferrer' "
            "style='display:block; font-size:12px; color:#22c55e; margin-top:4px;'>Voir l'annonce &#8599;</a>"
        )

    image_html = ""
    safe_image_url = sanitize_image_url(image_url)
    if safe_image_url:
        safe_image_url = html.escape(safe_image_url, quote=True)
        image_html = (
            f"<img src='{safe_image_url}' loading='lazy' referrerpolicy='no-referrer' "
            "style='display:block; width:100%; height:90px; object-fit:cover; border-radius:6px; "
            "margin-bottom:6px;' onerror=\"this.style.display='none'\">"
        )

    return f"""
    <div style='font-family:sans-serif; min-width:160px; max-width:200px;'>
        {image_html}
        <h4 style='margin:0 0 5px 0; color:#22c55e; border-bottom:1px solid #334155; padding-bottom:3px;'>{safe_type}</h4>
        <div style='font-size:15px; font-weight:bold; margin-bottom:5px;'>{safe_prix} €</div>
        <div style='color:#94a3b8; font-size:12px;'>{safe_quartier}</div>
        {link_html}
    </div>
    """


def write_map_metadata(metadata_path, output_html=None, extra=None):
    """Écrit un petit fichier JSON de métadonnées à côté de la carte générée,
    pour exposer un contrôle de fraîcheur (date de dernière génération) visible
    sans avoir à ouvrir la carte elle-même (ORA-54).

    `metadata_path` : chemin du fichier JSON à écrire (ex: .../map_metadata.json)
    `output_html`   : chemin de la carte HTML associée (optionnel, informatif)
    `extra`         : dict de champs additionnels à fusionner dans les métadonnées

    Renvoie le dict de métadonnées écrit.
    """
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    metadata = {"generated_at": generated_at}
    if output_html is not None:
        metadata["map_file"] = os.path.basename(output_html)
    if extra:
        metadata.update(extra)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info("Métadonnées de la carte écrites dans %s (generated_at=%s)", metadata_path, generated_at)
    return metadata


def build_bridge_message_script(map_js_var_name):
    """Génère le script JS qui écoute les messages postMessage envoyés par
    MapComponent.jsx (React) vers la carte Folium embarquée en iframe.

    Contrat documenté dans MAP_CONTRACT.md (ORA-125) : tout nouveau type de
    message doit être ajouté ici ET dans ce document.

    `map_js_var_name` : nom de la variable JS de l'objet Leaflet généré par
    Folium (`m.get_name()`), utilisé pour piloter la carte (ex: FLY_TO).
    """
    return f"""
    window.addEventListener("message", function(e) {{
        if (e.origin !== window.location.origin) {{
            return;
        }}

        if (e.data.type === 'TOGGLE_LAYER') {{
            var labels = document.getElementsByTagName('label');
            for (var i = 0; i < labels.length; i++) {{
                var labelText = labels[i].textContent.trim();
                if (labelText === e.data.name || labelText.includes(e.data.name)) {{
                    var box = labels[i].querySelector('input');
                    if (box && box.checked !== e.data.show) box.click();
                }}
            }}
        }} else if (e.data.type === 'FLY_TO') {{
            {map_js_var_name}.flyTo([e.data.lat, e.data.lng], e.data.zoom || {map_js_var_name}.getZoom());
        }}
    }});
    """


def main():
    # --- 3. CHARGEMENT DONNEES ---
    # A. Immo
    try:
        if os.path.exists(IMMO_CSV):
            df_immo = pd.read_csv(IMMO_CSV, sep=None, engine='python')
            df_immo.columns = df_immo.columns.str.strip().str.lower()
            for col in ['latitude', 'longitude']:
                if col in df_immo.columns: df_immo[col] = pd.to_numeric(df_immo[col], errors='coerce')
        else: df_immo = pd.DataFrame()
    except: df_immo = pd.DataFrame()

    # B. Cavaliers
    df_poi = pd.DataFrame()
    try:
        if os.path.exists(POI_CSV):
            df_poi = pd.read_csv(POI_CSV, sep=None, engine='python')
            df_poi.columns = df_poi.columns.str.strip().str.lower()
            if 'categorie_cavalier' in df_poi.columns: df_poi['type'] = df_poi['categorie_cavalier']
            elif 'type_osm' in df_poi.columns: df_poi['type'] = df_poi['type_osm']
            if 'nom_lieu' in df_poi.columns: df_poi['nom'] = df_poi['nom_lieu']
            for col in ['latitude', 'longitude']:
                if col in df_poi.columns:
                    df_poi[col] = df_poi[col].astype(str).str.replace(',', '.', regex=False)
                    df_poi[col] = pd.to_numeric(df_poi[col], errors='coerce')
    except: pass

    # --- 4. CARTE ---
    print("🛑 GENERATION CARTE (METRO LIGNES AUTO)...")
    m = folium.Map(location=[45.7640, 4.8357], zoom_start=13, tiles='CartoDB dark_matter', zoom_control=False)

    # --- CREATION DES GROUPES ---
    fg_studio = folium.FeatureGroup(name='Immo Studio/T1', show=True)
    fg_t2 = folium.FeatureGroup(name='Immo T2', show=True)
    fg_t3 = folium.FeatureGroup(name='Immo T3', show=True)
    fg_t4 = folium.FeatureGroup(name='Immo Grand (T4+)', show=True)

    # Groupe Métro Unifié
    fg_metro = folium.FeatureGroup(name='Metro', show=True)

    fg_vice = folium.FeatureGroup(name='Vice', show=True)
    fg_gentri = folium.FeatureGroup(name='Gentrification', show=False)
    fg_nuisance = folium.FeatureGroup(name='Nuisance', show=False)
    fg_superstition = folium.FeatureGroup(name='Superstition', show=False)

    # --- 5. GENERATION POINTS IMMO ---
    for _, row in df_immo.iterrows():
        if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
            lat = row['latitude'] + random.uniform(-0.0001, 0.0001)
            lon = row['longitude'] + random.uniform(-0.0001, 0.0001)

            type_local = str(row.get('type_local', '')).strip()
            prix = str(row.get('prix', '?')).replace('.0', '')
            listing_url = sanitize_listing_url(row.get('url'))
            image_url = row.get('image')

            txt_popup = build_immo_popup_html(type_local, prix, row.get('quartier', 'Lyon'), listing_url, image_url)

            target_group = None
            if type_local == 'Studio/T1': target_group = fg_studio
            elif type_local == 'T2': target_group = fg_t2
            elif type_local == 'T3': target_group = fg_t3
            elif type_local == 'Grand (T4+)': target_group = fg_t4

            if target_group:
                # Popup (pas Tooltip) : reste ouvert au clic au lieu de disparaître
                # dès que la souris quitte le marker, ce qui rendait le lien "Voir
                # l'annonce" à l'intérieur impossible à atteindre (ORA-134).
                marker = folium.CircleMarker(
                    [lat, lon], radius=5, color=COLORS['Immo'], weight=1, fill=True, fill_color=COLORS['Immo'], fill_opacity=0.8,
                    popup=folium.Popup(txt_popup, max_width=220, className='oracle-popup'),
                )
                marker.add_to(target_group)

    # --- 6. GESTION DU MÉTRO VIA JSON (LIGNES + STATIONS) ---
    if os.path.exists(METRO_JSON):
        try:
            with open(METRO_JSON, 'r', encoding='utf-8') as f:
                metro_data = json.load(f)

            # Dictionnaire pour stocker les coordonnées par ligne (ex: {'A': [[lat,lon], [lat,lon]...]})
            stations_by_line = {}

            # 1. DESSINER LES STATIONS (ICONES) ET MEMORISER LES POSITIONS
            count_stations = 0
            for feature in metro_data['features']:
                if feature['geometry']['type'] == 'Point':
                    # Données
                    props = feature['properties']
                    coords = feature['geometry']['coordinates']
                    lon, lat = coords[0], coords[1]

                    nom_station = props.get('nom', 'Station')
                    ligne = props.get('ligne', '?')

                    # Sauvegarde pour le tracé de la ligne
                    if ligne not in stations_by_line:
                        stations_by_line[ligne] = []
                    stations_by_line[ligne].append([lat, lon])

                    # Style
                    color = METRO_COLORS.get(ligne, '#888888')
                    popup_txt = f"<b>Station {nom_station}</b><br>Ligne {ligne}"

                    # Icone HTML
                    icon_html = f"""
                    <div style="
                        width: 24px; height: 24px;
                        background: white; border-radius: 50%;
                        display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.5);
                        border: 2px solid white;
                    ">
                        <div style="
                            width: 18px; height: 18px;
                            background: {color}; border-radius: 50%;
                            display: flex; align-items: center; justify-content: center;
                            font-family: sans-serif; font-weight: bold; font-size: 10px; color: white;
                        ">{ligne}</div>
                    </div>
                    """

                    folium.Marker(
                        [lat, lon],
                        icon=folium.DivIcon(html=icon_html, icon_size=(24, 24), icon_anchor=(12, 12)),
                        popup=folium.Popup(popup_txt, max_width=200, className='oracle-popup')
                    ).add_to(fg_metro)
                    count_stations += 1

            # 2. DESSINER LES LIGNES EN RELIANT LES POINTS
            # Si le fichier JSON est bien ordonné, cela reliera les stations dans l'ordre
            for ligne, coords in stations_by_line.items():
                if len(coords) > 1:
                    folium.PolyLine(
                        locations=coords,
                        color=METRO_COLORS.get(ligne, '#888888'),
                        weight=4,
                        opacity=0.6,
                        smooth_factor=1.5 # Adoucit un peu les angles
                    ).add_to(fg_metro)

            print(f"🚇 Métro chargé : {len(stations_by_line)} lignes tracées, {count_stations} stations.")

        except Exception as e:
            print(f"⚠️ Erreur lors du traitement de metro_lyon.json : {e}")

    # --- 7. CAVALIERS ---
    mapping_simple = {'vice': (fg_vice, COLORS['Vice']), 'gentrification': (fg_gentri, COLORS['Gentrification']), 'nuisance': (fg_nuisance, COLORS['Nuisance']), 'superstition': (fg_superstition, COLORS['Superstition'])}
    if 'type' in df_poi.columns:
        for _, row in df_poi.iterrows():
            raw_type = str(row.get('type', '')).lower().strip()
            target_config = None
            for key, config in mapping_simple.items():
                if key in raw_type:
                    target_config = config
                    break
            if target_config and pd.notnull(row.get('latitude')):
                group, color_hex = target_config

                # Nettoyage Type (ex: "Vice - Bar" -> "Bar")
                if ' - ' in raw_type:
                    clean_type = raw_type.split(' - ')[-1].title()
                else:
                    clean_type = raw_type.title()

                txt_popup = f"""
                <div style='font-size: 13px; line-height: 1.4;'>
                    <b style='font-size: 15px; color: #f8fafc;'>{row.get('nom', clean_type)}</b><br>
                    <span style='color: {color_hex}; font-weight: bold;'>{clean_type}</span>
                </div>
                """

                folium.CircleMarker(
                    [row['latitude'], row['longitude']], radius=5, color=color_hex, weight=1, fill=True, fill_color=color_hex, fill_opacity=0.8,
                    popup=folium.Popup(txt_popup, max_width=200, className='oracle-popup')
                ).add_to(group)

    # --- 8. RENDU ---
    fg_studio.add_to(m)
    fg_t2.add_to(m)
    fg_t3.add_to(m)
    fg_t4.add_to(m)
    fg_metro.add_to(m) # Groupe Unique
    fg_vice.add_to(m)
    fg_gentri.add_to(m)
    fg_nuisance.add_to(m)
    fg_superstition.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    html_out = m.get_root().render()

    # --- 9. HACK CSS/JS (POPUPS, CONTROLE CALQUES) ---
    hack = f"""
    <style>
        .leaflet-control-layers {{ display: none !important; }}

        /* STYLE POPUP DARK */
        .leaflet-popup-content-wrapper, .leaflet-popup-tip,
        .leaflet-tooltip.oracle-popup {{
            background-color: #0f172a !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
            border-radius: 12px !important;
        }}
        .leaflet-popup-close-button {{ color: #94a3b8 !important; }}
        .leaflet-popup-close-button:hover {{ color: #f8fafc !important; }}
        .leaflet-interactive {{ cursor: pointer !important; }}
    </style>

    <script>
    {build_bridge_message_script(m.get_name())}
    </script>
    </body>
    """

    html_out = html_out.replace('</body>', hack)

    if not os.path.exists(FRONTEND_DATA_DIR):
        os.makedirs(FRONTEND_DATA_DIR)

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f"🎉 TERMINÉ : {OUTPUT_HTML} (Métro : Lignes reliées automatiquement)")

    # --- 10. CONTRÔLE DE FRAÎCHEUR (ORA-54) ---
    # Écrit map_metadata.json à côté de la carte, avec la date de génération,
    # pour détecter facilement une carte périmée si le pipeline de données change.
    write_map_metadata(METADATA_JSON, output_html=OUTPUT_HTML)


if __name__ == "__main__":
    main()
