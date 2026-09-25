import pandas as pd
import numpy as np
import json
import os
import random
import sys
import warnings
import re
from shapely.geometry import MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from sklearn.neighbors import BallTree

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION ET CHEMINS
# =============================================================================
print("⚙️  Configuration du pipeline...")
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, '..', 'data')
backend_dir = os.path.dirname(script_dir)

# backend/services (annonces_store) n'est pas sur sys.path par défaut quand ce
# script est lancé depuis backend/scripts/ (ex: `python clean_immo.py`, ou
# l'étape DAG Airflow `clean_immo`) plutôt que depuis backend/ (comme app.py).
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from services import annonces_store  # noqa: E402 (après le sys.path.insert nécessaire)
from services.adresse_texte import localiser_adresse  # noqa: E402
from services.geocodage import geocoder  # noqa: E402
from services.localisation_texte import localiser_par_texte  # noqa: E402

# Fichiers d'entrée/sortie
INPUT_RAW_CSV = os.path.join(data_dir, "base_de_donnees_immo_complet.csv")
CAVALIERS_CSV = os.path.join(data_dir, "cavaliers_all.csv")
OUTPUT_FINAL_CSV = os.path.join(data_dir, "master_immo_final.csv")
ANNONCES_DB_PATH = os.path.join(data_dir, "annonces.db")
# Historique cumulatif des annonces sorties du master (cf. step_archive_hors_master).
ARCHIVE_CSV = os.path.join(data_dir, "master_archive.csv")
SCRAPING_CONFIG_PATH = os.path.join(script_dir, '..', '..', 'scripts', 'scraping_config.json')

# Paramètres globaux
RADIUS_METERS = 500
# Seed fixe du jitter géographique : garantit qu'à données brutes égales,
# deux exécutions du pipeline produisent des coordonnées identiques (donc
# des features de distance et un modèle identiques). Ne pas changer sans
# ré-entraîner et recommitter price_predictor.pkl.
GEOCODING_JITTER_SEED = 42
# Nombre de jours au-delà duquel une annonce non re-confirmée par le scraping
# est considérée expirée et exclue du pipeline (ORA-134 : le pipeline n'avait
# auparavant aucun mécanisme de suppression, les annonces retirées/louées sur
# le site source restaient indéfiniment). ~2 runs hebdomadaires de marge pour
# absorber un run manqué/en échec sans purger à tort une annonce encore active.
TTL_JOURS_DERNIER_SCAN = 14
FALLBACK_ZONES = {
    "69001": {"lat": 45.7705, "lon": 4.8306, "radius": 0.005},
    "69002": {"lat": 45.7533, "lon": 4.8327, "radius": 0.008},
    "69003": {"lat": 45.7562, "lon": 4.8655, "radius": 0.015},
    "69004": {"lat": 45.7770, "lon": 4.8270, "radius": 0.007},
    "69005": {"lat": 45.7580, "lon": 4.8050, "radius": 0.008},
    "69006": {"lat": 45.7690, "lon": 4.8550, "radius": 0.007},
    "69007": {"lat": 45.7350, "lon": 4.8380, "radius": 0.015},
    "69008": {"lat": 45.7380, "lon": 4.8700, "radius": 0.010},
    "69009": {"lat": 45.7780, "lon": 4.8030, "radius": 0.012},
    "69100": {"lat": 45.7720, "lon": 4.8850, "radius": 0.020},
}

# Les 10 quartiers officiels de Lille (ORA-71 POC) : boîte englobante
# (lat/lon min/max) et centroïde calculés à partir des limites
# administratives réelles (Overpass, `boundary=administrative` +
# `admin_level=10` dans Lille — même mécanisme que api_overpass.py pour les
# cavaliers). Pas d'estimation à la main comme les FALLBACK_ZONES Lyon.
QUARTIERS_LILLE = {
    "Lille-Centre": {"lat_min": 50.6221, "lat_max": 50.6433, "lon_min": 3.0487, "lon_max": 3.0835, "centroid_lat": 50.6315, "centroid_lon": 3.0700},
    "Vieux-Lille": {"lat_min": 50.6361, "lat_max": 50.6510, "lon_min": 3.0484, "lon_max": 3.0725, "centroid_lat": 50.6455, "centroid_lon": 3.0622},
    "Wazemmes": {"lat_min": 50.6184, "lat_max": 50.6326, "lon_min": 3.0350, "lon_max": 3.0613, "centroid_lat": 50.6243, "centroid_lon": 3.0466},
    "Lille-Moulins": {"lat_min": 50.6117, "lat_max": 50.6270, "lon_min": 3.0483, "lon_max": 3.0847, "centroid_lat": 50.6193, "centroid_lon": 3.0718},
    "Vauban-Esquermes": {"lat_min": 50.6206, "lat_max": 50.6481, "lon_min": 3.0288, "lon_max": 3.0536, "centroid_lat": 50.6302, "centroid_lon": 3.0402},
    "Lille-Sud": {"lat_min": 50.6008, "lat_max": 50.6167, "lon_min": 3.0236, "lon_max": 3.0768, "centroid_lat": 50.6097, "centroid_lon": 3.0537},
    "Faubourg de Béthune": {"lat_min": 50.6139, "lat_max": 50.6226, "lon_min": 3.0212, "lon_max": 3.0500, "centroid_lat": 50.6191, "centroid_lon": 3.0355},
    "Bois Blancs": {"lat_min": 50.6218, "lat_max": 50.6389, "lon_min": 3.0168, "lon_max": 3.0401, "centroid_lat": 50.6318, "centroid_lon": 3.0281},
    "Fives": {"lat_min": 50.6153, "lat_max": 50.6422, "lon_min": 3.0785, "lon_max": 3.1039, "centroid_lat": 50.6280, "centroid_lon": 3.0914},
    "Saint-Maurice Pellevoisin": {"lat_min": 50.6372, "lat_max": 50.6572, "lon_min": 3.0747, "lon_max": 3.1040, "centroid_lat": 50.6470, "centroid_lon": 3.0849},
}

# Zones de repli pour le jitter (annonces sans coordonnées réelles) : CP
# fiables Lomme/Hellemmes/Euralille.
FALLBACK_ZONE_LOMME = {"lat": 50.6457, "lon": 2.9871, "radius": 0.018}
FALLBACK_ZONE_HELLEMMES = {"lat": 50.6275, "lon": 3.1092, "radius": 0.013}
FALLBACK_ZONE_EURALILLE = {"lat": 50.6392, "lon": 3.0738, "radius": 0.006}

# Vraies communes limitrophes de Lille (pas des communes associées comme
# Lomme/Hellemmes : des communes indépendantes, avec leur propre mairie et
# CP) dont des annonces remontent parfois dans une recherche SeLoger centrée
# sur Lille (rayon de recherche du site) — constaté en conditions réelles
# sur le champ `Lieu` (ORA-71 POC follow-up : Lambersart, La Madeleine,
# Faches-Thumesnil, Villeneuve-d'Ascq). Centre + rayon (max(largeur,
# hauteur)/2 de la bounding box, même formule que _lille_zone_center_and_radius)
# depuis les limites administratives réelles (Nominatim, boundary=administrative).
# Jamais clippées à LILLE_COMMUNE_POLYGON — ce ne sont pas des annonces
# Lille, et Lambersart/La Madeleine bordent directement Lille : un clip à la
# frontière de Lille placerait leurs annonces du mauvais côté de la limite.
ZONES_LIMITROPHES_LILLE = {
    "Lambersart": {"lat": 50.6477924, "lon": 3.0223644, "radius": 0.0224, "cp": "59130"},
    "La Madeleine": {"lat": 50.6544010, "lon": 3.0733338, "radius": 0.0137, "cp": "59110"},
    "Faches-Thumesnil": {"lat": 50.6026031, "lon": 3.0697877, "radius": 0.0181, "cp": "59155"},
    "Villeneuve-d'Ascq": {"lat": 50.6193174, "lon": 3.1314002, "radius": 0.0460, "cp": "59650"},
}
CP_A_ZONE_LIMITROPHE = {z["cp"]: nom for nom, z in ZONES_LIMITROPHES_LILLE.items()}

