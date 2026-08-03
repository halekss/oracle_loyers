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
# moins de 500m, `{dist_m}` = distance moyenne au plus proche (mètres).
POI_PHRASES = {
    ('vice', 'sex-shop'): "Un sex-shop à {dist_m}m — le quartier a plus d'un tour dans son sac.",
    ('vice', 'bar'): "{n} bar(s) à moins de 500m — parfait pour un verre, moins pour dormir.",
    ('vice', 'tabac'): "Un bureau de tabac à {dist_m}m — la cigarette du matin n'a jamais été aussi accessible.",
    ('vice', 'cbd_shop'): "Une boutique CBD à {dist_m}m — le quartier gère son stress à sa façon.",
    ('vice', 'kebab'): "{n} kebab(s) à moins de 500m — le vrai indicateur de vie nocturne.",
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
    'vice': "{n} '{poi}' à moins de 500m — l'ambiance ne manque pas.",
    'gentrification': "Un '{poi}' à {dist_m}m — encore un signe de gentrification.",
    'nuisance': "Un '{poi}' à {dist_m}m — à prendre en compte pour vos nuits.",
    'superstition': "Un '{poi}' à {dist_m}m — pour les âmes sensibles.",
}

ABSENCE_PHRASES = {
    'vice': "Aucune tentation (bar, kebab, casino...) à moins de 500m — un quartier sage.",
    'gentrification': "Aucun signe de gentrification marquant (épicerie fine, yoga...) à moins de 500m — encore un quartier authentique.",
    'nuisance': "Aucune nuisance notable (école, discothèque...) à moins de 500m — la paix, tout simplement.",
    'superstition': "Ni cimetière ni pompes funèbres à moins de 500m — rien à signaler côté au-delà.",
}

# En dessous de ce seuil de densité moyenne à 500m, on considère qu'il n'y a
# pas de signal notable pour la catégorie (bascule sur ABSENCE_PHRASES).
PRESENCE_THRESHOLD = 0.5


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


def _phrase_for(category, poi, n, dist_m):
    template = POI_PHRASES.get((category, poi), GENERIC_PHRASES[category])
    return template.format(n=n, dist_m=dist_m, poi=poi.replace('_', ' '))


def summarize_cavaliers(df_subset):
    """Résume les 4 "Cavaliers" (Vice, Gentrification, Nuisance, Superstition)
    pour un sous-ensemble d'annonces (ex : celles d'un quartier), sous forme de
    phrases concrètes et cynique — pas un score abstrait — pour rester lisible
    hors de l'application (export PDF, ORA-73).

    Pour chaque catégorie, sélectionne le type de POI le plus présent (densité
    moyenne à 500m la plus élevée) ; si aucun n'atteint PRESENCE_THRESHOLD,
    utilise une phrase d'absence plutôt que de citer un POI non représentatif.

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
            phrase = ABSENCE_PHRASES[category]
        else:
            dist_m = round(float(best_dist)) if best_dist is not None and best_dist == best_dist else 0
            phrase = _phrase_for(category, best_poi, round(float(best_n)), dist_m)

        factors.append({"categorie": CATEGORY_LABELS[category], "phrase": phrase})

    return factors
