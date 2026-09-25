import re

CATEGORY_ORDER = ['vice', 'gentrification', 'nuisance', 'superstition']
CATEGORY_LABELS = {
    'vice': 'Vice',
    'gentrification': 'Gentrification',
    'nuisance': 'Nuisance',
    'superstition': 'Superstition',
}

DIST_COLUMN_RE = re.compile(r'^dist_(vice|gentrification|nuisance|superstition)_(.+)$')

# Une phrase concrète et cynique par type de POI connu (ton du reste de
# l'app, cf. README) plutôt qu'un score abstrait. `{n}` = nombre moyen à
# moins de `{rayon}` (mètres), `{dist_m}` = distance moyenne au plus proche
# (mètres). `{rayon}` est paramétré (summarize_cavaliers, /api/cavaliers) —
# 500 par défaut pour ne rien changer aux appelants existants
# (/api/quartier-stats, export PDF, tous fixés à ce rayon).
POI_PHRASES = {
    ('vice', 'sex-shop'): "Un sex-shop à {dist_m}m — le quartier a plus d'un tour dans son sac.",
    ('vice', 'bar'): "{n} bar(s) à moins de {rayon}m — parfait pour un verre, moins pour dormir.",
    ('vice', 'tabac'): "Un bureau de tabac à {dist_m}m — la cigarette du matin n'a jamais été aussi accessible.",
    ('vice', 'cbd_shop'): "Une boutique CBD à {dist_m}m — le quartier gère son stress à sa façon.",
    ('vice', 'kebab'): "{n} kebab(s) à moins de {rayon}m — le vrai indicateur de vie nocturne.",
    ('vice', 'casino'): "Un casino à {dist_m}m — vos voisins jouent peut-être plus gros que le loyer.",
    ('gentrification', 'épicerie_fine'): "Une épicerie fine à {dist_m}m — le loyer du quartier vous remercie.",
    ('gentrification', 'atelier_vélo'): "Un atelier vélo à {dist_m}m — ici, on pédale plutôt qu'on ne prend le bus.",
    ('gentrification', 'salle_sport'): "Une salle de sport à {dist_m}m — la gentrification muscle aussi les mollets.",
    ('gentrification', 'crèche'): "Une crèche à {dist_m}m — familles avec poussette tout-terrain en approche.",
    ('gentrification', 'yoga'): "Un studio de yoga à {dist_m}m — le namaste du quartier qui monte.",
    ('gentrification', 'torréfacteur'): "Un torréfacteur artisanal à {dist_m}m — le café à 5€ n'est plus très loin.",
    ('gentrification', 'fleuriste'): "Un fleuriste à {dist_m}m — même les trottoirs sont instagrammables.",
    ('nuisance', 'aire_de_jeux'): "Une aire de jeux à {dist_m}m — cris d'enfants inclus, gratuitement.",
    ('nuisance', 'discothèque'): "Une discothèque à {dist_m}m — les boules quiès seront vos meilleures amies.",
    ('nuisance', 'école'): "Une école à {dist_m}m — la sonnerie de 8h20 sera votre nouveau réveil.",
    ('nuisance', 'salle_de_concert'): "Une salle de concert à {dist_m}m — les basses passent mieux que le loyer.",
    ('nuisance', 'station_service'): "Une station-service à {dist_m}m — pratique le matin, bruyant la nuit.",
    ('superstition', 'pompes_funèbres'): "Des pompes funèbres à {dist_m}m — voisinage discret garanti.",
    ('superstition', 'cimetière'): "Un cimetière à {dist_m}m — calme absolu, dans tous les sens du terme.",
}

GENERIC_PHRASES = {
    'vice': "{n} '{poi}' à moins de {rayon}m — l'ambiance ne manque pas.",
    'gentrification': "Un '{poi}' à {dist_m}m — encore un signe de gentrification.",
    'nuisance': "Un '{poi}' à {dist_m}m — à prendre en compte pour vos nuits.",
    'superstition': "Un '{poi}' à {dist_m}m — pour les âmes sensibles.",
}