# Contour réel de la commune de Lille (Lille + Lomme + Hellemmes, communes
# associées incluses dans le même périmètre administratif), (lat, lon),
# simplifié (tolérance 0.001°) depuis la géométrie officielle Overpass
# (relation OSM 58404, boundary=administrative, admin_level=8). Utilisé
# pour le repli générique "Lille" (annonce sans quartier ni
# GPS identifiable) : un simple cercle centré sur Lille débordait sur les
# communes voisines (constaté : des points retombaient à Lambersart,
# CP 59130, qui n'est pas Lille) — le tirage au sort se fait maintenant
# dans ce polygone réel, jamais hors de la commune.
LILLE_COMMUNE_BOUNDARY = [
    (50.63425, 3.102922), (50.636352, 3.116447), (50.635104, 3.121575), (50.63071, 3.120809),
    (50.626357, 3.123631), (50.623247, 3.121491), (50.621158, 3.125725), (50.618866, 3.124655),
    (50.619919, 3.122659), (50.617762, 3.11862), (50.620659, 3.114763), (50.616899, 3.106474),
    (50.615356, 3.105996), (50.618598, 3.100104), (50.615315, 3.089101), (50.617918, 3.086251),
    (50.614276, 3.079495), (50.606825, 3.071274), (50.612587, 3.061975), (50.601047, 3.054422),
    (50.600836, 3.049154), (50.606886, 3.043057), (50.604567, 3.041546), (50.604832, 3.036781),
    (50.611518, 3.023805), (50.61338, 3.024486), (50.613821, 3.028045), (50.61696, 3.024005),
    (50.625416, 3.018609), (50.624765, 3.004541), (50.62649, 3.013979), (50.625929, 3.000785),
    (50.627261, 3.000946), (50.629155, 2.997657), (50.62748, 2.993557), (50.633299, 2.986269),
    (50.63507, 2.979557), (50.633589, 2.969605), (50.635091, 2.967968), (50.636319, 2.970486),
    (50.638361, 2.968752), (50.641787, 2.972724), (50.643808, 2.972231), (50.645929, 2.974569),
    (50.657337, 2.968853), (50.66126, 2.983942), (50.65532, 2.999231), (50.649313, 3.006613),
    (50.648573, 3.010639), (50.639723, 3.019517), (50.635438, 3.028825), (50.638902, 3.036931),
    (50.64201, 3.036872), (50.644663, 3.039081), (50.648076, 3.04577), (50.648645, 3.051345),
    (50.649498, 3.05052), (50.650532, 3.052421), (50.649251, 3.057827), (50.651045, 3.05959),
    (50.649829, 3.06607), (50.641814, 3.075194), (50.644523, 3.075811), (50.64381, 3.077523),
    (50.647248, 3.082992), (50.649095, 3.080395), (50.650819, 3.083484), (50.657156, 3.085078),
    (50.656857, 3.08761), (50.656147, 3.090034), (50.651434, 3.089657), (50.650979, 3.091089),
    (50.650162, 3.094658), (50.652284, 3.104027), (50.643558, 3.093867), (50.640943, 3.093566),
    (50.640181, 3.096752), (50.638901, 3.094515), (50.636936, 3.096269), (50.638376, 3.098526),
    (50.635762, 3.0992), (50.63425, 3.102922),
]
LILLE_COMMUNE_POLYGON = Polygon([(lon, lat) for lat, lon in LILLE_COMMUNE_BOUNDARY])

# "Lille propre" (ORA-71 POC) : zone couverte par les 10 quartiers centraux
# réels de QUARTIERS_LILLE, à l'exclusion de Lomme, Hellemmes et Euralille.
# Les 10 quartiers viennent d'une requête Overpass distincte de celle de
# Lomme/Hellemmes (admin_level=10 "quartier" à l'intérieur de Lille, alors
# que Lomme/Hellemmes sont des communes associées à part) et ne les
# recouvrent pas en leur centre — mais la boîte englobante de Fives, un
# quartier réel voisin, chevauche légèrement la zone de repli à main levée
# d'Hellemmes (FALLBACK_ZONE_HELLEMMES, estimée comme les FALLBACK_ZONES
# Lyon, pas un vrai contour) : les zones de Lomme/Hellemmes/Euralille sont
# donc explicitement retirées de l'union, pas seulement supposées disjointes.
# Euralille (quartier d'affaires, pas une commune) n'a par ailleurs pas de
# vrai contour cartographié dans OSM (juste un point labellisé, vérifié via
# Nominatim) : sa zone de repli à main levée est retirée pour la même
# raison.
# Sert de repli générique pour "Lille" (annonce Lille sans
# quartier identifié) : le CP par défaut (59000) veut dire "quelque part
# dans la commune de Lille", jamais "à Lomme", "à Hellemmes" ou "à
# Euralille" — ces trois-là ont leur propre CP distinctif (59160/59260/
# 59777) et, s'il avait été détecté, l'annonce serait déjà résolue vers
# leur nom avant d'atteindre ce repli (cf. get_point_for_zipcode). Les
# utiliser comme zone de secours pour une annonce dont on ignore juste la
# position aurait mélangé leurs vraies annonces avec des annonces
# génériques placées là par hasard.
LILLE_PROPRE_POLYGON = unary_union([
    box(z["lon_min"], z["lat_min"], z["lon_max"], z["lat_max"]) for z in QUARTIERS_LILLE.values()
]).intersection(LILLE_COMMUNE_POLYGON).difference(unary_union([
    Point(z["lon"], z["lat"]).buffer(z["radius"])
    for z in (FALLBACK_ZONE_LOMME, FALLBACK_ZONE_HELLEMMES, FALLBACK_ZONE_EURALILLE)
]))

# SeLoger encode parfois un slug de quartier réel dans l'URL de l'annonce
# (ex: seloger.com/.../lille-59/moulins/12345.htm) — signal structuré fourni
# par le site lui-même, pas une détection par mot-clé dans le texte libre de
# la description (écartée en conception : "proche de Wazemmes" ne veut pas
# dire "à Wazemmes"). Century21/Orpi/PAP n'exposent pas ce niveau de détail
# dans leurs URLs Lille. Slugs relevés sur les annonces SeLoger Lille
# réellement scrapées (Task 8) ; les sous-secteurs de Lomme/Hellemmes sont
# regroupés sous leur commune, les micro-quartiers sans équivalent dans
# QUARTIERS_LILLE (Caulier, Mont-à-Camp) sous le quartier officiel le plus
# proche.
SELOGER_SLUG_TO_QUARTIER_LILLE = {
    "centre": "Lille-Centre",
    "vieux-lille": "Vieux-Lille",
    "wazemmes": "Wazemmes",
    "moulins": "Lille-Moulins",
    "vauban-esquermes": "Vauban-Esquermes",
    "lille-sud": "Lille-Sud",
    "faubourg-de-bethune-concorde": "Faubourg de Béthune",
    "bois-blanc": "Bois Blancs",
    "fives": "Fives",
    "caulier": "Fives",
    "saint-maurice-pellevoisin": "Saint-Maurice Pellevoisin",
    "hellemmes-centre": "Hellemmes",
    "hellemmes-epine-mont-de-terre": "Hellemmes",
    "hellemmes-les-sarts": "Hellemmes",
    "lomme-le-marais": "Lomme",
    "mitterie": "Lomme",
    "bourg-delivrance": "Lomme",
    "mont-a-camp-marais": "Lomme",
}

