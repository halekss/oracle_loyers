# Contrat API — Oracle des Loyers

Ce document est la source de vérité du contrat des routes exposées par le backend Flask (`backend/app.py`). Toute route ajoutée, modifiée ou supprimée doit être répercutée ici.

Base URL locale : `http://localhost:5000/api` (voir `VITE_API_URL` dans [`.env.example`](./.env.example) pour la configuration en déploiement).

Toutes les routes `POST` acceptent un corps JSON (`Content-Type: application/json` ou `text/plain` contenant du JSON — le frontend envoie `text/plain` pour éviter un preflight CORS).

**Rate limiting** : toutes les routes ci-dessous sont soumises à une limite globale par IP (`RATE_LIMIT_DEFAULT` dans [`.env.example`](./.env.example), défaut `200 per day, 50 per hour`). Un dépassement renvoie `429 { "error": "Trop de requêtes. Réessayez dans quelques instants." }`.

---

## Authentification (ORA-46)

**Décision : aucune authentification n'est mise en place sur les routes actuelles.**

Toutes les routes exposées par `backend/app.py` sont en lecture seule ou de simple consultation publique, à l'exception du tracking de clics ci-dessous — qui reste une écriture anonyme et non sensible (aucune donnée personnelle, pas d'action destructive) :

| Route | Nature |
|---|---|
| `GET /api/health` | Lecture — état du serveur et version du modèle |
| `GET /api/listings` | Lecture — annonces publiques affichées sur la carte |
| `GET /api/annonces` | Lecture — liste paginée des annonces stockées (aucune écriture) |
| `GET /api/annonces/<id>` | Lecture — détail d'une annonce stockée (aucune écriture) |
| `POST /api/annonces/<id>/click` | Écriture — journalisation anonyme d'un clic sortant (compteur de vues, ORA-91/92), aucune donnée personnelle |
| `POST /api/quartier-stats` | Lecture — agrégats calculés à la volée sur le CSV (aucune écriture) |
| `POST /api/quartier-historique` | Lecture — historique des snapshots (aucune écriture) |
| `POST /api/predict` | Lecture — inférence du modèle ML déjà chargé en mémoire (aucune écriture, aucun ré-entraînement) |
| `POST /api/chat` | Lecture — chatbot RAG groundé sur les données existantes (aucune écriture) |
| `POST /api/report/pdf` | Lecture — génère un PDF à partir d'un résultat déjà calculé, aucun recalcul ni écriture |

Aucune de ces routes ne supprime ou ne modifie de données, ne déclenche de ré-entraînement, ni n'expose de logs ou d'informations d'administration. Le ré-entraînement du modèle est piloté exclusivement par le DAG Airflow (hors périmètre HTTP, protégé par l'authentification Airflow elle-même via `AIRFLOW_ADMIN_USERNAME`/`AIRFLOW_ADMIN_PASSWORD`). Il n'existe aujourd'hui **aucune route d'administration ou de déclenchement manuel exposée via Flask**.

Ce projet est une démo portfolio publique sans notion d'utilisateur ni de compte : imposer une authentification (API-key ou JWT) sur des routes de consultation publiques ajouterait de la friction et de la complexité sans bénéfice de sécurité réel. La protection en place aujourd'hui (rate limiting par IP, CORS restreint à une liste d'origines de confiance) est jugée suffisante et proportionnée au risque.

**Cette décision doit être réévaluée dès qu'une route d'administration, de suppression de données, de déclenchement manuel de ré-entraînement, ou d'accès à des logs/informations sensibles serait ajoutée.** Dans ce cas, le mécanisme recommandé est une API-key simple (en-tête `X-API-Key`, comparée à une variable d'environnement type `ADMIN_API_KEY`), suffisant pour un projet de cette taille sans système d'utilisateurs.

---

## `GET /api/health`

Expose l'état du serveur et la version du modèle de prédiction actuellement chargé (ORA-31). Non soumis au rate limiting (`@limiter.exempt`).

- **Payload d'entrée** : aucun.
- **Réponse `200`** :

```json
{
  "status": "ok",
  "model_loaded": true,
  "model": {
    "model_version": "5af9e5a1be0c",
    "trained_at": "2026-08-03T13:21:36.516616+00:00",
    "metrics": { "mae": 167.03, "r2": 0.755 }
  }
}
```