ABSENCE_PHRASES = {
    'vice': "Aucune tentation (bar, kebab, casino...) à moins de {rayon}m — un quartier sage.",
    'gentrification': "Aucun signe de gentrification marquant (épicerie fine, yoga...) à moins de {rayon}m — encore un quartier authentique.",
    'nuisance': "Aucune nuisance notable (école, discothèque...) à moins de {rayon}m — la paix, tout simplement.",
    'superstition': "Ni cimetière ni pompes funèbres à moins de {rayon}m — rien à signaler côté au-delà.",
}

# En dessous de ce seuil de densité moyenne à 500m, on considère qu'il n'y a
# pas de signal notable pour la catégorie (bascule sur ABSENCE_PHRASES).
PRESENCE_THRESHOLD = 0.5

# Rayon par défaut de summarize_cavaliers/detail_cavaliers : ce sont les
# seules colonnes précalculées disponibles dans master_immo_final.csv
# (nb_<cat>_<poi>_500m) — /api/quartier-stats et l'export PDF restent fixés
# à cette valeur. /api/cavaliers (services/cavaliers_radius.py) calcule lui
# en direct pour 300/500/1000m et passe son propre rayon à `phrase_for`/
# `ABSENCE_PHRASES`.
DEFAULT_RAYON_M = 500


def list_poi_types(df):
    """Introspecte les colonnes `dist_<catégorie>_<poi>` réellement présentes
    dans `df` pour retrouver les types de POI par catégorie de cavalier, sans
    dépendre d'une liste figée — une nouvelle catégorie ajoutée en amont
    (cavaliers_lyon.csv / clean_immo.py) est prise en compte automatiquement."""
    result = {}
    for col in df.columns:
        match = DIST_COLUMN_RE.match(col)
        if match:
            category, poi = match.groups()
            result.setdefault(category, []).append(poi)
    return result


def phrase_for(category, poi, n, dist_m, rayon=DEFAULT_RAYON_M):
    """Phrase concrète pour un `poi` connu (POI_PHRASES) ou, à défaut, une
    phrase générique par catégorie (GENERIC_PHRASES). Partagée avec
    services/cavaliers_radius.py (calcul en direct par rayon choisi)."""
    template = POI_PHRASES.get((category, poi), GENERIC_PHRASES[category])
    return template.format(n=n, dist_m=dist_m, poi=poi.replace('_', ' '), rayon=rayon)


def summarize_cavaliers(df_subset, rayon=DEFAULT_RAYON_M):
    """Résume les 4 "Cavaliers" (Vice, Gentrification, Nuisance, Superstition)
    pour un sous-ensemble d'annonces (ex : celles d'un quartier), sous forme de
    phrases concrètes et cynique — pas un score abstrait — pour rester lisible
    hors de l'application (export PDF, ORA-73).

    Pour chaque catégorie, sélectionne le type de POI le plus présent (densité
    moyenne à `rayon` la plus élevée) ; si aucun n'atteint PRESENCE_THRESHOLD,
    utilise une phrase d'absence plutôt que de citer un POI non représentatif.

    `rayon` (mètres, défaut 500) : uniquement le libellé inséré dans les
    phrases ("... à moins de {rayon}m") — les colonnes `nb_*_500m` sous-
    jacentes restent toujours calculées à 500m (features du modèle, jamais
    recalculées ici) ; ne passer un autre rayon que si `df_subset` a été
    filtré/calculé en conséquence par l'appelant (cf. cavaliers_radius.py).

    Renvoie une liste de dicts `{"categorie": <label>, "phrase": <texte>}`,
    dans l'ordre Vice / Gentrification / Nuisance / Superstition, en sautant
    une catégorie totalement absente des colonnes de `df_subset`.
    """
    poi_types_by_category = list_poi_types(df_subset)
    factors = []

    for category in CATEGORY_ORDER:
        poi_types = poi_types_by_category.get(category)
        if not poi_types:
            continue

        best_poi = None
        best_n = -1
        best_dist = None
        for poi in poi_types:
            nb_col = f"nb_{category}_{poi}_500m"
            dist_col = f"dist_{category}_{poi}"
            n_mean = df_subset[nb_col].mean() if nb_col in df_subset.columns else 0
            dist_mean = df_subset[dist_col].mean() if dist_col in df_subset.columns else None
            if n_mean != n_mean:  # NaN (colonne entièrement vide sur ce sous-ensemble)
                n_mean = 0
            if n_mean > best_n:
                best_n = n_mean
                best_poi = poi
                best_dist = dist_mean

        if best_poi is None or best_n < PRESENCE_THRESHOLD:
            phrase = ABSENCE_PHRASES[category].format(rayon=rayon)
        else:
            dist_m = round(float(best_dist)) if best_dist is not None and best_dist == best_dist else 0
            phrase = phrase_for(category, best_poi, round(float(best_n)), dist_m, rayon=rayon)

        factors.append({"categorie": CATEGORY_LABELS[category], "phrase": phrase})

    return factors