# Segment de quartier optionnel dans une URL SeLoger : .../locations/<type>/
# <commune-slug>[-<arrondissement>eme]-<dept>/<quartier-slug>/<id>.htm —
# n'existe que lorsque SeLoger connaît un quartier précis pour cette
# annonce. Lille n'a pas d'arrondissement (ex: "lille-59/moulins/...") ；
# Lyon en a (ex: "lyon-8eme-69/monplaisir-le-bachut/...", jamais consommé
# pour Lyon ici — cf. resolve_lille_quartier_hint — mais le motif doit
# quand même le reconnaître sans planter dessus).
SELOGER_URL_QUARTIER_RE = re.compile(
    r'/[a-z][a-z\-]*-(?:\d{1,2}eme-)?\d{2}/([a-z][a-z0-9\-]+)/\d+\.htm', re.IGNORECASE
)


def extract_seloger_quartier_slug(url):
    """Slug de quartier brut dans une URL SeLoger, ou None si absent (URL
    SeLoger sans détail de quartier, ou URL d'un autre site)."""
    if pd.isna(url): return None
    match = SELOGER_URL_QUARTIER_RE.search(str(url))
    return match.group(1).lower() if match else None


def resolve_lille_quartier_hint(url):
    """Quartier réel Lille déduit du slug d'URL SeLoger, ou None si aucun
    slug connu (URL absente, site sans slug, ou slug non répertorié dans
    SELOGER_SLUG_TO_QUARTIER_LILLE)."""
    slug = extract_seloger_quartier_slug(url)
    if slug is None: return None
    return SELOGER_SLUG_TO_QUARTIER_LILLE.get(slug)


def _lille_zone_center_and_radius(quartier_nom):
    """Centre + rayon de jitter pour un quartier Lille connu (les 10
    quartiers centraux de QUARTIERS_LILLE, ou Lomme/Hellemmes/Euralille via
    leur zone de repli dédiée), ou None si le nom n'est pas reconnu."""
    if quartier_nom in QUARTIERS_LILLE:
        z = QUARTIERS_LILLE[quartier_nom]
        radius = max(z["lat_max"] - z["lat_min"], z["lon_max"] - z["lon_min"]) / 2
        return z["centroid_lat"], z["centroid_lon"], radius
    if quartier_nom == "Lomme":
        z = FALLBACK_ZONE_LOMME
        return z["lat"], z["lon"], z["radius"]
    if quartier_nom == "Hellemmes":
        z = FALLBACK_ZONE_HELLEMMES
        return z["lat"], z["lon"], z["radius"]
    if quartier_nom == "Euralille":
        z = FALLBACK_ZONE_EURALILLE
        return z["lat"], z["lon"], z["radius"]
    return None


def match_quartier_lille(lat, lon):
    """Quartier réel dont la boîte englobante contient (lat, lon) ; en cas de
    chevauchement (quartiers limitrophes) ou d'absence de correspondance,
    renvoie le quartier au centroïde le plus proche — toujours un vrai nom,
    jamais de résultat vide pour un point dans l'agglomération lilloise."""
    candidates = [
        name for name, z in QUARTIERS_LILLE.items()
        if z["lat_min"] <= lat <= z["lat_max"] and z["lon_min"] <= lon <= z["lon_max"]
    ]
    pool = candidates or list(QUARTIERS_LILLE.keys())
    return min(
        pool,
        key=lambda name: (lat - QUARTIERS_LILLE[name]["centroid_lat"]) ** 2
        + (lon - QUARTIERS_LILLE[name]["centroid_lon"]) ** 2,
    )


def _lille_cavalier_zone(lat, lon):
    """Quartier/commune Lille le plus proche pour un cavalier (vraie
    coordonnée Overpass) — étend match_quartier_lille aux communes associées
    Lomme/Hellemmes/Euralille (hors des 10 quartiers centraux), pour pouvoir
    regrouper TOUS les cavaliers Lille par zone réelle, comme pour Lyon."""
    for nom, z in (("Lomme", FALLBACK_ZONE_LOMME), ("Hellemmes", FALLBACK_ZONE_HELLEMMES), ("Euralille", FALLBACK_ZONE_EURALILLE)):
        if (lat - z["lat"]) ** 2 + (lon - z["lon"]) ** 2 <= z["radius"] ** 2:
            return nom
    return match_quartier_lille(lat, lon)

# =============================================================================
# CONSTANTS (statuts valides)
# =============================================================================
STATUTS_VALIDES = {"active", "a_verifier", "inactive"}

# =============================================================================
# ETAPE 0 : FUSION PRESERVANTE DU STATUT (ORA-134 bis)
# =============================================================================
def _vu_au_dernier_scrape(df):
    """`sur_carte` : True si l'annonce a été revue lors du dernier scrape de son
    (ville, site), i.e. `date_dernier_scan` == max du groupe. Ne supprime rien :
    seule la carte filtre dessus, l'entraînement et l'historique de prix gardent
    toutes les lignes. Sans colonne `date_dernier_scan`, aucune info : True.
    # ponytail: granularité jour — un scrape à cheval sur minuit masquerait les
    # annonces du 1er jour ; passer à un identifiant de run si ça arrive."""
    if 'date_dernier_scan' not in df.columns:
        return pd.Series(True, index=df.index)
    scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True).dt.normalize()
    cles = [df[c] for c in ('ville', 'site') if c in df.columns]
    dernier = scan.groupby(cles).transform('max') if cles else scan.max()
    return scan == dernier


