# Contrat postMessage — Carte (React ↔ HTML généré)

Ce document est la source de vérité des messages échangés via `postMessage` entre `frontend/src/components/MapComponent.jsx` (React) et la carte Folium statique embarquée en iframe (`frontend/public/data/map_pings_lyon_calques.html`, générée par `backend/scripts/generate_map.py`). Le contrat est **bidirectionnel** : React → iframe (piloter la carte : `FLY_TO`, `FLY_TO_BOUNDS`, `TOGGLE_LAYER`) et iframe → React (notifier une interaction utilisateur sur la carte : `ANNONCE_CLICK`). Tout nouveau type de message doit être ajouté ici, dans `MapComponent.jsx` **et** dans `generate_map.build_bridge_message_script` (React → iframe) ou dans le popup HTML généré (iframe → React).

L'iframe est servie depuis la même origine que l'application React (fichier statique de `frontend/public/data/`) : c'est un prérequis du contrat, pas un détail d'implémentation — c'est ce qui permet une vérification d'origine simple des deux côtés (voir Sécurité ci-dessous).

---

## Sécurité (ORA-125)

* **React → iframe** : `MapComponent.jsx` cible `window.location.origin` plutôt que `'*'` sur chaque `postMessage` ; `generate_map.build_bridge_message_script` (iframe) ignore tout message dont `e.origin !== window.location.origin`, avant même de lire `e.data.type`.
* **iframe → React** : le popup HTML généré (`build_immo_popup_html`) cible `window.location.origin` sur son `postMessage` ; `MapComponent.jsx` valide de même `e.origin === window.location.origin` avant de traiter un message reçu (`ANNONCE_CLICK`).

Sans ces deux garde-fous, n'importe quelle page tierce capable d'obtenir une référence vers l'iframe (ou l'iframe elle-même si elle naviguait vers un contenu hostile) pourrait piloter la carte (recentrage, activation de calques) — surface d'attaque mineure ici, mais le principe reste : ne jamais faire confiance à un message sans vérifier son origine.

## Messages documentés

### `FLY_TO`

Recentre/zoome la carte Leaflet sur des coordonnées données, avec la transition animée native de Leaflet (`flyTo`).

**Émis par** : `MapComponent.jsx`, sur changement de la prop `center` (scan quartier, insight chat, résultats filtrés — ORA-105).

```json
{ "type": "FLY_TO", "lat": 45.75, "lng": 4.85, "zoom": 15 }
```

* `lat`, `lng` : coordonnées WGS84 (obligatoires).
* `zoom` : niveau de zoom Leaflet cible ; si absent ou falsy, le zoom courant de la carte est conservé (`zoom || <map>.getZoom()`).

**Traité par** : `build_bridge_message_script` → `<map>.flyTo([lat, lng], zoom)`.

### `FLY_TO_BOUNDS`

Recentre/zoome la carte sur une bounding-box (transition animée, `flyToBounds`), plutôt que sur un point unique.

**Émis par** : `MapComponent.jsx`, sur changement de la prop `bounds` — calculée par `App.jsx` à partir des quartiers des annonces actuellement affichées dans `AnnoncesList` (colonne Oracle desktop, ORA-105). `bounds` vaut `null` quand ces annonces n'ont aucune coordonnée exploitable ; dans ce cas `MapComponent.jsx` envoie un `FLY_TO` de repli vers le centre-ville plutôt qu'un `FLY_TO_BOUNDS` vide.

```json
{ "type": "FLY_TO_BOUNDS", "bounds": [[45.72, 4.80], [45.78, 4.87]] }
```

* `bounds` : `[[latMin, lngMin], [latMax, lngMax]]`, format attendu par `L.Map#flyToBounds`.

**Traité par** : `build_bridge_message_script` → `<map>.flyToBounds(bounds)`.

### `SET_TILE_URL`

Indique à la carte où aller chercher ses tuiles : le **proxy de tuiles du backend** (`GET /api/tiles/<z>/<x>/<y>.png`). La clé API CARTO reste côté serveur (`CARTO_API_KEY`), le navigateur ne la voit jamais — ni dans ce message, ni dans le HTML de la carte (versionné), ni dans les requêtes réseau. L'URL dépend du déploiement (`VITE_API_URL`), d'où un envoi au runtime plutôt qu'une écriture dans la carte générée ; avant ce message, la couche pointe sur un pixel transparent inline (aucune requête).

**Émis par** : `MapComponent.jsx`, à chaque chargement de l'iframe (`handleIframeLoad`).

```json
{ "type": "SET_TILE_URL", "url": "http://localhost:5000/api/tiles/{z}/{x}/{y}{r}.png" }
```

