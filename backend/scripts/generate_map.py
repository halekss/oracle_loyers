import argparse
import folium
import pandas as pd
import os
import random
import sys
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

IMMO_CSV = os.path.join(DATA_DIR, 'master_immo_final.csv')
ANNONCES_DB_PATH = os.path.join(DATA_DIR, 'annonces.db')

# Une carte HTML statique par ville (ORA-71 POC) : `metro_json`/`quartiers_geojson`
# sont optionnels, absents pour une ville tant que sa couche correspondante n'a
# pas été produite (chargement gracieux existant, cf. load_geojson_file et le
# `if os.path.exists(METRO_JSON)` plus bas).
VILLE_CONFIG = {
    'lyon': {
        'output_html': 'map_pings_lyon_calques.html',
        'metadata_json': 'map_metadata_lyon.json',
        'poi_csv': 'cavaliers_lyon.csv',
        'metro_json': 'metro_lyon.json',
        # Limites des 9 arrondissements de Lyon (OSM/Nominatim), récupérées une
        # fois par scripts/fetch_lyon_arrondissements.py et versionnées (ORA-104).
        'quartiers_geojson': 'lyon_arrondissements.geojson',
        'center': [45.7640, 4.8357],
    },
    'lille': {
        'output_html': 'map_pings_lille_calques.html',
        'metadata_json': 'map_metadata_lille.json',
        'poi_csv': 'cavaliers_lille.csv',
        'metro_json': 'metro_lille.json',
        'quartiers_geojson': 'lille_quartiers.geojson',
        'center': [50.6292, 3.0573],
    },
}

# Source de vérité unique de la liste des calques carte (nom Folium/TOGGLE_LAYER,
# visibilité par défaut, libellé et couleur du panneau React) : consommée ici
# ET par MapComponent.jsx (import JS direct du même fichier), pour ne plus
# avoir à synchroniser LAYER_MAPPING (React) et les FeatureGroup/GeoJson
# (Python) à la main à chaque nouveau calque (ORA-130, lié à ORA-125) —
# partagée par toutes les villes, pas de déclinaison par ville.
LAYERS_CONFIG_JSON = os.path.join(PROJECT_ROOT, 'frontend', 'src', 'config', 'mapLayers.config.json')


def resolve_ville_paths(ville):
    """Résout les chemins absolus (HTML de sortie, métadonnées, POI, métro,
    GeoJSON quartiers) et le centre de carte pour une ville déclarée dans
    VILLE_CONFIG. Lève KeyError si la ville n'est pas déclarée (fail-fast
    plutôt qu'un repli silencieux vers Lyon)."""
    config = VILLE_CONFIG[ville]
    return {
        "output_html": os.path.join(FRONTEND_DATA_DIR, config['output_html']),
        "metadata_json": os.path.join(FRONTEND_DATA_DIR, config['metadata_json']),
        "poi_csv": os.path.join(DATA_DIR, config['poi_csv']),
        "metro_json": os.path.join(DATA_DIR, config['metro_json']),
        "quartiers_geojson": os.path.join(DATA_DIR, config['quartiers_geojson']),
        "center": config['center'],
    }


def filter_by_ville(df_immo, ville):
    """Filtre les annonces sur la ville demandée (comparaison insensible à la
    casse). Si la colonne `ville` est absente (données pas encore migrées),
    renvoie le DataFrame inchangé plutôt que de tout faire disparaître."""
    if 'ville' not in df_immo.columns:
        return df_immo
    return df_immo[df_immo['ville'].str.lower() == ville.lower()]
# Source de vérité unique de la liste des calques carte (nom Folium/TOGGLE_LAYER,
# visibilité par défaut, libellé et couleur du panneau React) : consommée ici
# ET par MapComponent.jsx (import JS direct du même fichier), pour ne plus
# avoir à synchroniser LAYER_MAPPING (React) et les FeatureGroup/GeoJson
# (Python) à la main à chaque nouveau calque (ORA-130, lié à ORA-125).
LAYERS_CONFIG_JSON = os.path.join(PROJECT_ROOT, 'frontend', 'src', 'config', 'mapLayers.config.json')