def step_flag_expired(df, previous_csv_path=None, ttl_days=None, reference_date=None):
    """Fusionne `df` (résultat frais de data_fusion.py) avec le `master_immo_final.csv`
    du run précédent pour calculer/préserver la colonne `statut` (ORA-134 bis).

    Remplace l'ancien `step_prune_expired`, qui excluait purement et simplement
    du dataframe les lignes dont `date_dernier_scan` dépassait `ttl_days` — un
    ré-entraînement hebdomadaire du pipeline complet aurait alors effacé le
    travail du DAG de nettoyage quotidien (`verify_annonces_async.py`, qui
    marque `inactive` sans jamais supprimer de ligne). Ici, aucune ligne n'est
    supprimée : on ne fait que calculer/reporter le `statut`.

    Règles de fusion (clé = `url`, seul identifiant stable inter-runs — voir
    Global Constraints du plan ORA-134 bis) :
    - Ligne absente du CSV précédent (première apparition) : `statut='active'`.
    - Ligne déjà `inactive` dans le CSV précédent : reste `inactive` (une
      confirmation de mort par vérification HTTP n'est jamais écrasée par une
      re-fusion — seul `verify_annonces_async.py` peut la faire repasser
      `active` s'il la re-confirme vivante).
    - Ligne présente dans `df` (le scrape frais) avec un `date_dernier_scan`
      récent (<= ttl_days) : `statut='active'` — réapparaître dans un scrape
      est une preuve directe de vie, y compris pour une ligne qui était
      `a_verifier`.
    - Ligne dont le `date_dernier_scan` dépasse `ttl_days` (non revue par le
      scraping depuis trop longtemps), ou absente du scrape courant mais
      présente précédemment et pas déjà `inactive` : `statut='a_verifier'` —
      candidate pour `verify_annonces_async.py`, jamais supprimée ici.
    - Exception à la règle précédente : si la ligne était `active` et que
      `derniere_verification_http` (posée par `verify_annonces_async.py`) est
      encore récente (<= ttl_days), elle reste `active` même si
      `date_dernier_scan` est stale/absent ce run — la confirmation HTTP est
      plus autoritaire que l'absence de re-scan, et l'écraser créerait une
      boucle de flip-flop quotidienne active <-> a_verifier.
    - Ligne absente du scrape courant (url introuvable dans `df`) : jamais
      supprimée, quel que soit son statut précédent — y compris `inactive`
      (une ligne `inactive` est, par construction, absente de tous les
      scrapes futurs ; l'exclure ici la ferait disparaître silencieusement de
      `master_immo_final.csv`, ce que cette fonction existe justement pour
      empêcher). Elle est réinjectée via `disparues` ci-dessous, qui conserve
      `inactive` tel quel et flague le reste en `a_verifier`.

    Conservateur par construction, comme l'ancien `step_prune_expired` : une
    ligne sans `date_dernier_scan` exploitable est traitée comme "non
    confirmée récemment" (a_verifier si elle a un statut précédent, sinon
    active par défaut faute d'information pour trancher plus fort).
    """
    print("\n🗑️  ETAPE 0 : Calcul du statut (fusion préservante, ORA-134 bis)...")

    # Default values for optional parameters
    if previous_csv_path is None:
        previous_csv_path = OUTPUT_FINAL_CSV
    if ttl_days is None:
        ttl_days = TTL_JOURS_DERNIER_SCAN

    reference_date = reference_date or pd.Timestamp.now(tz='UTC').normalize()

    if 'date_dernier_scan' in df.columns:
        dernier_scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True)
        age_jours = (reference_date - dernier_scan).dt.days
        vue_recemment = age_jours <= ttl_days  # NaN -> False (pas de preuve de fraîcheur)
    else:
        vue_recemment = pd.Series(False, index=df.index)

    previous_statut = {}
    previous_derniere_verif = {}
    previous_verif_recente = {}
    previous_df = None
    if os.path.exists(previous_csv_path):
        previous_df = _sans_colonnes_dupliquees(pd.read_csv(previous_csv_path))
        if 'statut' in previous_df.columns and 'url' in previous_df.columns:
            previous_statut = dict(zip(previous_df['url'], previous_df['statut']))
        if 'derniere_verification_http' in previous_df.columns and 'url' in previous_df.columns:
            previous_derniere_verif = dict(zip(previous_df['url'], previous_df['derniere_verification_http']))
            # Même pattern ttl_days/reference_date que `vue_recemment` ci-dessus,
            # appliqué cette fois à `derniere_verification_http` (le signal de
            # confirmation du vérificateur HTTP, plus autoritaire et parfois
            # plus récent que `date_dernier_scan` du scraper — Finding 2).
            verif_dates = pd.to_datetime(previous_df['derniere_verification_http'], errors='coerce', utc=True)
            age_verif_jours = (reference_date - verif_dates).dt.days
            recent_mask = age_verif_jours <= ttl_days
            previous_verif_recente = dict(zip(previous_df['url'], recent_mask))

    nouveau_statut = []
    nouveau_derniere_verif = []
    for url, deja_vu in zip(df['url'], vue_recemment):
        ancien = previous_statut.get(url)
        if ancien == 'inactive':
            nouveau_statut.append('inactive')
        elif deja_vu:
            nouveau_statut.append('active')
        elif ancien == 'active' and previous_verif_recente.get(url, False):
            # date_dernier_scan est stale/absente ce run, mais le vérificateur
            # HTTP (verify_annonces_async.py) a confirmé la ligne vivante plus
            # récemment que ttl_days : on ne l'écrase pas en a_verifier (sinon
            # boucle de flip-flop quotidienne active <-> a_verifier).
            nouveau_statut.append('active')
        elif ancien is not None:
            nouveau_statut.append('a_verifier')
        else:
            nouveau_statut.append('active')
        # Merge derniere_verification_http from previous CSV for matched rows
        nouveau_derniere_verif.append(previous_derniere_verif.get(url, ''))
    df = df.copy()
    df['statut'] = nouveau_statut
    df['derniere_verification_http'] = nouveau_derniere_verif
    df['sur_carte'] = _vu_au_dernier_scrape(df)

    # Lignes disparues du scrape courant (url absente de `df`), quel que soit
    # leur statut précédent (y compris `inactive` — Finding 1 : une ligne déjà
    # inactive est PAR DÉFINITION absente de tous les scrapes futurs ; l'exclure
    # ici la supprimerait silencieusement de master_immo_final.csv à chaque run
    # hebdomadaire, exactement la destruction que ce correctif ORA-134 bis
    # existe pour éliminer, et désynchroniserait annonces.db, qui n'est
    # qu'upserté et ne serait jamais notifié de la suppression). Conservées
    # toujours, jamais perdues (ORA-134 bis, étape 3.1 — "toute annonce absente
    # du nouveau scrape passe en à vérifier, pas supprimée directement").
    if os.path.exists(previous_csv_path) and previous_df is not None and 'url' in previous_df.columns:
        urls_courantes = set(df['url'])
        disparues = previous_df[
            ~previous_df['url'].isin(urls_courantes)
        ].copy()
        if len(disparues):
            # Ensure disparues has a statut column (default to a_verifier if missing).
            # Le lambda ci-dessous n'est PAS du code mort malgré les apparences :
            # il préserve `inactive` tel quel et ne flague en `a_verifier` que le
            # reste, maintenant que le filtre ci-dessus laisse bien passer les
            # lignes inactive jusqu'ici (avant le fix Finding 1, elles étaient
            # déjà exclues plus haut et ce lambda ne voyait jamais 'inactive').
            if 'statut' not in disparues.columns:
                disparues['statut'] = 'a_verifier'
            else:
                disparues['statut'] = disparues['statut'].apply(lambda s: s if s == 'inactive' else 'a_verifier')
            disparues['sur_carte'] = False
            print(f"   ↩️  {len(disparues)} annonce(s) absente(s) du scrape courant, conservée(s) (a_verifier ou inactive), retirée(s) de la carte.")
            df = pd.concat([df, disparues], ignore_index=True, sort=False)

    counts = df['statut'].value_counts().to_dict()
    print(f"   ✅ Statuts : {counts}")
    return df


def _sans_colonnes_dupliquees(df):
    """Retire les colonnes `nom.1`, `nom.2`… que pandas crée à la lecture d'un CSV
    dont l'en-tête répète `nom` (ex. `position_fiable`, ajoutée à chaque run par
    step_quartiers alors que le master précédent la contenait déjà)."""
    return df[[c for c in df.columns
               if not (re.search(r'\.\d+$', c) and re.sub(r'\.\d+$', '', c) in df.columns)]]


def load_sites_actifs(config_path=SCRAPING_CONFIG_PATH):
    """Clés des sites actifs (`sites_actifs` de scraping_config.json, ex. {'vizzit', 'orpi'}),
    ou None si la clé est absente (aucune restriction)."""
    with open(config_path, encoding='utf-8') as f:
        sites = json.load(f).get('sites_actifs')
    return set(sites) if sites else None


def step_archive_hors_master(df, archive_path=ARCHIVE_CSV, sites_actifs=None, aujourd_hui=None):
    """Le master ne garde que les annonces scrapées au dernier run de leur (ville, site),
    encore `active`, et d'un site actif. Toutes les autres sortent vers `master_archive.csv`.

    L'archive est cumulative : une ligne par (url, prix, date_dernier_scan), avec
    `archive_le` (date de sortie). Elle sert à suivre l'évolution des prix (anciennes +
    nouvelles annonces). Une annonce revenue dans un scrape ultérieur reprend son
    statut `active` et repart dans le master (l'historique reste dans l'archive).

    Renvoie (master, sortantes). `sortantes` garde son `statut` (`inactive` conservé,
    le reste devient `a_verifier`) pour que annonces.db cesse de les servir."""
    print("\n📦 ETAPE 0 bis : Archivage des annonces hors dernier run...")
    if sites_actifs is None:
        sites_actifs = load_sites_actifs()
    aujourd_hui = aujourd_hui or pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d')

    en_master = (df['statut'] == 'active') & df['sur_carte'].astype(bool)
    if sites_actifs:
        cle_site = df['site'].astype(str).str.lower().str.replace(' ', '', regex=False)
        en_master &= cle_site.isin(sites_actifs)

    sortantes = df[~en_master].copy()
    master = df[en_master].drop(columns=['position_fiable'], errors='ignore').reset_index(drop=True)
    if len(sortantes):
        sortantes['statut'] = sortantes['statut'].where(sortantes['statut'] == 'inactive', 'a_verifier')
        sortantes['sur_carte'] = False
        sortantes['archive_le'] = aujourd_hui
        archive = _sans_colonnes_dupliquees(pd.read_csv(archive_path)) if os.path.exists(archive_path) else None
        nouvelle = pd.concat([archive, _sans_colonnes_dupliquees(sortantes)], ignore_index=True, sort=False)
        nouvelle = nouvelle.drop_duplicates(subset=['url', 'prix', 'date_dernier_scan'], keep='last')
        tmp = archive_path + '.tmp'
        nouvelle.to_csv(tmp, index=False)
        os.replace(tmp, archive_path)
    print(f"   ✅ Master : {len(master)} annonces ; {len(sortantes)} archivée(s) dans {os.path.basename(archive_path)}.")
    return master, sortantes

