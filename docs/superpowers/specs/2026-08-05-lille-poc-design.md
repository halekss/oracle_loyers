# POC multi-ville : ajout de Lille (2026-08-05)

## Objectif

Faire un test rapide (preuve de concept) pour valider que le pipeline Oracle
des Loyers peut couvrir une deuxième ville, Lille, et l'afficher sur la
carte du frontend. Priorité : voir de vraies données Lille sur la carte le
plus vite possible, quitte à adapter/dupliquer ponctuellement la logique
Lyon plutôt que construire une architecture multi-ville pleinement générique
tout de suite. Une généralisation plus poussée pourra être faite plus tard
si ce test est concluant.

Ce spec fait suite au travail ORA-71 (`README.md:238-249`), qui a déjà rendu
génériques les scrapers, le stockage des annonces et l'entraînement du
modèle ML. Ce qui manque encore pour "voir une ville sur la carte" est
détaillé ci-dessous.

## Décisions de cadrage

1. **Portée** : preuve de concept rapide, pas de généralisation complète de
   toute la chaîne (ex: pas de reverse-geocoding automatique, pas de
   refonte de `chat_service.py`).
2. **Source de données** : scraping réel sur les 6 sites existants
   (Century21, Orpi, PAP, SeLoger, Vizzit, Paruvendu), URLs Lille à vérifier
   à la main dans `scripts/scraping_config.json`.
3. **Granularité "quartier"** pour Lille : le code postal (ex: `59000`,
   `59800`...), pas les vrais noms de quartiers ni de reverse-geocoding.
   Comme les CP Lyon (69xxx) et Lille (59xxx) ne se chevauchent jamais,
   aucune ambiguïté de recherche entre les deux villes.
4. **Affichage carte** : un sélecteur de ville dans l'UI qui bascule entre
   deux cartes HTML statiques générées séparément (une par ville), pas de
   carte unique fusionnée.
5. **Combinaison des données** : un seul pipeline/dataset combiné
   (`master_immo_final.csv` avec une colonne `ville`), pas deux pipelines
   parallèles. Cohérent avec l'architecture actuelle du backend (un seul
   `DataLoader`, un seul modèle) et déjà supporté par `train_model.py`
   (testé par `MultiCityFeatureGenericizationTest`).
6. **Chat "Immotep"** : non généralisé dans ce POC. Le prompt système reste
   "conseiller lyonnais" et la regex d'arrondissement (`6900[1-9]`) ne
   matchera simplement pas les CP Lille (59xxx) — Immotep répondra sur
   Lille via la recherche générale (quartier/prix), sans le mode spécial
   "arrondissement". Limitation connue, acceptée pour ce POC.

## Design détaillé

### 1. Scraping (`scripts/scraping_config.json`)

Ajout d'un bloc `"lille"` dans `villes`, avec les 6 URLs de recherche
vérifiées à la main pour Lille (même structure que le bloc `"lyon"`
existant). Aucun changement de code scraper : `scraper_utils.py` et les 6
scrapers lisent déjà la config sans nom de ville en dur (ORA-71).

### 2. Fusion des données brutes (`backend/scripts/data_fusion.py`)

- Remplacer la liste de fichiers en dur (lignes ~74-78, ~129) par une
  boucle sur les villes déclarées dans `scraping_config.json`, construisant
  les noms de fichiers via leur `slug` (`annonces_{slug}_{site}.csv`).
- Remplacer `df['ville'] = 'Lyon'` codé en dur (lignes ~111, ~144) par le
  nom de la ville courante de la boucle.
- Sortie : un seul CSV combiné (renommé, ex.
  `base_de_donnees_immo_complet.csv`, ex-`..._lyon_complet.csv`)
  contenant les deux villes.
- La regex d'extraction d'arrondissement (`lyon\s*(\d{1,2})`, lignes ~35/60)
  reste inchangée ; elle ne matche simplement rien sur les lignes Lille
  (comportement correct, Lille n'a pas d'arrondissements numérotés).

### 3. Nettoyage & résolution de quartier (`backend/scripts/clean_immo.py`)

- `INPUT_RAW_CSV`/`OUTPUT_FINAL_CSV` renommés (suppression du `_lyon_`),
  mais toujours un seul fichier en entrée/sortie.
- `CAVALIERS_CSV` pointe vers un `cavaliers_all.csv` combiné (fusion de
  `cavaliers_lyon.csv` + `cavaliers_lille.csv`, chacun généré une fois par
  `api_overpass.py`, déjà générique via `resolve_active_city_name()`).
