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

# CARTO exige désormais une clé API sur ses tuiles gratuites (basemaps.cartocdn.com,
# depuis fin août 2026) : sans elle, les tuiles s'affichent quand même (HTTP 200)
# mais avec un filigrane "API KEY REQUIRED" incrusté dans l'image. Clé gratuite
# (5M requêtes/mois) à obtenir sur https://carto.com/basemaps/apikey/.
CARTO_API_KEY = os.environ.get('CARTO_API_KEY', '')
CARTO_DARK_MATTER_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
if CARTO_API_KEY:
    CARTO_DARK_MATTER_URL += f"?key={CARTO_API_KEY}"
CARTO_ATTRIBUTION = (
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> '
    'contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
)

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
# Seuil ±5 % et couleurs des bandes de marché (ORA-165/168), partagés avec le
# panneau React (services/marketBand.js) : carte et panneau restent cohérents.
MARKET_BANDS_CONFIG_JSON = os.path.join(PROJECT_ROOT, 'frontend', 'src', 'config', 'marketBands.config.json')


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


# --- ORA-165/166 : pastilles prix, bandes de marché, regroupement, légende ---

# Couleur du texte de la pastille, lisible sur chaque fond de bande.
BAND_TEXT_COLORS = {'below': '#052e16', 'within': '#1c1400', 'above': '#ffffff'}
# En dessous de ce nombre d'annonces, la médiane d'un (quartier, type) est trop
# peu fiable : repli sur la médiane du type sur toute la ville.
MIN_LISTINGS_FOR_QUARTIER_MEDIAN = 3
# Quartiers de repli, sans nom de lieu réel : pas d'étiquette sur la carte.
UNLABELLED_QUARTIER_MARKERS = ('non localisé', 'secteur ', 'inconnu')


def load_market_bands(path=MARKET_BANDS_CONFIG_JSON):
    """`{thresholdPct, bands: {below|within|above: {label, color}}}` (config partagée)."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def market_band(ecart_pct, threshold_pct):
    """Bande de marché d'un écart en % (mêmes bornes que marketBand.js) :
    < -seuil = 'below', > +seuil = 'above', sinon 'within'."""
    if ecart_pct < -threshold_pct:
        return 'below'
    if ecart_pct > threshold_pct:
        return 'above'
    return 'within'


def ecart_vs_median(prix, median):
    """Écart en % (arrondi) d'un loyer à la médiane de référence, None si incalculable."""
    try:
        prix, median = float(prix), float(median)
    except (TypeError, ValueError):
        return None
    if median <= 0 or pd.isna(prix) or pd.isna(median):
        return None
    return round((prix - median) / median * 100)


def compute_reference_medians(df_immo):
    """Loyer médian de référence par annonce (Series alignée sur `df_immo`) :
    médiane de son (quartier, type_local) s'il compte assez d'annonces, sinon
    médiane de son type sur toute la ville."""
    if df_immo.empty or not {'prix', 'quartier', 'type_local'}.issubset(df_immo.columns):
        return pd.Series(index=df_immo.index, dtype=float)
    by_quartier = df_immo.groupby(['quartier', 'type_local'])['prix']
    quartier_median = by_quartier.transform('median')
    quartier_count = by_quartier.transform('count')
    type_median = df_immo.groupby('type_local')['prix'].transform('median')
    return quartier_median.where(quartier_count >= MIN_LISTINGS_FOR_QUARTIER_MEDIAN, type_median)


def build_price_pill_html(prix, band, bands_config, count=None):
    """Pastille prix d'un marqueur d'annonce, colorée selon la bande de marché.
    `count` (>=2) : marqueur groupé, badge du nombre d'annonces."""
    color = bands_config['bands'][band]['color']
    text_color = BAND_TEXT_COLORS[band]
    safe_prix = html.escape(str(prix))
    badge = (
        f"<span class='oracle-pill-count'>{int(count)}</span>" if count and count >= 2 else ""
    )
    return (
        f"<div class='oracle-pill' style='background:{color}; color:{text_color};'>"
        f"{safe_prix} €{badge}</div>"
    )


