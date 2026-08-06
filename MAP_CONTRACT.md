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

### `TOGGLE_LAYER`

Active/désactive un calque Folium (`LayerControl`) depuis le panneau de contrôle React, sans dupliquer ce panneau dans la carte elle-même (masqué via CSS).

**Émis par** : `MapComponent.jsx`, sur toggle utilisateur ou au chargement initial de l'iframe (`handleIframeLoad`, pour resynchroniser l'état des calques React vers la carte).

```json
{ "type": "TOGGLE_LAYER", "name": "Immo T2", "show": true }
```

* `name` : libellé du calque tel qu'affiché dans le `LayerControl` Folium (`LAYER_MAPPING` dans `MapComponent.jsx` fait la correspondance clé interne → libellé réel).
* `show` : état cible (`true`/`false`).

**Traité par** : `build_bridge_message_script` → simule un clic sur la case à cocher Leaflet correspondante si son état diverge de `show` (Folium n'expose pas d'API JS directe pour piloter `LayerControl` par nom).

### `ANNONCE_CLICK` (iframe → React, ORA-107)

Notifie React qu'un utilisateur a cliqué sur le lien "Voir l'annonce" d'un popup marker, pour tracker le clic exactement comme `AnnonceCard.jsx` (`api.logAnnonceClick`). Le HTML statique généré par `generate_map.py` n'a pas connaissance de l'URL du backend (pas de build Vite, donc pas de `VITE_API_URL`) : plutôt que de dupliquer cette configuration dans du Python généré, la carte délègue l'appel API à React via ce message.

**Émis par** : l'attribut `onclick` du lien généré par `build_immo_popup_html`, uniquement si l'id SQLite (`annonces.db`) de l'annonce a pu être résolu par URL (`annonces_store.get_annonce_by_url`) au moment de la génération de la carte — silencieux sinon (pas de régression bloquante si le store n'est pas encore synchronisé pour cette annonce).

```json
{ "type": "ANNONCE_CLICK", "id": 42 }
```

* `id` : id SQLite de l'annonce dans `annonces.db`.

**Traité par** : `MapComponent.jsx`, un listener `message` dédié (distinct du contrat React → iframe ci-dessus) qui appelle `api.logAnnonceClick(id)` — même fonction que `AnnonceCard.jsx`, donc même comportement (fire-and-forget, ne bloque jamais la navigation vers l'annonce qui s'ouvre via le `<a href>` natif du popup, indépendant de ce message).

## Ajouter un nouveau type de message

1. Documenter le type ici (payload, émetteur, effet attendu).
2. Ajouter le `postMessage(...)` correspondant dans `MapComponent.jsx`, avec `window.location.origin` comme cible.
3. Ajouter la branche `else if (e.data.type === '...')` dans `generate_map.build_bridge_message_script`.
4. Ajouter un test dans `backend/tests/test_generate_map.py::BuildBridgeMessageScriptTest` (le script est une fonction pure testable, pas besoin de rendre la carte entière) et dans `frontend/src/components/MapComponent.test.jsx`.

Ne pas ajouter de nouveau calque carte (ORA-104, ORA-105, rafraîchissement live) sans suivre ces étapes : c'est précisément la dette que ce contrat corrige.