# backend/services (annonces_store) n'est pas sur sys.path par défaut quand ce
# script est lancé depuis backend/scripts/ (ex: `python generate_map.py`, ou
# l'étape DAG Airflow `generate_map`) plutôt que depuis backend/ (comme app.py).
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from services import annonces_store  # noqa: E402 (après le sys.path.insert nécessaire)

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


def build_immo_tooltip_html(type_local, prix):
    """Aperçu léger affiché au survol d'un marker d'annonce (ORA-99).

    Volontairement sans lien ni action : un tooltip Leaflet (quel que soit son
    mode, sticky ou non) se ferme au `mouseout` du marker, pas selon si la
    souris est sur le tooltip lui-même — impossible d'y héberger un lien
    cliquable de façon fiable. Le lien reste réservé au popup au clic
    (cf. build_immo_popup_html)."""
    safe_type = html.escape(str(type_local))
    safe_prix = html.escape(str(prix))

    return f"""
    <div style='font-family:sans-serif; font-size:12px; white-space:nowrap;'>
        <b style='color:#22c55e;'>{safe_type}</b> — {safe_prix} €
    </div>
    """


def build_immo_popup_html(type_local, prix, quartier, listing_url=None, image_url=None, annonce_id=None):
    """Contenu du popup affiché au clic sur un marker d'annonce (ORA-90).

    Affiche la photo d'annonce scrapée telle quelle (hotlink direct vers le
    site source, jamais téléchargée ni re-hébergée sur notre infra) : décision
    ORA-94 (LEGAL_DECISIONS.md) explicitement révisée pour autoriser ce mode
    d'affichage, cf. section "SUPERSEDED" du document.

    `annonce_id` (id SQLite dans annonces.db, résolu par url dans main() via
    annonces_store.get_annonce_by_url) : si connu, le clic sur le lien
    notifie le parent React via postMessage (contrat ANNONCE_CLICK,
    MAP_CONTRACT.md) plutôt que d'appeler directement l'API backend depuis ce
    HTML statique, qui n'a pas connaissance de son URL (ORA-107/ORA-126) —
    React appelle ensuite le même api.logAnnonceClick que AnnonceCard.jsx.
    """
    safe_type = html.escape(str(type_local))
    safe_prix = html.escape(str(prix))
    safe_quartier = html.escape(str(quartier))

    link_html = ""
    if listing_url:
        safe_link_url = html.escape(listing_url, quote=True)
        onclick_html = ""
        if annonce_id is not None:
            onclick_html = (
                " onclick=\"parent.postMessage({type: 'ANNONCE_CLICK', "
                f"id: {int(annonce_id)}}}, window.location.origin)\""
            )
        link_html = (
            f"<a href='{safe_link_url}' target='_blank' rel='noopener noreferrer'{onclick_html} "
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


def load_geojson_file(path):
    """Charge un fichier GeoJSON versionné dans le repo (ex: limites des
    arrondissements, ORA-104). Renvoie None si le fichier est absent ou
    invalide plutôt que de faire planter la génération de la carte."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("GeoJSON illisible (%s) : %s", path, e)
        return None


def load_layers_config(path=LAYERS_CONFIG_JSON):
    """Charge la liste des calques carte depuis le JSON partagé avec le
    frontend (ORA-130) : `[{key, name, label, group, defaultVisible, uiColor}, ...]`.

    `key` identifie le calque côté React (état `layers`, `LAYER_MAPPING`),
    `name` est le nom du calque tel que connu de Folium/`LayerControl` et du
    contrat `TOGGLE_LAYER` (MAP_CONTRACT.md), `defaultVisible` fixe l'état
    initial (`FeatureGroup(show=...)` ici, `layers` initial côté React).

    Contrairement à `load_geojson_file` (couche optionnelle, absence tolérée),
    ce fichier est requis pour générer une carte cohérente : une erreur ici
    (fichier manquant/JSON invalide) doit faire échouer la génération plutôt
    que de produire silencieusement une carte sans calques.
    """
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
        }} else if (e.data.type === 'FLY_TO_BOUNDS') {{
            {map_js_var_name}.flyToBounds(e.data.bounds);
        }}
    }});
    """


def main(ville='lyon'):
    paths = resolve_ville_paths(ville)

    # --- 3. CHARGEMENT DONNEES ---
    # A. Immo
    try:
        if os.path.exists(IMMO_CSV):
            df_immo = pd.read_csv(IMMO_CSV, sep=None, engine='python')
            df_immo.columns = df_immo.columns.str.strip().str.lower()
            for col in ['latitude', 'longitude']:
                if col in df_immo.columns: df_immo[col] = pd.to_numeric(df_immo[col], errors='coerce')
            df_immo = filter_by_ville(df_immo, ville)
        else: df_immo = pd.DataFrame()
    except: df_immo = pd.DataFrame()

    # B. Cavaliers
    df_poi = pd.DataFrame()
    try:
        if os.path.exists(paths['poi_csv']):
            # encoding='utf-8-sig' : certains cavaliers_*.csv (ex: cavaliers_lille.csv,
            # produit par api_overpass.py via to_csv(..., encoding='utf-8-sig'))
            # ont un BOM UTF-8 ; sans ce paramètre, le moteur 'python' laisse le
            # BOM collé au nom de la première colonne ("﻿categorie_cavalier"),
            # qui ne matche alors plus "categorie_cavalier" ci-dessous — tous les
            # POI de la ville concernée disparaissaient silencieusement de la carte
            # (constaté sur un run réel : 0/400 POI Lille affichés).
            df_poi = pd.read_csv(paths['poi_csv'], sep=None, engine='python', encoding='utf-8-sig')
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
    print(f"🛑 GENERATION CARTE {ville.upper()} (METRO LIGNES AUTO)...")
    m = folium.Map(location=paths['center'], zoom_start=13, tiles='CartoDB dark_matter', zoom_control=False)

    # Config partagée des calques (ORA-130) : nom Folium/TOGGLE_LAYER et
    # visibilité par défaut de chaque calque, aussi consommée par
    # MapComponent.jsx (LAYER_MAPPING + état initial `layers`).
    layers_config = load_layers_config()
    layer_by_key = {layer['key']: layer for layer in layers_config}

    # --- CREATION DES GROUPES ---
    fg_studio = folium.FeatureGroup(name=layer_by_key['Studio']['name'], show=layer_by_key['Studio']['defaultVisible'])
    fg_t2 = folium.FeatureGroup(name=layer_by_key['T2']['name'], show=layer_by_key['T2']['defaultVisible'])
    fg_t3 = folium.FeatureGroup(name=layer_by_key['T3']['name'], show=layer_by_key['T3']['defaultVisible'])
    fg_t4 = folium.FeatureGroup(name=layer_by_key['T4']['name'], show=layer_by_key['T4']['defaultVisible'])

    # Groupe Métro Unifié
    fg_metro = folium.FeatureGroup(name=layer_by_key['Metro']['name'], show=layer_by_key['Metro']['defaultVisible'])

    fg_vice = folium.FeatureGroup(name=layer_by_key['Vice']['name'], show=layer_by_key['Vice']['defaultVisible'])
    fg_gentri = folium.FeatureGroup(name=layer_by_key['Gentrification']['name'], show=layer_by_key['Gentrification']['defaultVisible'])
    fg_nuisance = folium.FeatureGroup(name=layer_by_key['Nuisance']['name'], show=layer_by_key['Nuisance']['defaultVisible'])
    fg_superstition = folium.FeatureGroup(name=layer_by_key['Superstition']['name'], show=layer_by_key['Superstition']['defaultVisible'])

    # --- 5. GENERATION POINTS IMMO ---
    for _, row in df_immo.iterrows():
        if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
            lat = row['latitude'] + random.uniform(-0.0001, 0.0001)
            lon = row['longitude'] + random.uniform(-0.0001, 0.0001)

            type_local = str(row.get('type_local', '')).strip()
            prix = str(row.get('prix', '?')).replace('.0', '')
            listing_url = sanitize_listing_url(row.get('url'))
            image_url = row.get('image')

            # ORA-107 : résout l'id SQLite (annonces.db) à partir de l'URL pour
            # que le clic sur le marker puisse être tracké (via ANNONCE_CLICK/
            # React), comme AnnonceCard.jsx. None si l'annonce n'y est pas
            # encore synchronisée (store pas encore peuplé pour ce run).
            annonce_id = None
            if listing_url:
                existing = annonces_store.get_annonce_by_url(listing_url, db_path=ANNONCES_DB_PATH)
                if existing:
                    annonce_id = existing['id']

            txt_tooltip = build_immo_tooltip_html(type_local, prix)
            txt_popup = build_immo_popup_html(
                type_local, prix, row.get('quartier', ville.capitalize()), listing_url, image_url, annonce_id,
            )

            target_group = None
            if type_local == 'Studio/T1': target_group = fg_studio
            elif type_local == 'T2': target_group = fg_t2
            elif type_local == 'T3': target_group = fg_t3
            elif type_local == 'Grand (T4+)': target_group = fg_t4

            if target_group:
                # Popup (pas Tooltip) : reste ouvert au clic au lieu de disparaître
                # dès que la souris quitte le marker, ce qui rendait le lien "Voir
                # l'annonce" à l'intérieur impossible à atteindre (ORA-134). Le
                # tooltip au survol reste utilisé en parallèle pour un aperçu
                # rapide sans lien (ORA-99, build_immo_tooltip_html).
                marker = folium.CircleMarker(
                    [lat, lon], radius=5, color=COLORS['Immo'], weight=1, fill=True, fill_color=COLORS['Immo'], fill_opacity=0.8,
                    tooltip=folium.Tooltip(txt_tooltip, class_name='oracle-popup'),
                    popup=folium.Popup(txt_popup, max_width=220, className='oracle-popup'),
                )
                marker.add_to(target_group)

    # --- 6. GESTION DU MÉTRO VIA JSON (LIGNES + STATIONS) ---
    if os.path.exists(paths['metro_json']):
        try:
            with open(paths['metro_json'], 'r', encoding='utf-8') as f:
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
            print(f"⚠️ Erreur lors du traitement de {paths['metro_json']} : {e}")

    # --- 6bis. LIMITES DES QUARTIERS (ARRONDISSEMENTS), ORA-104 ---
    quartiers_geojson = load_geojson_file(paths['quartiers_geojson'])
    if quartiers_geojson:
        folium.GeoJson(
            quartiers_geojson,
            name=layer_by_key['Quartiers']['name'],
            show=layer_by_key['Quartiers']['defaultVisible'],  # Off par défaut, cohérent avec Nuisance/Gentrification/Superstition
            style_function=lambda feature: {
                'fillColor': '#a78bfa',
                'color': '#a78bfa',
                'weight': 2,
                'fillOpacity': 0.06,
            },
            highlight_function=lambda feature: {'fillOpacity': 0.18, 'weight': 3},
            tooltip=folium.GeoJsonTooltip(fields=['nom'], aliases=['Quartier :']),
        ).add_to(m)
        print(f"🗺️ Quartiers chargés : {len(quartiers_geojson.get('features', []))} arrondissements tracés.")
    else:
        print(f"⚠️ GeoJSON des quartiers introuvable ou invalide ({paths['quartiers_geojson']}), couche ignorée.")

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

    with open(paths['output_html'], 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f"🎉 TERMINÉ : {paths['output_html']} (Métro : Lignes reliées automatiquement)")

    # --- 10. CONTRÔLE DE FRAÎCHEUR (ORA-54) ---
    # Écrit map_metadata_<ville>.json à côté de la carte, avec la date de
    # génération, pour détecter facilement une carte périmée si le pipeline
    # de données change.
    write_map_metadata(paths['metadata_json'], output_html=paths['output_html'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère la carte statique Folium pour une ville.")
    parser.add_argument('--ville', default='lyon', help="Slug de la ville (cf. VILLE_CONFIG), ex: lyon, lille.")
    args = parser.parse_args()
    main(args.ville)
