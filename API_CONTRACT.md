# Contrat API — Oracle des Loyers

Ce document est la source de vérité du contrat des routes exposées par le backend Flask (`backend/app.py`). Toute route ajoutée, modifiée ou supprimée doit être répercutée ici.

Base URL locale : `http://localhost:5000/api` (voir `VITE_API_URL` dans [`.env.example`](./.env.example) pour la configuration en déploiement).

Toutes les routes `POST` acceptent un corps JSON (`Content-Type: application/json` ou `text/plain` contenant du JSON — le frontend envoie `text/plain` pour éviter un preflight CORS).

---

## `GET /api/listings`

Renvoie les annonces immobilières utilisées pour l'affichage sur la carte.

- **Payload d'entrée** : aucun.
- **Réponse `200`** : tableau JSON d'objets, un par annonce. Les valeurs manquantes (`NaN`) sont remplacées par une chaîne vide.

```json
[
  {
    "latitude": 45.75,
    "longitude": 4.85,
    "prix": 850,
    "type_local": "T2",
    "quartier": "Gerland"
  }
]
```

- **Codes d'erreur** : aucun cas d'erreur explicite. Si les données ne sont pas chargées, la route renvoie `200` avec un tableau vide `[]`.

Exemple :

```bash
curl http://localhost:5000/api/listings
```

---

## `POST /api/quartier-stats`

Calcule des statistiques réelles (prix moyen, prix/m², nombre de biens) à partir du CSV de données, pour un quartier et un type de bien donnés. **N'appelle pas le modèle de Machine Learning.**

- **Payload d'entrée** :

| Champ | Type | Obligatoire | Défaut | Description |
|---|---|---|---|---|
| `quartier` | string | oui | — | Recherche textuelle insensible à la casse dans la colonne `quartier` |
| `type_local` | string | non | `"Tout"` | Un de `"Tout"`, `"T1"`, `"T2"`, `"T3"`, `"T4+"` |

```json
{ "quartier": "Gerland", "type_local": "T2" }
```

- **Réponse `200`** (bien trouvé) :

```json
{
  "found": true,
  "quartier_detecte": "Gerland",
  "type_filtre": "T2",
  "count": 42,
  "prix_moyen": 780,
  "prix_m2_moyen": 16,
  "center": { "lat": 45.735, "lng": 4.831 }
}
```

- **Réponse `200`** (quartier trouvé mais aucun bien pour le type demandé) :

```json
{
  "found": true,
  "quartier_detecte": "Gerland",
  "count": 0,
  "prix_moyen": 0,
  "prix_m2_moyen": 0,
  "message": "Pas de T4+ trouvé dans ce secteur."
}
```

- **Réponse `200`** (aucun bien pour le quartier) :

```json
{ "found": false, "message": "Aucun bien trouvé pour le secteur 'xyz'" }
```

- **Codes d'erreur** :
  - `400` si `quartier` est vide : `{ "error": "Le nom du quartier est vide" }`
  - `500` si les données ne sont pas chargées ou en cas d'exception : `{ "error": "..." }`

Exemple :

```bash
curl -X POST http://localhost:5000/api/quartier-stats \
  -H "Content-Type: application/json" \
  -d '{"quartier":"Gerland","type_local":"T2"}'
```

---

## `POST /api/predict`

Prédiction de prix par Machine Learning (XGBoost).

> ⚠️ **État actuel : placeholder non fonctionnel.** La route ignore le payload d'entrée et renvoie toujours des valeurs à zéro (voir `backend/app.py`, route `predict`). Le modèle `price_predictor.pkl` est chargé au démarrage mais n'est pas encore utilisé par cette route. À ne pas considérer comme fiable côté frontend tant que ce n'est pas corrigé.

- **Payload d'entrée (attendu à terme)** : caractéristiques du bien (surface, quartier, type de bien, etc. — non encore stabilisé).
- **Réponse `200` (actuelle)** :

```json
{ "estimated_price": 0, "price_m2": 0, "confiance": "Non disponible" }
```

- **Codes d'erreur** : `500` en cas d'exception, `{ "error": "..." }`.

Exemple :

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## `POST /api/chat`

Route du chatbot "Immotep" : combine une réponse "groundée" sur les données réelles quand c'est possible, sinon un appel à Gemini avec contexte RAG borné.

- **Payload d'entrée** :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `message` | string | oui | Message utilisateur (tronqué côté serveur à 2000 caractères avant interpolation dans le prompt Gemini) |
| `context` | string | non | Contexte texte libre (ex. `"Quartier: Gerland, Type: T2, Prix Moyen: 780€"`) fourni par le frontend après un scan de quartier (tronqué à 2000 caractères) |

```json
{ "message": "Que vaut un T2 à Gerland ?", "context": "Quartier: Gerland, Type: T2" }
```

- **Réponse `200`** :

| Champ | Type | Description |
|---|---|---|
| `response` | string | Réponse textuelle affichée à l'utilisateur |
| `intent` | string | Intention détectée par le parseur interne (ou `"error"`) |
| `parsed` | object | Résultat brut du parsing de la requête |
| `recommendations` | array | Annonces recommandées en lien avec la requête, s'il y en a |
| `comparisons` | array | Annonces utilisées pour comparaison, s'il y en a |
| `map_focus` | object \| null | `{ "lat", "lng", "zoom" }` si la réponse doit recentrer la carte |

```json
{
  "response": "Gerland, ça tourne autour de 780€ pour un T2...",
  "intent": "comparison",
  "parsed": { "...": "..." },
  "recommendations": [],
  "comparisons": [],
  "map_focus": { "lat": 45.735, "lng": 4.831, "zoom": 15 }
}
```

- **Codes d'erreur** :
  - `400` si `message` est vide : `{ "response": "Silence... Tu n'as rien à dire ?" }`
  - `500` en cas d'exception non gérée : `{ "response": "Erreur interne côté serveur. Immotep revient dès que l'API répond correctement." }`
  - En cas d'absence de `GEMINI_API_KEY`, de timeout ou de quota Gemini dépassé, la route reste en `200` mais `intent` vaut `"error"` et `response` explique la cause.

Exemple :

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Que vaut un T2 à Gerland ?","context":"Quartier: Gerland, Type: T2"}'
```