- `build_shapes_from_cavaliers()` : suppression du filtre
  `startswith('69')` (ligne ~63) — le regroupement par code postal sépare
  déjà naturellement les deux villes, le filtre devient inutile.
- `FALLBACK_ZONES` (lignes ~31-42) : ajout des CP Lille (59000, 59800,
  59160, 59260, 59777, 59110, 59700...) avec un centre lat/lon approximatif
  par CP.
- `trouver_quartier()` (lignes ~136-153) : ajout d'une branche
  `if cp.startswith('59'): return f"Lille {cp}"` avant le bloc de règles
  Lyon. Le bloc Lyon existant (69001-69009, seuils lat/lon) reste identique
  — zéro régression sur Lyon.
- Le fallback ultime `get_point_in_circle(45.7640, 4.8357, 0.02)` (centre
  Lyon, ligne ~96) reste tel quel comme filet de sécurité ; comme tous les
  CP Lille seront couverts par `FALLBACK_ZONES`, il ne devrait jamais être
  atteint pour des données Lille.

### 4. Modèle ML & backend (`train_model.py`, `backend/app.py`)

- `train_model.py` tourne sur le nouveau `master_immo_final.csv` combiné,
  sans changement de code (déjà générique — `ville` encodée en one-hot dès
  que 2 valeurs distinctes existent). Nouveau `price_predictor.pkl`
  committé.
- `backend/app.py` ligne 165 : `CAVALIERS_PATH` pointe vers
  `cavaliers_all.csv` au lieu de `cavaliers_lyon.csv`.
- Aucun changement à `backend/schemas.py` : `/api/quartier-stats` et
  `/api/predict` (recherche par `str.contains` sur le quartier)
  fonctionnent sans ambiguïté sans paramètre `ville` supplémentaire, grâce
  à la décision #3 (CP Lyon et Lille disjoints). `/api/annonces?ville=...`
  fonctionne déjà (existant, ORA-84).

### 5. Génération de la carte (`backend/scripts/generate_map.py`)

- Ajout d'un paramètre CLI `--ville` : filtre `master_immo_final.csv` sur
  la ville demandée, sélectionne `POI_CSV`/`METRO_JSON`/`OUTPUT_HTML` et le
  centre de `folium.Map(location=[...])` en fonction de la ville, au lieu
  des constantes en dur (lignes ~19, ~23-24, ~158).
- La couche transport en commun (`METRO_JSON`) devient optionnelle : si le
  fichier n'existe pas pour la ville demandée, la couche est simplement
  omise au lieu de faire planter le script. Lille n'aura donc pas de
  couche métro/tram dans ce POC.
- Le script tourne deux fois (`--ville lyon`, `--ville lille`), produisant
  `map_pings_lyon_calques.html` (inchangé) et `map_pings_lille_calques.html`
  (nouveau).

### 6. Frontend — sélecteur de ville

- Nouveau state `ville` dans `frontend/src/App.jsx` (défaut `'lyon'`),
  propagé à `MapComponent`.
- `frontend/src/components/MapComponent.jsx` ligne 40 : le `mapUrl` en dur
  devient `` `/data/map_pings_${ville}_calques.html?...` ``.
- Petit sélecteur UI (2 boutons "Lyon"/"Lille", même style visuel que les
  filtres T1/T2/T3 existants) ajouté près de la recherche
  (`SearchForm.jsx` ou `App.jsx`). Au clic : change `ville`, recharge
  l'iframe de la carte. Pas de filtrage additionnel de la recherche par
  quartier (non nécessaire, cf. décision #3).

## Hors périmètre (explicitement)

- Généralisation complète de `chat_service.py` (prompt, extraction
  d'arrondissement).
- Reverse-geocoding automatique ou vrais contours de quartiers pour Lille.
- Carte unique fusionnant les deux villes.
- Couche transport en commun (métro/tram) pour Lille.
- Ajout d'un paramètre `ville` aux schémas `/api/quartier-stats` et
  `/api/predict`.

## Tests

- Réutiliser/étendre `MultiCityFeatureGenericizationTest`
  (`backend/tests/test_model_regression.py`) avec les vraies données Lille
  une fois disponibles, en complément du test à ville fictive existant.
- Vérifier `ResolveActiveCityNameTest`
  (`backend/tests/test_api_overpass.py`) reste vert après ajout du bloc
  `lille` dans `scraping_config.json`.
- Test manuel frontend : sélecteur Lyon/Lille bascule bien la carte
  affichée, recherche par CP Lille retourne des résultats cohérents.