* `url` : modèle d'URL Leaflet ; doit commencer par `http://` ou `https://`, finir par `/{z}/{x}/{y}{r}.png` et ne contenir ni espace, ni guillemet, ni chevron, sinon le message est ignoré.

**Traité par** : `build_bridge_message_script` → `setUrl(url)` sur chaque `L.TileLayer` de la carte.

**Côté backend** : `services/tile_proxy.py` appelle `basemaps.cartocdn.com` avec la clé, met les tuiles en cache mémoire, limite le débit (`RATE_LIMIT_TILES`, 3000/h par défaut) et valide `z`/`x`/`y` ; sans clé configurée, CARTO renvoie un filigrane « API KEY REQUIRED » (dégradation visible, pas une panne).

### `TOGGLE_LAYER`

Active/désactive un calque Folium (`LayerControl`) depuis le panneau de contrôle React, sans dupliquer ce panneau dans la carte elle-même (masqué via CSS).

**Émis par** : `MapComponent.jsx`, sur toggle utilisateur ou au chargement initial de l'iframe (`handleIframeLoad`, pour resynchroniser l'état des calques React vers la carte).

```json
{ "type": "TOGGLE_LAYER", "name": "Immo T2", "show": true }
```

* `name` : libellé du calque tel qu'affiché dans le `LayerControl` Folium (`LAYER_MAPPING` dans `MapComponent.jsx` fait la correspondance clé interne → libellé réel — voir "Config partagée des calques" ci-dessous pour la source de vérité de cette correspondance).
* `show` : état cible (`true`/`false`).

**Traité par** : `build_bridge_message_script` → simule un clic sur la case à cocher Leaflet correspondante si son état diverge de `show` (Folium n'expose pas d'API JS directe pour piloter `LayerControl` par nom).

### `SET_FOCUS` / `CLEAR_FOCUS`

Matérialise le rayon des cavaliers choisi (300/500/1000m, `GET /api/cavaliers`) directement sur la carte, dans la vue "Calques" du rail : les pings de cavaliers **dans** le rayon restent pleins (opacité 1), ceux **hors** du rayon passent à 0,25 ; un cercle pointillé violet (rempli à 6 %) matérialise le rayon lui-même. `CLEAR_FOCUS` restaure l'opacité pleine de tous les cavaliers et retire le cercle.

**Émis par** : `MapComponent.jsx`, `SET_FOCUS` quand la vue "Calques" est active ET qu'un quartier a été scanné (`center` connu) ou que le rayon choisi change ; `CLEAR_FOCUS` dès que l'une des deux conditions cesse d'être vraie (changement de vue, ou aucun scan).

```json
{ "type": "SET_FOCUS", "lat": 45.750, "lng": 4.832, "radius_m": 500 }
```

```json
{ "type": "CLEAR_FOCUS" }
```

* `lat`, `lng` : centre du quartier scanné (`center` de `/api/quartier-stats`/`/api/cavaliers`).
* `radius_m` : rayon en mètres (300, 500 ou 1000 — cf. `GET /api/cavaliers`, API_CONTRACT.md).

**Traité par** : `build_bridge_message_script` →
* pour chaque entrée de `oracleCavalierMarkers` (déclaré par `build_cavalier_markers_script`, une entrée `{m, lat, lng, famille}` par marker cavalier posé sur la carte), calcule la distance au point de focus via `L.LatLng#distanceTo` (pas de haversine dupliqué côté JS) et appelle `marker.setOpacity(1)` ou `marker.setOpacity(0.25)` selon qu'elle est dans le rayon ou non ;
* dessine `L.circle([lat, lng], { radius: radius_m, color: '#A78BFA', dashArray: '6 6', fill: true, fillOpacity: 0.06 })`, en retirant l'éventuel cercle précédent (`window.__oracleFocusCircle`) avant d'ajouter le nouveau — un seul cercle affiché à la fois, jamais empilés à chaque changement de rayon ;
* `CLEAR_FOCUS` : `setOpacity(1)` sur chaque entrée de `oracleCavalierMarkers`, retire `window.__oracleFocusCircle`.

**Pings des cavaliers (`cavalier_icon_html`, `generate_map.py`)** : depuis ORA-130 (voir ci-dessous), chaque cavalier est un `folium.Marker`/`DivIcon` (plus un `CircleMarker`) dont la forme et la couleur viennent de `mapLayers.config.json` (`shape`/`uiColor`) — même source que le panneau React (`CavalierRow.jsx`) et sa légende carte. Une classe CSS par forme (`oracle-cav-circle`/`-diamond`/`-triangle`/`-square`, injectée une fois dans le `<style>` de la page) plutôt qu'un SVG inline par marker, pour ne pas alourdir le HTML généré (des centaines de cavaliers par carte).