`status` vaut `"degraded"` et `model.model_version`/`trained_at`/`metrics` sont `null` si le modèle ou ses métadonnées (`backend/models/price_predictor.pkl.meta.json`) sont indisponibles.

Exemple :

```bash
curl http://localhost:5000/api/health
```

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

## `GET /api/annonces`

Liste paginée des annonces stockées dans la table `annonces` (SQLite, `backend/data/annonces.db`, ORA-81), filtrable par ville et/ou quartier (ORA-84). Distinct de `GET /api/listings` : `annonces` est le store dédié aux futures fonctionnalités de consultation d'annonces (fiche détail, tracking de clics), alors que `/api/listings` sert uniquement l'affichage sur la carte à partir du CSV du pipeline ML.

- **Paramètres de requête** (tous optionnels) :

| Paramètre | Type | Défaut | Description |
|---|---|---|---|
| `ville` | string | — | Filtre exact sur la ville |
| `quartier` | string | — | Filtre exact sur le quartier |
| `page` | integer | `1` | Numéro de page (≥ 1) |
| `per_page` | integer | `20` | Taille de page (≥ 1, plafonné à 100) |

- **Réponse `200`** :

```json
{
  "items": [
    {
      "id": 1,
      "titre": "T2 Gerland",
      "prix": 850,
      "surface": 45,
      "ville": "Lyon",
      "quartier": "Gerland",
      "url": "https://example.com/annonce-1",
      "date_scraping": "2026-08-04T10:00:00+00:00",
      "images": []
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 1,
  "total_pages": 1
}
```

- **Réponse `400`** : `{ "error": "page et per_page doivent être des entiers" }` ou `{ "error": "page et per_page doivent être positifs" }`.

Exemple :

```bash
curl "http://localhost:5000/api/annonces?ville=Lyon&quartier=Gerland&page=1&per_page=20"
```

---

## `GET /api/annonces/<id>`

Détail d'une annonce par son id (ORA-85).

- **Payload d'entrée** : aucun (id dans le chemin).
- **Réponse `200`** : l'objet annonce (mêmes champs que dans `items` ci-dessus).
- **Réponse `404`** : `{ "error": "Annonce introuvable" }`.

Exemple :

```bash
curl http://localhost:5000/api/annonces/1
```

---

## `POST /api/annonces/<id>/click`

Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le nouveau total de vues (ORA-92). Chaque appel insère une ligne dans la table `clics` (`annonce_id`, `clicked_at`) — pas de déduplication : plusieurs clics du même visiteur comptent chacun.

### Décision ORA-86 — redirection directe vs modal intermédiaire

**Décision : redirection directe** (`window.open(url, '_blank', 'noopener,noreferrer')` au clic sur une `AnnonceCard`, sans modal de confirmation intermédiaire). Le clic déclenche cet appel `POST` en fire-and-forget (sans bloquer ni retarder la redirection) puis ouvre l'url source dans un nouvel onglet.