def group_by_exact_position(entries, precision=5):
    """Regroupe les annonces à coordonnées identiques (~1 m, `precision`
    décimales) : typiquement des annonces Vizzit géolocalisées sur la même
    rue. Renvoie une liste de groupes (listes d'entrées), ordre d'apparition
    conservé. Chaque entrée est un dict avec au moins `lat` et `lon`."""
    groups = {}
    for entry in entries:
        key = (round(entry['lat'], precision), round(entry['lon'], precision))
        groups.setdefault(key, []).append(entry)
    return list(groups.values())


def build_group_popup_html(group, bands_config):
    """Bulle d'un marqueur groupé (ORA-166) : « N annonces · même adresse »,
    une ligne surface / prix / écart % par annonce, et la mention de la source
    de géolocalisation quand toutes viennent de Vizzit (GPS réel)."""
    threshold = bands_config['thresholdPct']
    rows = []
    for entry in group:
        ecart = entry.get('ecart')
        ecart_html = ""
        if ecart is not None:
            band = market_band(ecart, threshold)
            color = bands_config['bands'][band]['color']
            sign = '+' if ecart > 0 else ''
            ecart_html = f"<b style='color:{color};'>{sign}{int(ecart)} %</b>"
        surface = entry.get('surface')
        surface_txt = f"{int(surface)} m²" if surface is not None and pd.notna(surface) else "— m²"
        link_html = ""
        if entry.get('url'):
            safe_url = html.escape(entry['url'], quote=True)
            onclick = ""
            if entry.get('annonce_id') is not None:
                onclick = (
                    " onclick=\"parent.postMessage({type: 'ANNONCE_CLICK', "
                    f"id: {int(entry['annonce_id'])}}}, window.location.origin)\""
                )
            link_html = (
                f" <a href='{safe_url}' target='_blank' rel='noopener noreferrer'{onclick} "
                "style='color:#22c55e;' aria-label='Voir l&#39;annonce'>&#8599;</a>"
            )
        rows.append(
            "<li style='display:flex; justify-content:space-between; gap:10px; padding:2px 0;'>"
            f"<span>{html.escape(str(entry.get('type_local', '')))} · {surface_txt}</span>"
            f"<span><b>{html.escape(str(entry['prix']))} €</b> {ecart_html}{link_html}</span></li>"
        )
    sources = {str(e.get('site', '')).strip().lower() for e in group}
    note = (
        "Géolocalisées sur la même rue (Vizzit)"
        if sources == {'vizzit'}
        else "Coordonnées identiques"
    )
    return (
        "<div style='font-family:sans-serif; min-width:200px; font-size:12px;'>"
        f"<div style='font-size:14px; font-weight:bold; margin-bottom:4px;'>{len(group)} annonces · même adresse</div>"
        f"<ul style='list-style:none; margin:0; padding:0;'>{''.join(rows)}</ul>"
        f"<div style='color:#94a3b8; font-size:11px; margin-top:6px;'>{note}</div>"
        "</div>"
    )


def compute_quartier_labels(df_immo, min_listings=3):
    """`[(NOM EN CAPITALES, lat, lon)]` : centre de chaque quartier réel
    (moyenne des annonces localisées). Les quartiers de repli (« Non
    localisé », « Secteur … ») n'ont pas de position significative : ignorés."""
    if df_immo.empty or not {'quartier', 'latitude', 'longitude'}.issubset(df_immo.columns):
        return []
    located = df_immo.dropna(subset=['quartier', 'latitude', 'longitude'])
    labels = []
    for nom, group in located.groupby('quartier'):
        if len(group) < min_listings or any(m in str(nom).lower() for m in UNLABELLED_QUARTIER_MARKERS):
            continue
        labels.append((str(nom).upper(), float(group['latitude'].mean()), float(group['longitude'].mean())))
    return labels