# =============================================================================
# ETAPE 1 : GEOCODING & JITTER (geocoding_jitter.py)
# =============================================================================
def build_shapes_from_cavaliers(cavaliers_csv_path=CAVALIERS_CSV):
    """Dessine les zones basées sur les cavaliers (leur position réelle
    dessine la forme de chaque secteur, plutôt qu'une simple boîte/cercle).

    Renvoie un dict {clé: shapely.Polygon} au lieu de muter un global, pour
    rester testable avec des entrées/sorties explicites. La clé est le code
    postal pour Lyon (colonne `code_postal`, produite par
    enrich_cavaliers_cp.py) ; pour Lille (ORA-71 POC), où le CP ne délimite
    pas de zone significative pour le centre (cf. resolve_lille_quartier_hint
    dans clean_immo.py), c'est le nom de quartier réel résolu depuis les
    vraies coordonnées de chaque cavalier — même principe que Lyon (quadriller
    la ville à partir des cavaliers), appliqué au bon axe de regroupement
    pour cette ville. Les deux types de clés cohabitent dans le même dict ;
    get_point_for_zipcode() consulte chacune avec la bonne clé pour sa ville.
    """
    print("   🎨 Construction des formes géographiques...")
    polygons_map = {}

    if not os.path.exists(cavaliers_csv_path):
        print("   ⚠️ Pas de fichier cavaliers, utilisation des cercles simples.")
        return polygons_map

    try:
        df_cav = pd.read_csv(cavaliers_csv_path)

        if 'code_postal' in df_cav.columns:
            df_lyon = df_cav[df_cav['code_postal'].notna()].copy()
            df_sans_cp = df_cav[df_cav['code_postal'].isna()]
        else:
            df_lyon = df_cav.iloc[0:0]
            df_sans_cp = df_cav

        if not df_lyon.empty:
            df_lyon['code_postal'] = df_lyon['code_postal'].fillna(0).astype(str).apply(lambda x: x.split('.')[0])
            for cp, group in df_lyon.groupby('code_postal'):
                if len(group) >= 4:
                    points = list(zip(group.longitude, group.latitude))
                    polygons_map[cp] = MultiPoint(points).convex_hull.buffer(0.001)

        if not df_sans_cp.empty:
            zones = df_sans_cp.apply(lambda r: _lille_cavalier_zone(r['latitude'], r['longitude']), axis=1)
            for zone, group in df_sans_cp.assign(_zone=zones).groupby('_zone'):
                if len(group) >= 4:
                    points = list(zip(group.longitude, group.latitude))
                    polygons_map[zone] = MultiPoint(points).convex_hull.buffer(0.001)
    except Exception as e:
        print(f"   ⚠️ Erreur formes : {e}")

    return polygons_map

def get_random_point_in_polygon(polygon):
    minx, miny, maxx, maxy = polygon.bounds
    for _ in range(100):
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return p.y, p.x
    return polygon.centroid.y, polygon.centroid.x

def get_point_in_circle(center_lat, center_lon, radius):
    angle = random.uniform(0, 2 * np.pi)
    r = radius * np.sqrt(random.uniform(0, 1))
    return center_lat + r * np.cos(angle), center_lon + r * np.sin(angle)

def get_point_for_zipcode(cp, polygons_map, url=None, hint=None):
    # Communes limitrophes réelles (Lambersart, La Madeleine...) : jamais
    # clippées à LILLE_COMMUNE_POLYGON, ce ne sont pas des annonces Lille
    # (cf. ZONES_LIMITROPHES_LILLE). Vérifié avant la branche Lille
    # ci-dessous car ces CP commencent aussi par "59".
    if cp in CP_A_ZONE_LIMITROPHE:
        z = ZONES_LIMITROPHES_LILLE[CP_A_ZONE_LIMITROPHE[cp]]
        return get_point_in_circle(z["lat"], z["lon"], z["radius"])

    # Lille (ORA-71 POC) : priorité au quartier déduit de l'URL SeLoger
    # (signal structuré le plus fiable qu'on ait) ; sinon CP fiables
    # Lomme/Hellemmes/Euralille en zones dédiées ; sinon reste de la zone
    # centrale (59000/59800, ambiguë) sur la grande zone "Lille Centre" —
    # pas de fausse précision par CP quand aucun indice ne permet mieux.
    if cp.startswith('59'):
        # `hint` explicite (quartier trouvé par le texte) prime sur l'URL.
        hint = hint or resolve_lille_quartier_hint(url)
        if hint is None:
            if cp == '59160': hint = "Lomme"
            elif cp == '59260': hint = "Hellemmes"
            elif cp == '59777': hint = "Euralille"
        if hint:
            # Comme pour Lyon : si assez de vrais cavaliers dessinent une
            # forme pour ce quartier, on place le point dedans plutôt que
            # dans un simple cercle (build_shapes_from_cavaliers).
            if hint in polygons_map:
                # L'enveloppe convexe des cavaliers reste presque toujours
                # dans la commune (ses points d'origine y sont), mais la
                # vraie frontière n'est pas convexe : l'enveloppe peut
                # déborder légèrement dans un creux du contour — on la borne
                # au vrai contour, comme le cercle ci-dessous.
                clipped = polygons_map[hint].intersection(LILLE_COMMUNE_POLYGON)
                if not clipped.is_empty:
                    return get_random_point_in_polygon(clipped)
                return get_random_point_in_polygon(polygons_map[hint])
            zone = _lille_zone_center_and_radius(hint)
            if zone:
                lat, lon, radius = zone
                # Le cercle du quartier peut légèrement déborder de la vraie
                # commune près des bords (constaté : quelques centaines de
                # mètres, ex. Lille-Sud/Fives côté frontière) — on le borne
                # au vrai contour, comme le repli générique.
                clipped = Point(lon, lat).buffer(radius).intersection(LILLE_COMMUNE_POLYGON)
                if not clipped.is_empty:
                    return get_random_point_in_polygon(clipped)
                return get_point_in_circle(lat, lon, radius)
        # Repli générique (aucun indice de quartier) : tirage au sort dans
        # "Lille propre" (cf. LILLE_PROPRE_POLYGON) — jamais dans les
        # communes voisines (Lambersart, La Madeleine...) ni dans
        # Lomme/Hellemmes, qui ont leurs propres annonces (CP distinctif) et
        # ne doivent pas être polluées par des annonces à la position
        # inconnue placées là par hasard.
        return get_random_point_in_polygon(LILLE_PROPRE_POLYGON)

    if cp in polygons_map:
        return get_random_point_in_polygon(polygons_map[cp])
    elif cp in FALLBACK_ZONES:
        z = FALLBACK_ZONES[cp]
        return get_point_in_circle(z["lat"], z["lon"], z["radius"])
    else:
        return get_point_in_circle(45.7640, 4.8357, 0.02)

def clean_zipcode(val):
    try:
        return str(int(float(val))).strip()
    except:
        return str(val).strip()