Justification :
- Cohérent avec la posture « agrégateur » déjà actée en ORA-94 (`LEGAL_DECISIONS.md`) : l'application ne fait que pointer vers l'annonce d'origine, elle n'en reproduit ni le contenu ni les visuels — une redirection franche renforce cette distinction (pas d'ambiguïté sur qui héberge quoi).
- Une modal de confirmation ("Vous quittez Oracle des Loyers...") n'apporte aucune protection réelle ici : aucune donnée utilisateur n'est engagée par le clic, et l'usage (comparateur de loyers) est celui d'un simple lien de renvoi, pas d'une transaction.
- Le tracking étant fire-and-forget et non bloquant, échouer à le journaliser (backend indisponible, réseau) ne doit jamais empêcher l'utilisateur d'atteindre l'annonce.

- **Payload d'entrée** : aucun (id dans le chemin).
- **Réponse `200`** :

```json
{ "logged": true, "views": 3 }
```

- **Réponse `404`** : `{ "error": "Annonce introuvable" }`.

Exemple :

```bash
curl -X POST http://localhost:5000/api/annonces/1/click
```

---

## `POST /api/quartier-stats`

Calcule des statistiques réelles (prix moyen, prix/m², nombre de biens) à partir du CSV de données, pour un quartier et un type de bien donnés. **N'appelle pas le modèle de Machine Learning.**

- **Payload d'entrée** :

| Champ | Type | Obligatoire | Défaut | Description |
|---|---|---|---|---|
| `quartier` | string | oui | — | Résolu vers le quartier connu le plus proche : insensible à la casse/accents/tirets, tolère les fautes de frappe (`backend/services/text_matching.py`, ORA-109/ORA-110) |
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
  "center": { "lat": 45.735, "lng": 4.831 },
  "facteurs": [
    { "categorie": "Vice", "phrase": "2 bar(s) à moins de 500m — parfait pour un verre, moins pour dormir." },
    { "categorie": "Gentrification", "phrase": "Une salle de sport à 338m — la gentrification muscle aussi les mollets." },
    { "categorie": "Nuisance", "phrase": "Une aire de jeux à 208m — cris d'enfants inclus, gratuitement." },
    { "categorie": "Superstition", "phrase": "Ni cimetière ni pompes funèbres à moins de 500m — rien à signaler côté au-delà." }
  ],
  "comparables": [
    { "type_local": "T2", "prix": 780, "surface": 45 },
    { "type_local": "T2", "prix": 760, "surface": 42 },
    { "type_local": "T2", "prix": 810, "surface": 48 }
  ]
}
```

`facteurs` (ORA-73) : résumé des 4 "Cavaliers" pour le quartier détecté, sous forme de phrases concrètes (pas un score abstrait) générées par `backend/services/cavaliers_factors.py` à partir des colonnes `dist_*`/`nb_*_500m` de `master_immo_final.csv`. Utilisé par le frontend pour l'export PDF de l'estimation (bouton "Exporter en PDF", `POST /api/report/pdf`, ORA-121).

`comparables` (ORA-122/ORA-128) : jusqu'à 3 biens réels du même quartier/type, les plus proches du prix moyen (`prix_moyen`) — pas un échantillon aléatoire. Vide si aucun bien ne correspond au filtre type demandé.

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

- **Réponse `200`** (aucun quartier connu n'est raisonnablement proche) :

```json
{ "found": false, "ambiguous": false, "suggestions": [], "message": "Aucun bien trouvé pour le secteur 'xyz'" }
```

- **Réponse `200`** (saisie ambiguë — plusieurs quartiers assez proches, ORA-111) :

```json
{
  "found": false,
  "ambiguous": true,
  "suggestions": ["Croix-Rousse Plateau", "Pentes Croix-Rousse"],
  "message": "Quartier ambigu pour 'croiss' — vouliez-vous dire : Croix-Rousse Plateau, Pentes Croix-Rousse ?"
}
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

## `POST /api/quartier-historique`

Évolution du prix moyen/m² pour un quartier à travers les snapshots de données enregistrés (ORA-72, voir README section "Versioning des snapshots de données"). Même recherche textuelle insensible à la casse que `/api/quartier-stats`.

- **Payload d'entrée** : identique à `/api/quartier-stats` (`quartier` obligatoire, `type_local` optionnel, défaut `"Tout"`).