## Config partagée des calques (ORA-130)

Avant ORA-130, la liste des calques (clé interne, libellé Folium/`TOGGLE_LAYER`, visibilité par défaut) était codée en dur à deux endroits qu'il fallait synchroniser à la main : `LAYER_MAPPING`/l'état initial `layers` dans `MapComponent.jsx` côté React, et les `folium.FeatureGroup`/`folium.GeoJson` (`name=`, `show=`) dans `generate_map.py` côté Python. Un calque oublié d'un côté ne cassait rien immédiatement (le contrat `TOGGLE_LAYER` échoue silencieusement si `name` ne correspond à aucun `<label>` Leaflet), ce qui rendait l'oubli facile à manquer en revue.

Les deux côtés lisent maintenant le même fichier JSON, source de vérité unique de la liste des calques :

**`frontend/src/config/mapLayers.config.json`**

```json
[
  {
    "key": "T2",
    "name": "Immo T2",
    "label": "Apparts T2",
    "group": "immobilier",
    "defaultVisible": true,
    "uiColor": "#22c55e"
  }
]
```

* `key` : identifiant interne côté React (état `layers`, appelé par `toggleLayer(key)`).
* `name` : libellé du calque Folium, celui qu'attend `TOGGLE_LAYER.name` (voir ci-dessus) et celui passé à `folium.FeatureGroup(name=...)`/`folium.GeoJson(name=...)` côté Python.
* `label` : texte affiché dans le panneau de contrôle React (`ToggleItem`).
* `group` : section du panneau React (`transports`, `contexte`, `immobilier`) — détermine où le calque apparaît, pas la structure des sections elle-même (toujours codée dans `MapComponent.jsx`).
* `defaultVisible` : état initial, des deux côtés — `layers` initial dans `MapComponent.jsx` **et** `show=` du `FeatureGroup`/`GeoJson` correspondant dans `generate_map.py`.
* `uiColor` : couleur du point/pastille affiché à côté du libellé dans le panneau React (`ToggleItem`). Pour les 4 calques cavaliers, cette même couleur pilote aussi l'icône du marker Folium (`generate_map.cavalier_icon_html`) — une seule source pour panneau/légende/carte, plus de dict `COLORS` séparé côté Python pour ces calques. Sans effet côté carte pour les autres calques (immo, métro, quartiers), dont le rendu vient d'ailleurs (`generate_map.COLORS['Immo']`, `METRO_COLORS`, style GeoJSON).
* `shape` (cavaliers uniquement) : forme de l'icône, une des 4 valeurs `circle`/`diamond`/`triangle`/`square` — lue à la fois par `generate_map.cavalier_icon_html` (classe CSS `oracle-cav-<shape>`) et par React (`CavalierShapeIcon.jsx`, mêmes noms de forme).

**Consommé par** :
* `MapComponent.jsx` : `import mapLayersConfig from '../config/mapLayers.config.json'` (import JS statique, bundlé par Vite — synchrone, pas de `fetch` réseau). `LAYER_MAPPING`, l'état initial `layers` et le rendu des `ToggleItem` du panneau en dérivent tous.
* `generate_map.py` : `load_layers_config()` (`json.load` sur `LAYERS_CONFIG_JSON = <repo>/frontend/src/config/mapLayers.config.json`, chemin résolu via `PROJECT_ROOT`, déjà utilisé pour écrire dans `frontend/public/data/`). Fichier requis : contrairement à `load_geojson_file` (calque optionnel), une config manquante ou invalide fait échouer la génération plutôt que produire une carte sans calques.

**Pourquoi un fichier dans `frontend/src/` plutôt qu'à la racine du repo** : le build Docker du frontend (`frontend/Dockerfile`) a pour contexte `./frontend` uniquement (voir `docker-compose.yml`) — un fichier à la racine du repo ne serait pas copié dans l'image et casserait `npm run build`. `generate_map.py`, lui, a toujours besoin d'un checkout complet du repo (il écrit déjà dans `frontend/public/data/` via `PROJECT_ROOT`), donc lire un fichier sous `frontend/src/` ne lui ajoute pas de contrainte nouvelle.

**Ajouter un calque** : ajouter une entrée dans `mapLayers.config.json` (les deux côtés la découvrent automatiquement — pas de section entièrement nouvelle du panneau nécessaire pour rester dans `transports`/`contexte`/`immobilier`) ; côté Python, il reste nécessaire d'écrire le code qui peuple ce `FeatureGroup`/`GeoJson` avec les données réelles du calque (`generate_map.py` ne peut pas deviner cette logique depuis la config).

### `ANNONCE_CLICK` (iframe → React, ORA-107)