def step_prune_expired(df, ttl_days=TTL_JOURS_DERNIER_SCAN, reference_date=None):
    """Exclut les annonces dont `date_dernier_scan` dépasse `ttl_days` (ORA-134) :
    une annonce non revue par le scraping depuis trop longtemps est considérée
    disparue du site source (louée, expirée, retirée) plutôt que de rester
    indéfiniment dans `master_immo_final.csv`/`annonces.db`.

    Conservateur par construction : une ligne sans `date_dernier_scan` exploitable
    (colonne absente du CSV d'entrée, ou valeur manquante/invalide — cas des
    lignes écrites avant l'ajout de cette colonne aux 6 scrapers) est conservée
    plutôt que purgée, faute d'information pour trancher. Le stock déjà
    accumulé avant ce correctif n'est donc nettoyé qu'au fil des prochains runs
    de scraping, pas rétroactivement ici (cf. le nettoyage ponctuel
    `prune_dead_annonces.py`, basé sur une vérification HTTP directe, pour le
    stock déjà en place au moment de ce correctif).
    """
    print("\n🗑️  ETAPE 0 : Purge des annonces expirées (TTL)...")

    if 'date_dernier_scan' not in df.columns:
        print("   ⚠️  Colonne 'date_dernier_scan' absente (CSV antérieur à ORA-134) : purge ignorée.")
        return df

    reference_date = reference_date or pd.Timestamp.now(tz='UTC').normalize()
    dernier_scan = pd.to_datetime(df['date_dernier_scan'], errors='coerce', utc=True)
    age_jours = (reference_date - dernier_scan).dt.days

    # NaN (date manquante/invalide) : comparaison pandas -> False -> conservée.
    expiree = age_jours > ttl_days
    if expiree.any():
        print(f"   ✅ {int(expiree.sum())} annonce(s) expirée(s) (non revue(s) depuis >{ttl_days}j) exclue(s).")
    else:
        print("   ✅ Aucune annonce expirée.")
    return df[~expiree].reset_index(drop=True)


# CP qui désignent une zone unique et fiable (étape 2 de step_geocoding) : les
# arrondissements lyonnais, Lomme/Hellemmes/Euralille et les communes limitrophes.
# 59000/59800/69000/69100 sont ambigus (ou à zone trop large) : pas de décision.
CP_FIABLES = {f"6900{i}" for i in range(1, 10)} | {"59160", "59260", "59777"} | set(CP_A_ZONE_LIMITROPHE)


def _source_cp_ou_url(cp, url):
    """'url' (slug de quartier SeLoger), 'cp' (CP fiable) ou None (ambigu)."""
    if cp in CP_A_ZONE_LIMITROPHE:
        return 'cp'
    if cp.startswith('59') and resolve_lille_quartier_hint(url):
        return 'url'
    return 'cp' if cp in CP_FIABLES else None


def _ville_de_la_ligne(row, cp):
    """'lille'/'lyon' d'après la colonne `ville`, sinon le préfixe du CP ; sinon None."""
    ville = str(row.get('ville') or '').strip().lower()
    if ville in ('lille', 'lyon'):
        return ville
    return {'59': 'lille', '69': 'lyon'}.get(cp[:2])


def _position_adresse(row, cp, ville, geocodeur):
    """(lat, lon, precision, cp_geocode) d'une adresse du bien trouvée dans le texte, sinon None.

    Lyon et Lille uniquement (le géocodeur est restreint à la commune ; une
    commune limitrophe est donc ignorée). Le CP du résultat doit être cohérent
    avec celui déjà connu : un arrondissement fiable doit correspondre exactement
    (rue homonyme d'un autre arrondissement = rejet).
    """
    if ville not in ('lyon', 'lille') or cp in CP_A_ZONE_LIMITROPHE:
        return None
    adresse, _raison = localiser_adresse(
        [row.get(c) for c in ('description_detail', 'description_raw', 'description')]
    )
    if not adresse:
        return None
    cp_connu = cp if cp in CP_FIABLES else None
    res = geocodeur(adresse, cp_connu, ville)
    prefixe = '690' if ville == 'lyon' else '59'
    if not res or not str(res['cp']).startswith(prefixe) or (cp_connu and res['cp'] != cp_connu):
        return None
    return res['lat'], res['lon'], res['precision'], res['cp']


def step_geocoding(df, cavaliers_csv_path=CAVALIERS_CSV, seed=GEOCODING_JITTER_SEED, geocodeur=geocoder):
    print("\n📍 ETAPE 1 : Géocodage & Jitter...")
    random.seed(seed)
    polygons_map = build_shapes_from_cavaliers(cavaliers_csv_path)

    df['code_postal'] = df['code_postal'].fillna(69000).apply(clean_zipcode)

    lats, lons, gps_reel, sources, zones_texte, precisions = [], [], [], [], [], []
    for _, row in df.iterrows():
        # Priorité stricte, la première règle qui s'applique gagne :
        # 1. GPS scrapé (Vizzit) — jamais écrasé
        if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')) and row.get('latitude') != "" and row.get('longitude') != "":
            try:
                lats.append(float(row['latitude']))
                lons.append(float(row['longitude']))
                gps_reel.append(True)
                sources.append('gps')
                zones_texte.append('')
                precisions.append('')
                continue
            except (TypeError, ValueError):
                pass  # conversion impossible : on génère

        cp, url = row['code_postal'], row.get('url')
        # 1 bis. Adresse du bien extraite du texte (ORA-180) : rue/numéro géocodés.
        # Pas de jitter : le point est celui de l'API. Échec/rejet → règles suivantes.
        ville = _ville_de_la_ligne(row, cp)
        pos = _position_adresse(row, cp, ville, geocodeur)
        if pos:
            lat, lon, precision, cp_geocode = pos
            lats.append(lat)
            lons.append(lon)
            # Lille : quartier déduit des coordonnées (branche a_gps_reel de trouver_quartier).
            gps_reel.append(ville == 'lille')
            sources.append('adresse')
            # Lyon : quartier via l'arrondissement géocodé, même si le CP de la ligne est ambigu.
            zones_texte.append(cp_geocode if ville == 'lyon' else '')
            precisions.append(precision)
            continue
        precisions.append('')
        # 2. CP fiable, ou slug de quartier d'URL SeLoger (même niveau)
        source = _source_cp_ou_url(cp, url)
        zone_texte = ''
        if source:
            lat, lon = get_point_for_zipcode(cp, polygons_map, url=url)
        else:
            # 3. Texte : lieu du bien explicite, uniquement si 1 et 2 n'ont rien donné
            zone, _raison = localiser_par_texte(
                [row.get(c) for c in ('description_detail', 'description_raw', 'description')],
                _ville_de_la_ligne(row, cp),
            )
            if zone:
                source, zone_texte = 'texte', zone
                lat, lon = get_point_for_zipcode(
                    zone if zone.startswith('69') else '59000', polygons_map,
                    hint=None if zone.startswith('69') else zone,
                )
            else:
                # 4. Jitter de repli (ville entière) : position fictive
                source = 'jitter'
                lat, lon = get_point_for_zipcode(cp, polygons_map)
        lats.append(lat)
        lons.append(lon)
        gps_reel.append(False)
        sources.append(source)
        zones_texte.append(zone_texte)

    df['latitude'] = lats
    df['longitude'] = lons
    df['source_localisation'] = sources
    # 'numero' (point exact) ou 'rue' (centre de la rue) pour source 'adresse', sinon vide.
    df['precision_localisation'] = precisions
    # Colonne de travail (comme a_gps_reel) : quartier/arrondissement décidé par
    # le texte, consommé par trouver_quartier() puis retirée par step_quartiers().
    df['zone_texte'] = zones_texte
    # Position fictive = pas sur la carte (la ligne reste dans le CSV/la base).
    sur_carte = df['sur_carte'].fillna(True).astype(bool) if 'sur_carte' in df.columns else True
    df['sur_carte'] = sur_carte & (df['source_localisation'] != 'jitter')
    # Colonne de travail (ORA-71 POC) : distingue une vraie coordonnée
    # (Vizzit) d'un point tiré au sort, consommée par trouver_quartier() pour
    # la zone centrale Lille ambiguë, puis retirée par step_quartiers() —
    # le schéma de master_immo_final.csv ne change pas.
    df['a_gps_reel'] = gps_reel
    # Texte brut consommé ci-dessus : retiré pour ne pas grossir le master ni
    # devenir une feature d'entraînement (train_model encode toute colonne texte).
    df = df.drop(columns=['description_raw'], errors='ignore')
    print(f"   ✅ {len(df)} annonces géolocalisées : {df['source_localisation'].value_counts().to_dict()}")
    return df