- **Réponse `200`** (assez d'historique) :

```json
{
  "found": true,
  "status": "ok",
  "quartier": "Gerland",
  "historique": [
    { "date": "2026-01-01T00:00:00+00:00", "prix_m2_moyen": 20, "count": 42 },
    { "date": "2026-01-08T00:00:00+00:00", "prix_m2_moyen": 21, "count": 45 }
  ]
}
```

- **Réponse `200`** (pas assez d'historique — un seul snapshot enregistré à ce jour, état actuel du projet) :

```json
{
  "found": true,
  "status": "insufficient_history",
  "message": "Pas encore assez d'historique de données pour observer une tendance (un seul snapshot enregistré à ce jour).",
  "historique": []
}
```

- **Codes d'erreur** : `400` si `quartier` est vide, comme `/api/quartier-stats`.

Exemple :

```bash
curl -X POST http://localhost:5000/api/quartier-historique \
  -H "Content-Type: application/json" \
  -d '{"quartier":"Gerland","type_local":"T2"}'
```

---

## `POST /api/predict`

Prédiction de prix par Machine Learning (modèle XGBoost `backend/models/price_predictor.pkl`, chargé au démarrage). Construit le vecteur de 45 features attendu par le modèle à partir du payload (distances aux points d'intérêt calculées à la volée depuis `cavaliers_lyon.csv`, coordonnées/code postal déduits du quartier si absents du payload).

- **Payload d'entrée** :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `surface` | number | oui | Surface en m², doit être strictement positive |
| `quartier` | string | oui | Recherche textuelle souple sur les quartiers connus (ex. `"Gerland"`) |
| `type_local` | string | oui | Un de `"Studio/T1"`, `"T2"`, `"T3"`, `"Grand (T4+)"` (alias acceptés : `"T1"`, `"T4"`, `"T4+"`, `"T5"`, `"Maison"`, `"Studio"`) |
| `type` | string | non | Type de bien brut : `"Appartement"` (défaut), `"Maison"` ou `"Studio"` |
| `latitude`, `longitude` | number | non | Si absents, moyenne des annonces réelles du quartier détecté |
| `code_postal` | number | non | Si absent, code postal le plus fréquent du quartier détecté |

```json
{ "surface": 45, "quartier": "Gerland", "type_local": "T2" }
```

- **Réponse `200`** :

```json
{
  "estimated_price": 962,
  "price_m2": 21,
  "confiance": "Moyenne",
  "comparables": 14,
  "quartier_detecte": "Gerland",
  "type_local_detecte": "T2"
}
```

`confiance` (`"Faible"` / `"Moyenne"` / `"Élevée"`) est dérivée du nombre réel de `comparables` (annonces du même quartier et type dans `master_immo_final.csv`) : `< 5` → Faible, `< 20` → Moyenne, `>= 20` → Élevée.

- **Codes d'erreur** :
  - `400` si le payload est invalide (`surface`/`quartier`/`type_local` manquant ou incorrect) : `{ "error": "Payload invalide", "details": ["..."] }`
  - `500` si le modèle n'est pas chargé, si les données de référence sont indisponibles, ou en cas d'exception pendant la prédiction : `{ "error": "..." }`

Exemple :

```bash
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"surface":45,"quartier":"Gerland","type_local":"T2"}'
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
  - `429` si la limite dédiée à cette route est dépassée (`RATE_LIMIT_CHAT`, défaut `15 per hour` par IP — plus stricte que la limite globale, pour protéger le quota Gemini) : `{ "error": "Trop de requêtes. Réessayez dans quelques instants." }`
  - `500` en cas d'exception non gérée : `{ "response": "Erreur interne côté serveur. Immotep revient dès que l'API répond correctement." }`
  - En cas d'absence de `GEMINI_API_KEY`, de timeout ou de quota Gemini dépassé, la route reste en `200` mais `intent` vaut `"error"` et `response` explique la cause.

Exemple :

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Que vaut un T2 à Gerland ?","context":"Quartier: Gerland, Type: T2"}'
```

---

## `POST /api/report/pdf`

Génère le rapport PDF d'une estimation (ORA-121), via WeasyPrint côté serveur — remplace `window.print()`. Ne recalcule rien : reprend tel quel le résultat déjà affiché par `ResultCard.jsx`.

- **Payload d'entrée** :

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `quartier` | string | oui | — |
| `estimated_price` | number | oui | — |
| `prix_m2` | number | non | — |
| `confiance` | string | non | `"Faible"` \| `"Moyenne"` \| `"Élevée"` |
| `count` | integer | non | Nombre de biens comparés |
| `type_local` | string | non | — |
| `facteurs` | array | non | `[{ "categorie", "phrase" }, ...]` (Les 4 Cavaliers, cf. `/api/quartier-stats`) |

```json
{
  "quartier": "Gerland",
  "estimated_price": 950,
  "prix_m2": 21,
  "confiance": "Élevée",
  "facteurs": [{ "categorie": "Vice", "phrase": "2 bar(s) à moins de 500m..." }]
}
```

- **Réponse `200`** : fichier `application/pdf`, `Content-Disposition: attachment; filename="rapport-oracle-<quartier>.pdf"`.
- **Codes d'erreur** :
  - `400` si `quartier` est vide ou `estimated_price` absent : `{ "error": "Payload invalide" }`
  - `500` si WeasyPrint échoue (ex. dépendances système manquantes, cf. Dockerfile) : `{ "error": "Erreur lors de la génération du PDF" }`

Exemple :

```bash
curl -X POST http://localhost:5000/api/report/pdf \
  -H "Content-Type: application/json" \
  -d '{"quartier":"Gerland","estimated_price":950,"prix_m2":21}' \
  --output rapport.pdf
```