def detail_cavaliers(df_subset):
    """Détail complet des 4 Cavaliers pour un sous-ensemble d'annonces (ORA-172,
    panneau "Les 4 Cavaliers · rayon 500 m") : contrairement à
    `summarize_cavaliers` (une phrase, le POI le plus présent), renvoie TOUS
    les sous-types avec leur compte (densité moyenne à 500m, arrondie) et leur
    distance minimale observée dans le sous-ensemble — pour lister "Bar 12 ·
    dès 46 m", "Tabac 3 · dès 158 m", etc.

    Renvoie une liste de dicts `{"categorie", "total", "items": [{"poi",
    "count", "dist_m"}, ...], "empty_message"}`, `items` triés par `count`
    décroissant, `empty_message` renseigné (sinon None) quand aucun sous-type
    n'atteint PRESENCE_THRESHOLD — nommant le POI le plus proche tous types
    confondus, à défaut de densité notable (ex. "Rien dans le rayon. Pompes
    funèbres les plus proches à 573 m.").
    """
    poi_types_by_category = list_poi_types(df_subset)
    result = []

    for category in CATEGORY_ORDER:
        poi_types = poi_types_by_category.get(category)
        if not poi_types:
            continue

        items = []
        closest = None  # (poi, dist_m) le plus proche tous types confondus
        for poi in poi_types:
            nb_col = f"nb_{category}_{poi}_500m"
            dist_col = f"dist_{category}_{poi}"
            n_mean = df_subset[nb_col].mean() if nb_col in df_subset.columns else 0
            if n_mean != n_mean:  # NaN
                n_mean = 0

            dist_min = df_subset[dist_col].min() if dist_col in df_subset.columns else None
            dist_m = round(float(dist_min)) if dist_min is not None and dist_min == dist_min else None
            if dist_m is not None and (closest is None or dist_m < closest[1]):
                closest = (poi, dist_m)

            n_rounded = round(float(n_mean))
            if n_rounded >= PRESENCE_THRESHOLD:
                items.append({
                    "poi": poi.replace('_', ' ').capitalize(),
                    "count": n_rounded,
                    "dist_m": dist_m,
                })

        items.sort(key=lambda item: item["count"], reverse=True)

        empty_message = None
        if not items:
            if closest is not None:
                empty_message = f"Rien dans le rayon. {closest[0].replace('_', ' ').capitalize()} les plus proches à {closest[1]} m."
            else:
                empty_message = "Rien dans le rayon."

        result.append({
            "categorie": CATEGORY_LABELS[category],
            "total": sum(item["count"] for item in items),
            "items": items,
            "empty_message": empty_message,
        })

    return result