# =============================================================================
# ETAPE 2 : ASSIGNATION QUARTIERS (quartier_assignation.py)
# =============================================================================
def trouver_quartier(row):
    lat, lon = row['latitude'], row['longitude']
    if pd.isna(row['code_postal']): return "Inconnu"
    try: cp = str(int(float(row['code_postal'])))
    except: cp = str(row['code_postal'])

    if pd.isna(lat) or pd.isna(lon): return f"Secteur {cp}"

    # Quartier décidé par le texte (step_geocoding, étape 3) : nom Lille direct,
    # ou arrondissement Lyon (CP ambigu remplacé par celui du texte).
    zone_texte = row.get('zone_texte')
    if isinstance(zone_texte, str) and zone_texte:
        if zone_texte.startswith('69'): cp = zone_texte
        else: return zone_texte

    # Communes limitrophes réelles (pas des communes associées) : leur CP
    # distinctif suffit à les identifier directement, avant la branche Lille
    # ci-dessous (ces CP commencent aussi par "59").
    if cp in CP_A_ZONE_LIMITROPHE:
        return CP_A_ZONE_LIMITROPHE[cp]

    # Lille (ORA-71 POC) : priorité au quartier déduit de l'URL SeLoger
    # (signal structuré fourni par le site, cf. resolve_lille_quartier_hint)
    # — c'est ce qui donne une vraie répartition par quartier même sans GPS
    # réel. Sinon CP fiable pour Lomme/Hellemmes/Euralille (anciennes
    # communes/secteur propre). Le reste de la zone centrale (59000/59800)
    # n'est PAS distinctif géographiquement (La Poste accepte les deux CP
    # pour la même adresse) : quartier réel sinon seulement si coordonnées
    # réelles disponibles (Vizzit), sinon repli générique honnête (cf. spec).
    if cp.startswith('59'):
        hint = resolve_lille_quartier_hint(row.get('url'))
        if hint: return hint
        if cp == '59160': return "Lomme"
        if cp == '59260': return "Hellemmes"
        if cp == '59777': return "Euralille"
        if row.get('a_gps_reel'):
            # Coordonnée réelle, mais Vizzit étiquette parfois une annonce
            # d'une commune voisine comme "Lille" (constaté sur une vraie
            # fiche : "Croisé-Laroche, Marcq-en-Barœul (proximité Lille)"
            # affichée avec le titre "Location : Appartement Lille (59000)")
            # — pas de quartier Lille inventé pour un point qui n'y est pas.
            if LILLE_COMMUNE_POLYGON.contains(Point(lon, lat)):
                return match_quartier_lille(lat, lon)
        # "Lille / Non localisé" (pas juste "Lille") : une recherche par nom
        # de ville ("Lille") doit pouvoir agréger toutes les annonces de la
        # ville, repli inclus, sans que le nom du repli lui-même soit ambigu
        # avec une vraie recherche de quartier (cf. resolve_quartier_filter,
        # backend/services/quartier_search.py).
        return "Lille / Non localisé"

    if cp == '69001': return "Pentes Croix-Rousse" if lat > 45.769 else "Terreaux / Hotel de Ville"
    if cp == '69002': return "Confluence" if lat < 45.749 else "Ainay" if lat < 45.756 else "Bellecour / Cordeliers"
    if cp == '69003': return "Montchat" if lon > 4.875 else "Préfecture / Quais" if lon < 4.848 else "Part-Dieu / Villette"
    if cp == '69004': return "Croix-Rousse Plateau"
    if cp == '69005': return "Vieux Lyon" if lon > 4.818 else "Point du Jour / St Just"
    if cp == '69006': return "Brotteaux / Foch"
    if cp == '69007': return "Gerland" if lat < 45.736 else "Guillotière / Jean Macé"
    if cp == '69008': return "Monplaisir / Bachut"
    if cp == '69009': return "Vaise / Valmy"
    # Renommé (depuis "Grand Lyon / Autre") pour la même raison que le repli
    # Lille ci-dessus : rester cohérent entre les deux villes et permettre
    # une recherche par nom de ville sans ambiguïté avec le nom du repli.
    return "Lyon / Non localisé"

def step_quartiers(df):
    print("\n🗺️  ETAPE 2 : Détermination des quartiers...")
    df['quartier'] = df.apply(trouver_quartier, axis=1)
    # ORA-156 : conservé (renommé) jusqu'à master_immo_final.csv pour savoir
    # quelles annonces ont une position réelle (GPS Vizzit) vs jitterée.
    df = df.drop(columns=['zone_texte'], errors='ignore')
    if 'a_gps_reel' in df.columns:
        df = df.rename(columns={'a_gps_reel': 'position_fiable'})
    print("   ✅ Quartiers assignés.")
    return df

# =============================================================================
# ETAPE 3 : MISE A JOUR DES TYPES (update_types.py)
# =============================================================================
def determine_type_local(row):
    text = (str(row.get('type', '')) + " " + str(row.get('description', ''))).lower()
    surface = row.get('surface', 0)

    if re.search(r'\b(t[4-9]|f[4-9]|[4-9]\s*pièce|maison)\b', text): return 'Grand (T4+)'
    if re.search(r'\b(t3|f3|3\s*pièce)\b', text): return 'T3'
    if re.search(r'\b(t2|f2|2\s*pièce)\b', text): return 'T2'
    if re.search(r'\b(t1|f1|1\s*pièce|studio)\b', text): return 'Studio/T1'

    try:
        s = float(surface)
        if s < 35: return 'Studio/T1'
        elif s < 55: return 'T2'
        elif s < 75: return 'T3'
        else: return 'Grand (T4+)'
    except: return 'Inconnu'

def step_types(df):
    print("\n🏠 ETAPE 3 : Classification des types (T1, T2...)...")
    df['type_local'] = df.apply(determine_type_local, axis=1)
    print("   ✅ Types mis à jour.")
    return df

# =============================================================================
# ETAPE 4 : CALCUL FEATURES (compute_features.py)
# =============================================================================
def get_nearest_distance_and_count(df_main, df_poi):
    if len(df_poi) == 0:
        return np.full(len(df_main), np.nan), np.zeros(len(df_main))

    coords_main = np.radians(df_main[['latitude', 'longitude']].values)
    coords_poi = np.radians(df_poi[['latitude', 'longitude']].values)

    tree = BallTree(coords_poi, metric='haversine')
    dist_rad, _ = tree.query(coords_main, k=1)
    dist_meters = dist_rad[:, 0] * 6371000

    radius_rad = RADIUS_METERS / 6371000
    counts = tree.query_radius(coords_main, r=radius_rad, count_only=True)

    return dist_meters, counts

