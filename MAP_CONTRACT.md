# Contrat postMessage — Carte (React ↔ HTML généré)

Ce document est la source de vérité des messages échangés via `postMessage` entre `frontend/src/components/MapComponent.jsx` (React, émetteur) et la carte Folium statique embarquée en iframe (`frontend/public/data/map_pings_lyon_calques.html`, générée par `backend/scripts/generate_map.py`, récepteur). Tout nouveau type de message doit être ajouté ici, dans `MapComponent.jsx` **et** dans `generate_map.build_bridge_message_script`.

L'iframe est servie depuis la même origine que l'application React (fichier statique de `frontend/public/data/`) : c'est un prérequis du contrat, pas un détail d'implémentation — c'est ce qui permet une vérification d'origine simple des deux côtés (voir Sécurité ci-dessous).

---

## Sécurité (ORA-125)

* **Émetteur** (`MapComponent.jsx`) : cible `window.location.origin` plutôt que `'*'` sur chaque `postMessage`, pour ne jamais livrer de commande carte à un autre document si l'iframe venait à naviguer ailleurs.
* **Récepteur** (`generate_map.build_bridge_message_script`) : ignore tout message dont `e.origin !== window.location.origin`, avant même de lire `e.data.type`.

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

### `TOGGLE_LAYER`

Active/désactive un calque Folium (`LayerControl`) depuis le panneau de contrôle React, sans dupliquer ce panneau dans la carte elle-même (masqué via CSS).

**Émis par** : `MapComponent.jsx`, sur toggle utilisateur ou au chargement initial de l'iframe (`handleIframeLoad`, pour resynchroniser l'état des calques React vers la carte).

```json
{ "type": "TOGGLE_LAYER", "name": "Immo T2", "show": true }
```

* `name` : libellé du calque tel qu'affiché dans le `LayerControl` Folium (`LAYER_MAPPING` dans `MapComponent.jsx` fait la correspondance clé interne → libellé réel).
* `show` : état cible (`true`/`false`).

**Traité par** : `build_bridge_message_script` → simule un clic sur la case à cocher Leaflet correspondante si son état diverge de `show` (Folium n'expose pas d'API JS directe pour piloter `LayerControl` par nom).

## Ajouter un nouveau type de message

1. Documenter le type ici (payload, émetteur, effet attendu).
2. Ajouter le `postMessage(...)` correspondant dans `MapComponent.jsx`, avec `window.location.origin` comme cible.
3. Ajouter la branche `else if (e.data.type === '...')` dans `generate_map.build_bridge_message_script`.
4. Ajouter un test dans `backend/tests/test_generate_map.py::BuildBridgeMessageScriptTest` (le script est une fonction pure testable, pas besoin de rendre la carte entière) et dans `frontend/src/components/MapComponent.test.jsx`.

Ne pas ajouter de nouveau calque carte (ORA-104, ORA-105, rafraîchissement live) sans suivre ces étapes : c'est précisément la dette que ce contrat corrige.