def build_legend_html(layers_config, bands_config):
    """Légende en coin de carte (ORA-166) : groupes Annonces / Métro /
    Cavaliers / Quartiers issus de la config partagée des calques, plus
    l'échelle « Écart au loyer médian du quartier ». Chaque ligne porte
    `data-layer` (nom Folium du calque) : un script grise la ligne quand le
    calque est masqué depuis le panneau de contrôle."""
    threshold = bands_config['thresholdPct']
    band_rows = ''.join(
        f"<li><span class='oracle-legend-swatch' style='background:{cfg['color']};'></span>"
        f"{html.escape(cfg['label'])} <span class='oracle-legend-muted'>{rule}</span></li>"
        for cfg, rule in (
            (bands_config['bands']['below'], f"&lt; −{threshold} %"),
            (bands_config['bands']['within'], f"± {threshold} %"),
            (bands_config['bands']['above'], f"&gt; +{threshold} %"),
        )
    )
    groups = [
        ('immobilier', 'Annonces'), ('transports', 'Métro'), ('contexte', 'Cavaliers & quartiers'),
    ]
    sections = []
    for group_key, title in groups:
        rows = ''.join(
            f"<li data-layer='{html.escape(layer['name'], quote=True)}'>"
            f"<span class='oracle-legend-swatch' style='background:{layer['uiColor']};'></span>"
            f"{html.escape(layer['label'])}</li>"
            for layer in layers_config if layer['group'] == group_key
        )
        sections.append(f"<div class='oracle-legend-title'>{title}</div><ul>{rows}</ul>")
    return (
        "<div class='oracle-legend' role='region' aria-label='Légende de la carte'>"
        f"{''.join(sections)}"
        "<div class='oracle-legend-title'>Écart au loyer médian du quartier</div>"
        f"<ul>{band_rows}</ul></div>"
    )


def build_legend_and_scale_script(map_var, legend_html):
    """Injecte la légende, l'échelle métrique et les classes de zoom
    (`oracle-z13`/`oracle-z14`, qui révèlent labels de quartiers et noms de
    stations) ; grise les lignes de légende des calques masqués."""
    legend_js = json.dumps(legend_html)
    # `load` : Folium rend le script d'init de la carte APRÈS </body> ; à
    # l'exécution de ce bloc, `{map_var}` n'est donc pas encore défini.
    return f"""
    window.addEventListener('load', function() {{
        var map = {map_var};
        var container = document.createElement('div');
        container.innerHTML = {legend_js};
        document.body.appendChild(container.firstChild);
        L.control.scale({{imperial: false, position: 'bottomleft'}}).addTo(map);
        function setLegend(name, on) {{
            document.querySelectorAll('.oracle-legend [data-layer]').forEach(function(li) {{
                if (li.getAttribute('data-layer') === name) li.classList.toggle('oracle-legend-off', !on);
            }});
        }}
        map.on('overlayadd', function(e) {{ setLegend(e.name, true); }});
        map.on('overlayremove', function(e) {{ setLegend(e.name, false); }});
        function updateZoomClasses() {{
            document.body.classList.toggle('oracle-z13', map.getZoom() >= 13);
            document.body.classList.toggle('oracle-z14', map.getZoom() >= 14);
        }}
        map.on('zoomend', updateZoomClasses);
        updateZoomClasses();
    }});
    """