def step_features(df, df_cavaliers):
    """Calcule les distances/comptages aux points d'intérêt.

    `df_cavaliers` est fourni explicitement par l'appelant (plutôt que lu depuis un
    chemin de fichier en dur) pour rester testable avec un petit jeu de données en mémoire.
    Un `df_cavaliers` vide est un cas limite valide : `df` est renvoyé inchangé.

    Borné par ville quand les deux DataFrames le permettent (`df['ville']` +
    `df_cavaliers['code_postal']`, même convention que build_shapes_from_cavaliers :
    code_postal renseigné = cavalier Lyon, absent = cavalier Lille) : une annonce
    ne cherche jamais son POI le plus proche parmi ceux d'une autre ville. Sans
    effet numérique aujourd'hui vu la distance entre Lyon et Lille, mais correct
    par construction plutôt que par coïncidence géographique — et nécessaire dès
    qu'une 3e ville plus proche des deux premières serait ajoutée. Repli sur le
    comportement d'origine (non borné) si l'une des deux colonnes est absente
    (ex: jeux de données de test à une seule ville).
    """
    print("\n🧮 ETAPE 4 : Calcul des distances (Points d'intérêt)...")
    if df_cavaliers is None or df_cavaliers.empty:
        print("   ⚠️ Pas de données cavaliers, aucune feature de distance calculée.")
        return df

    categories = df_cavaliers['categorie_cavalier'].unique()

    if 'ville' in df.columns and 'code_postal' in df_cavaliers.columns:
        cavaliers_par_ville = {
            'Lyon': df_cavaliers[df_cavaliers['code_postal'].notna()],
            'Lille': df_cavaliers[df_cavaliers['code_postal'].isna()],
        }
        annonces_par_ville = dict(list(df.groupby('ville')))
    else:
        cavaliers_par_ville = {None: df_cavaliers}
        annonces_par_ville = {None: df}

    for cat in categories:
        clean_name = cat.replace(" - ", "_").replace(" ", "_").lower()
        dist_col = f"dist_{clean_name}"
        count_col = f"nb_{clean_name}_{RADIUS_METERS}m"
        df[dist_col] = np.nan
        df[count_col] = 0

        for ville_nom, df_ville in annonces_par_ville.items():
            if df_ville.empty:
                continue
            subset_cav = cavaliers_par_ville.get(ville_nom, df_cavaliers)
            subset_cav = subset_cav[subset_cav['categorie_cavalier'] == cat]

            dists, counts = get_nearest_distance_and_count(df_ville, subset_cav)
            df.loc[df_ville.index, dist_col] = np.round(dists, 0)
            df.loc[df_ville.index, count_col] = counts

        print(f"   🔹 {cat} traité.")

    print("   ✅ Features calculées.")
    return df

# =============================================================================
# ETAPE 5 : CORRECTION IDS (fix_ids.py)
# =============================================================================
def step_ids(df):
    print("\n🔧 ETAPE 5 : Réindexation des IDs...")
    df['id_annonce'] = range(1, len(df) + 1)
    print(f"   ✅ {len(df)} annonces réindexées.")
    return df

# =============================================================================
# ETAPE 6 : SYNCHRONISATION DU STORE SQLITE (ORA-112)
# =============================================================================
def build_titre(row):
    """Pas de vrai champ 'titre' dans le CSV master (seulement 'description',
    un texte libre déjà nettoyé par data_fusion.py) : on synthétise un titre
    court et lisible à partir du type de bien + quartier, cohérent avec ce
    qu'affiche AnnonceCard.jsx."""
    type_local = str(row.get('type_local') or '').strip()
    quartier = str(row.get('quartier') or '').strip()
    if type_local and quartier:
        return f"{type_local} — {quartier}"
    return type_local or quartier or str(row.get('description') or '').strip()[:80] or None


def step_sync_annonces_store(df, db_path=ANNONCES_DB_PATH):
    """Alimente la table SQLite `annonces` (services/annonces_store.py) à partir
    du dataframe final, pour que `/api/annonces` (liste "Annonces récentes",
    tracking de clics) ait réellement des données à servir — jusqu'ici cette
    table n'était peuplée que par les tests unitaires, jamais par le pipeline
    (ORA-112). `upsert_annonce` dédoublonne par `url` (contrainte UNIQUE),
    donc rejouer cette étape sur les mêmes annonces les met juste à jour.
    """
    print("\n🗃️  ETAPE 6 : Synchronisation du store annonces (SQLite)...")
    annonces_store.init_db(db_path)

    synced = 0
    skipped_url = 0
    skipped_autre = 0
    for _, row in df.iterrows():
        url = row.get('url')
        if not isinstance(url, str) or not url.strip():
            skipped_url += 1
            continue

        image = row.get('image')
        images = [image] if isinstance(image, str) and image.strip() else None

        # Finding 5 : une valeur de statut corrompue/invalide ne doit pas se
        # propager telle quelle jusqu'à upsert_annonce (qui lève ValueError
        # pour un statut hors STATUTS_VALIDES) — sinon la ligne finit
        # silencieusement ignorée et journalisée comme "url manquante", ce qui
        # est faux et masque le vrai problème. On coerce vers 'a_verifier',
        # la valeur par défaut prudente déjà utilisée ailleurs dans ce module
        # (cf. step_flag_expired) pour un statut inconnu/indéterminé.
        statut_brut = row.get('statut') or 'active'
        statut = statut_brut if statut_brut in STATUTS_VALIDES else 'a_verifier'

        try:
            annonces_store.upsert_annonce(
                titre=build_titre(row),
                prix=float(row['prix']) if pd.notna(row.get('prix')) else None,
                surface=float(row['surface']) if pd.notna(row.get('surface')) else None,
                ville=row.get('ville') or None,
                quartier=row.get('quartier') or None,
                url=url,
                images=images,
                statut=statut,
                derniere_verification=row.get('derniere_verification_http') or None,
                db_path=db_path,
            )
            synced += 1
        except ValueError as exc:
            # Deux causes distinctes possibles malgré le filtre ci-dessus (garde-fou) :
            # url vide/blanche après strip (le cas attendu), ou toute autre
            # ValueError inattendue d'upsert_annonce (ex. contrainte future) —
            # on les distingue pour ne pas mentir dans le log ci-dessous.
            if "url" in str(exc).lower():
                skipped_url += 1
            else:
                skipped_autre += 1
                print(f"   ⚠️  Ligne ignorée (erreur upsert, pas url) : {exc}")

    skipped = skipped_url + skipped_autre
    print(f"   ✅ {synced} annonces synchronisées, {skipped} ignorées "
          f"({skipped_url} url manquante, {skipped_autre} autre erreur).")
    return df

# =============================================================================
# MAIN PIPELINE
# =============================================================================
def load_cavaliers(cavaliers_csv_path=CAVALIERS_CSV):
    """Charge le CSV des cavaliers, ou un DataFrame vide (mêmes colonnes) s'il est absent."""
    if os.path.exists(cavaliers_csv_path):
        return pd.read_csv(cavaliers_csv_path)
    return pd.DataFrame(columns=['categorie_cavalier', 'type_osm', 'nom_lieu', 'latitude', 'longitude'])

def main():
    print("🚀 DÉMARRAGE DU PIPELINE ETL COMPLET")
    print(f"📂 Entrée : {INPUT_RAW_CSV}")
    print(f"📂 Sortie : {OUTPUT_FINAL_CSV}")

    # 1. Chargement initial
    if not os.path.exists(INPUT_RAW_CSV):
        print("❌ Fichier d'entrée introuvable.")
        return

    df = pd.read_csv(INPUT_RAW_CSV)
    df_cavaliers = load_cavaliers(CAVALIERS_CSV)

    # 2. Exécution séquentielle en mémoire (orchestration pure, pas de logique métier ici)
    df = step_flag_expired(df)
    df, df_sortantes = step_archive_hors_master(df)
    df = step_geocoding(df, CAVALIERS_CSV)
    df = step_quartiers(df)
    df = step_types(df)
    df = step_features(df, df_cavaliers)
    df = step_ids(df)

    # 3. Sauvegarde finale
    print(f"\n💾 Sauvegarde finale vers {OUTPUT_FINAL_CSV}...")
    df.to_csv(OUTPUT_FINAL_CSV, index=False)
    print("✨ TERMINÉ ! Le fichier master est prêt.")

    # 4. Synchronisation du store SQLite consommé par /api/annonces (ORA-112)
    # Les annonces archivées sont synchronisées aussi (statut a_verifier/inactive) : sans ça,
    # annonces.db continuerait de servir comme « active » une annonce sortie du master.
    step_sync_annonces_store(pd.concat([df, df_sortantes], ignore_index=True, sort=False))

if __name__ == "__main__":
    main()