Notifie React qu'un utilisateur a cliqué sur le lien "Voir l'annonce" d'un popup marker, pour tracker le clic exactement comme `AnnonceCard.jsx` (`api.logAnnonceClick`). Le HTML statique généré par `generate_map.py` n'a pas connaissance de l'URL du backend (pas de build Vite, donc pas de `VITE_API_URL`) : plutôt que de dupliquer cette configuration dans du Python généré, la carte délègue l'appel API à React via ce message.

**Émis par** : l'attribut `onclick` du lien généré par `build_immo_popup_html`, uniquement si l'id SQLite (`annonces.db`) de l'annonce a pu être résolu par URL (`annonces_store.get_annonce_by_url`) au moment de la génération de la carte — silencieux sinon (pas de régression bloquante si le store n'est pas encore synchronisé pour cette annonce).

```json
{ "type": "ANNONCE_CLICK", "id": 42 }
```

* `id` : id SQLite de l'annonce dans `annonces.db`.

**Traité par** : `MapComponent.jsx`, un listener `message` dédié (distinct du contrat React → iframe ci-dessus) qui appelle `api.logAnnonceClick(id)` — même fonction que `AnnonceCard.jsx`, donc même comportement (fire-and-forget, ne bloque jamais la navigation vers l'annonce qui s'ouvre via le `<a href>` natif du popup, indépendant de ce message).

## Rendu de la carte : légende, échelle, noms (ORA-165/166)

Conventions visuelles de la carte générée — sans nouveau type de message `postMessage` :

* **Annonces** : simples points verts (un `CircleMarker` par annonce, popup au clic, tooltip au survol). Une version « pastille prix colorée par écart au loyer médian » avec regroupement des annonces à même adresse a été livrée puis retirée : la carte reste volontairement en points.
* **Légende** (`build_legend_html`) : injectée au chargement de la page, ses lignes de calques portent `data-layer` = `name` Folium et sont grisées quand le calque est masqué (`overlayadd`/`overlayremove`) — donc suit `TOGGLE_LAYER` sans message dédié.
* **Échelle** métrique (`L.control.scale`) et classes `oracle-z13`/`oracle-z14` sur `<body>` : les labels de quartiers (capitales, centre des annonces du quartier) apparaissent dès le zoom 13, les noms de stations de métro dès le zoom 14.

Le script de légende s'exécute sur l'événement `load` : Folium rend le script d'initialisation de la carte **après** `</body>`, la variable `map_…` n'existe pas encore lors de l'exécution d'un bloc injecté avant.

## Ajouter un nouveau type de message

1. Documenter le type ici (payload, émetteur, effet attendu).
2. Ajouter le `postMessage(...)` correspondant dans `MapComponent.jsx`, avec `window.location.origin` comme cible.
3. Ajouter la branche `else if (e.data.type === '...')` dans `generate_map.build_bridge_message_script`.
4. Ajouter un test dans `backend/tests/test_generate_map.py::BuildBridgeMessageScriptTest` (le script est une fonction pure testable, pas besoin de rendre la carte entière) et dans `frontend/src/components/MapComponent.test.jsx`.

Ne pas ajouter de nouveau calque carte (ORA-104, ORA-105, rafraîchissement live) sans suivre ces étapes : c'est précisément la dette que ce contrat corrige.

## Ajouter un nouveau calque (pas un nouveau type de message)

Un calque (ex. Quartiers, ORA-104) est différent d'un type de message : il s'agit d'ajouter une entrée dans `frontend/src/config/mapLayers.config.json` (voir "Config partagée des calques" ci-dessus), pas d'étendre le contrat `postMessage` lui-même. Le `TOGGLE_LAYER` documenté plus haut reste inchangé — il continue de piloter n'importe quel calque par son `name`, qu'il vienne ou non de cette config.

1. Ajouter l'entrée dans `mapLayers.config.json` (`key`, `name`, `label`, `group`, `defaultVisible`, `uiColor`).
2. Écrire, dans `generate_map.py`, le code qui construit le `FeatureGroup`/`GeoJson` correspondant à partir des données réelles du calque (la config ne fournit que l'identité du calque, pas son contenu).
3. Vérifier dans `MapComponent.jsx` que la `group` choisie correspond à une section existante du panneau (`transports`, `contexte`, `immobilier`) ; sinon, ajouter la nouvelle section dans le JSX (ceci reste un changement React, la config ne pilote pas la structure des sections).
4. Ajouter un test dans `backend/tests/test_generate_map.py::LoadLayersConfigTest` et dans `frontend/src/components/MapComponent.test.jsx` si le comportement du nouveau calque le justifie (visibilité par défaut, libellé, etc.).