def compute_layer_counts(df_poi, df_immo):
    """ORA-172 : compteurs du panneau "Contrôle des calques" (maquette 04,
    ex. "Vice 526", "T2 300") — calculés depuis les données à chaque
    génération de carte, jamais codés en dur côté React.

    `df_poi` : POI cavaliers (colonne `type`, ex. "Vice - Bar" — un POI
    compte pour sa catégorie dès que le nom de la catégorie apparaît dans le
    type, insensible à la casse, même logique que le rendu des marqueurs
    ci-dessus). `df_immo` : annonces (colonne `type_local`, valeurs exactes
    "Studio/T1"/"T2"/"T3"/"Grand (T4+)").
    """
    counts = {}
    if 'type' in df_poi.columns:
        raw_types = df_poi['type'].astype(str).str.lower()
        for key in ('vice', 'gentrification', 'nuisance', 'superstition'):
            counts[key.capitalize()] = int(raw_types.str.contains(key, na=False).sum())
    if 'type_local' in df_immo.columns:
        counts_by_type = df_immo['type_local'].value_counts()
        counts['Studio'] = int(counts_by_type.get('Studio/T1', 0))
        counts['T2'] = int(counts_by_type.get('T2', 0))
        counts['T3'] = int(counts_by_type.get('T3', 0))
        counts['T4'] = int(counts_by_type.get('Grand (T4+)', 0))
    return counts


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
            if 'statut' in df_immo.columns:
                avant = len(df_immo)
                df_immo = df_immo[df_immo['statut'] != 'inactive']
                print(f"   🧹 {avant - len(df_immo)} annonce(s) inactive(s) exclue(s) de la carte statique.")
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
    m = folium.Map(location=paths['center'], zoom_start=13, tiles=None, zoom_control=False)
    folium.TileLayer(
        tiles=CARTO_DARK_MATTER_URL,
        attr=CARTO_ATTRIBUTION,
        name='CartoDB dark_matter',
    ).add_to(m)

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
    # ORA-172 : funiculaires (lignes F1/F2, Lyon) séparés du métro dans le
    # panneau de calques (maquette 04, groupe "Transports") — même source
    # GeoJSON, juste un FeatureGroup distinct selon le préfixe de ligne.
    fg_funicular = folium.FeatureGroup(name=layer_by_key['Funicular']['name'], show=layer_by_key['Funicular']['defaultVisible']) if 'Funicular' in layer_by_key else None

    fg_vice = folium.FeatureGroup(name=layer_by_key['Vice']['name'], show=layer_by_key['Vice']['defaultVisible'])
    fg_gentri = folium.FeatureGroup(name=layer_by_key['Gentrification']['name'], show=layer_by_key['Gentrification']['defaultVisible'])
    fg_nuisance = folium.FeatureGroup(name=layer_by_key['Nuisance']['name'], show=layer_by_key['Nuisance']['defaultVisible'])
    fg_superstition = folium.FeatureGroup(name=layer_by_key['Superstition']['name'], show=layer_by_key['Superstition']['defaultVisible'])

    # --- 5. GENERATION POINTS IMMO ---
    # ORA-165/166 : pastille prix colorée selon l'écart au loyer médian du
    # quartier (bandes ±5 %, config partagée avec le panneau React) ; les
    # annonces à coordonnées identiques (typiquement Vizzit, même rue) sont
    # regroupées en un marqueur unique avec bulle « N annonces · même adresse ».
    bands_config = load_market_bands()
    band_threshold = bands_config['thresholdPct']
    reference_medians = compute_reference_medians(df_immo) if not df_immo.empty else pd.Series(dtype=float)

    entries = []
    for idx, row in df_immo.iterrows():
        if pd.notnull(row.get('latitude')) and pd.notnull(row.get('longitude')):
            type_local = str(row.get('type_local', '')).strip()
            prix = str(row.get('prix', '?')).replace('.0', '')
            listing_url = sanitize_listing_url(row.get('url'))

            # ORA-107 : résout l'id SQLite (annonces.db) à partir de l'URL pour
            # que le clic sur le marker puisse être tracké (via ANNONCE_CLICK/
            # React), comme AnnonceCard.jsx. None si l'annonce n'y est pas
            # encore synchronisée (store pas encore peuplé pour ce run).
            annonce_id = None
            if listing_url:
                existing = annonces_store.get_annonce_by_url(listing_url, db_path=ANNONCES_DB_PATH)
                if existing:
                    annonce_id = existing['id']

            ecart = ecart_vs_median(row.get('prix'), reference_medians.get(idx))
            entries.append({
                'lat': float(row['latitude']), 'lon': float(row['longitude']),
                'type_local': type_local, 'prix': prix, 'surface': row.get('surface'),
                'quartier': row.get('quartier', ville.capitalize()), 'url': listing_url,
                'image': row.get('image'), 'annonce_id': annonce_id,
                'site': row.get('site'), 'ecart': ecart,
            })

    def target_group_for(type_local):
        if type_local == 'Studio/T1': return fg_studio
        if type_local == 'T2': return fg_t2
        if type_local == 'T3': return fg_t3
        if type_local == 'Grand (T4+)': return fg_t4
        return None

    for group in group_by_exact_position(entries):
        first = group[0]
        target_group = target_group_for(first['type_local'])
        if target_group is None:
            continue
        band = market_band(first['ecart'], band_threshold) if first['ecart'] is not None else 'within'

        if len(group) >= 2:
            # Marqueur groupé : position exacte (pas de jitter), bulle dédiée.
            lat, lon = first['lat'], first['lon']
            txt_popup = build_group_popup_html(group, bands_config)
            txt_tooltip = f"{len(group)} annonces · même adresse"
            pill = build_price_pill_html(first['prix'], band, bands_config, count=len(group))
        else:
            lat = first['lat'] + random.uniform(-0.0001, 0.0001)
            lon = first['lon'] + random.uniform(-0.0001, 0.0001)
            txt_tooltip = build_immo_tooltip_html(first['type_local'], first['prix'])
            txt_popup = build_immo_popup_html(
                first['type_local'], first['prix'], first['quartier'], first['url'], first['image'], first['annonce_id'],
            )
            pill = build_price_pill_html(first['prix'], band, bands_config)

        # Popup (pas Tooltip) : reste ouvert au clic au lieu de disparaître
        # dès que la souris quitte le marker, ce qui rendait le lien "Voir
        # l'annonce" à l'intérieur impossible à atteindre (ORA-134). Le
        # tooltip au survol reste utilisé en parallèle pour un aperçu
        # rapide sans lien (ORA-99, build_immo_tooltip_html).
        folium.Marker(
            [lat, lon],
            icon=folium.DivIcon(html=pill, icon_size=(54, 20), icon_anchor=(27, 10), class_name='oracle-pill-icon'),
            tooltip=folium.Tooltip(txt_tooltip, class_name='oracle-popup'),
            popup=folium.Popup(txt_popup, max_width=260, className='oracle-popup'),
        ).add_to(target_group)

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

                    # ORA-172 : une ligne "F..." (F1/F2) est un funiculaire, pas
                    # le métro — groupe distinct si le calque existe (sinon repli
                    # sur fg_metro, ex. config plus ancienne sans "Funicular").
                    target_group = fg_funicular if ligne.startswith('F') and fg_funicular is not None else fg_metro

                    folium.Marker(
                        [lat, lon],
                        icon=folium.DivIcon(html=icon_html, icon_size=(24, 24), icon_anchor=(12, 12)),
                        popup=folium.Popup(popup_txt, max_width=200, className='oracle-popup'),
                        # ORA-165 : nom de la station, affiché à partir du zoom 14 (CSS)
                        tooltip=folium.Tooltip(html.escape(str(nom_station)), permanent=True, direction='right', offset=(12, 0), class_name='oracle-metro-label'),
                    ).add_to(target_group)
                    count_stations += 1

            # 2. DESSINER LES LIGNES EN RELIANT LES POINTS
            # Si le fichier JSON est bien ordonné, cela reliera les stations dans l'ordre
            for ligne, coords in stations_by_line.items():
                if len(coords) > 1:
                    target_group = fg_funicular if ligne.startswith('F') and fg_funicular is not None else fg_metro
                    folium.PolyLine(
                        locations=coords,
                        color=METRO_COLORS.get(ligne, '#888888'),
                        weight=4,
                        opacity=0.6,
                        smooth_factor=1.5 # Adoucit un peu les angles
                    ).add_to(target_group)

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

    # --- 6ter. LABELS DE QUARTIERS EN CAPITALES (ORA-165) ---
    # Hors LayerControl (control=False) : toujours présents, révélés par CSS à
    # partir du zoom 13 ; non interactifs pour ne pas gêner les clics marqueurs.
    fg_quartier_labels = folium.FeatureGroup(name='Noms de quartiers', control=False)
    for nom, lat, lon in compute_quartier_labels(df_immo):
        folium.Marker(
            [lat, lon],
            icon=folium.DivIcon(html=f"<div class='oracle-quartier-label'>{html.escape(nom)}</div>", icon_size=(160, 16), icon_anchor=(80, 8), class_name='oracle-quartier-icon'),
            interactive=False, keyboard=False,
        ).add_to(fg_quartier_labels)
    fg_quartier_labels.add_to(m)

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
    if fg_funicular is not None:
        fg_funicular.add_to(m)
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

        /* ORA-165 : pastille prix (bande de marché) */
        .oracle-pill-icon {{ background: transparent !important; border: none !important; }}
        .oracle-pill {{
            width: 54px; height: 20px; border-radius: 10px; box-sizing: border-box;
            display: flex; align-items: center; justify-content: center; position: relative;
            font: 700 10px/1 sans-serif; border: 1px solid rgba(7,10,18,0.55);
            box-shadow: 0 1px 4px rgba(0,0,0,0.6); white-space: nowrap;
        }}
        .oracle-pill-count {{
            position: absolute; top: -7px; right: -7px; min-width: 15px; height: 15px; padding: 0 3px;
            border-radius: 8px; background: #0f172a; color: #f8fafc; border: 1px solid #f8fafc;
            font: 700 9px/13px sans-serif; text-align: center; box-sizing: border-box;
        }}
        .leaflet-marker-icon:focus-visible .oracle-pill {{ outline: 2px solid #a78bfa; outline-offset: 2px; }}

        /* Noms de stations (zoom >= 14) et labels de quartiers (zoom >= 13) */
        .leaflet-tooltip.oracle-metro-label {{
            display: none; background: transparent; border: none; box-shadow: none;
            color: #e2e8f0; font: 600 10px sans-serif; text-shadow: 0 0 3px #070a12, 0 0 3px #070a12;
        }}
        .leaflet-tooltip.oracle-metro-label::before {{ display: none; }}
        body.oracle-z14 .leaflet-tooltip.oracle-metro-label {{ display: block; }}
        .oracle-quartier-icon {{ background: transparent !important; border: none !important; display: none; }}
        body.oracle-z13 .oracle-quartier-icon {{ display: block; }}
        .oracle-quartier-label {{
            width: 160px; text-align: center; color: #cbd5e1; font: 700 10px sans-serif;
            letter-spacing: 0.12em; text-shadow: 0 0 4px #070a12, 0 0 4px #070a12; pointer-events: none;
        }}

        /* Légende (ORA-166) */
        .oracle-legend {{
            position: absolute; left: 12px; bottom: 34px; z-index: 1000; max-width: 210px;
            background: rgba(15,23,42,0.92); color: #e2e8f0; border: 1px solid #334155;
            border-radius: 10px; padding: 8px 10px; font: 11px/1.5 sans-serif;
        }}
        .oracle-legend ul {{ list-style: none; margin: 0 0 4px; padding: 0; }}
        .oracle-legend-title {{ font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; font-weight: 700; margin-top: 4px; }}
        .oracle-legend-swatch {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; }}
        .oracle-legend-muted {{ color: #94a3b8; }}
        .oracle-legend-off {{ opacity: 0.35; text-decoration: line-through; }}
    </style>

    <script>
    {build_bridge_message_script(m.get_name())}
    {build_legend_and_scale_script(m.get_name(), build_legend_html(layers_config, bands_config))}
    </script>
    </body>
    """

    html_out = html_out.replace('</body>', hack)

    if not os.path.exists(FRONTEND_DATA_DIR):
        os.makedirs(FRONTEND_DATA_DIR)

    with open(paths['output_html'], 'w', encoding='utf-8') as f:
        f.write(html_out)

    print(f"🎉 TERMINÉ : {paths['output_html']} (Métro : Lignes reliées automatiquement)")

    # --- 10. CONTRÔLE DE FRAÎCHEUR (ORA-54) + COMPTEURS DE CALQUES (ORA-172) ---
    # Écrit map_metadata_<ville>.json à côté de la carte, avec la date de
    # génération, pour détecter facilement une carte périmée si le pipeline
    # de données change. `layer_counts` (ORA-172) alimente les compteurs du
    # panneau "Contrôle des calques" (MapComponent.jsx) — calculés depuis les
    # données à chaque génération plutôt que codés en dur côté React.
    layer_counts = compute_layer_counts(df_poi, df_immo)

    write_map_metadata(paths['metadata_json'], output_html=paths['output_html'], extra={'layer_counts': layer_counts})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère la carte statique Folium pour une ville.")
    parser.add_argument('--ville', default='lyon', help="Slug de la ville (cf. VILLE_CONFIG), ex: lyon, lille.")
    args = parser.parse_args()
    main(args.ville)
