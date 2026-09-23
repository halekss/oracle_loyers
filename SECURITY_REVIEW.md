# Revue de sécurité applicative (OWASP Top 10) — ORA-69

Date : 2026-08-03
Périmètre : backend Flask (`backend/`), configuration Docker/Airflow
(`docker-compose.yml`, `Airflow/`), CI/CD (`.github/workflows/`), frontend
React (`frontend/`).

Contexte : cette revue intervient **après** l'application des correctifs
CORS (ORA-42), rate limiting (ORA-41/45), secrets Airflow (ORA-43), validation
des payloads (ORA-44) et bornage du contexte de prompt (ORA-38). L'objectif
est de vérifier qu'aucun autre point n'a été manqué avant mise en production
réelle, via une checklist OWASP Top 10 (2021) légère.

Ce document ne couvre pas la question de l'authentification applicative,
traitée séparément par le ticket ORA-46 (voir constat dédié ci-dessous).

## Checklist OWASP Top 10 (2021)

### A01 — Broken Access Control : **Risque accepté (renvoi ORA-46)**

Aucune route (`/api/health`, `/api/listings`, `/api/quartier-stats`,
`/api/quartier-historique`, `/api/predict`, `/api/chat` dans `backend/app.py`)
n'exige d'authentification ni d'autorisation. Toutes les routes sont
publiques et en lecture (aucune mutation de données côté serveur, pas
d'administration exposée). C'est un choix assumé pour une démo portfolio
publique — voir ticket **ORA-46**, traité en parallèle, qui statue sur la
stratégie d'authentification éventuelle. Aucune action prise ici : ne pas
dupliquer ce travail.

Le contrôle d'accès *système* (Airflow webserver, base Postgres interne) est
en revanche correctement cloisonné : `airflow-db` n'expose aucun port vers
l'hôte dans `docker-compose.yml`, et Airflow exige des identifiants admin
définis via `.env` (ORA-43, pas de valeur par défaut faible committée).

### A02 — Cryptographic Failures : **OK**

- Aucun secret en dur dans le code (vérifié par recherche sur
  `GEMINI_API_KEY`, `SECRET_KEY`, `password` dans `backend/`, `scripts/`,
  `Airflow/`) : uniquement des valeurs factices dans les tests
  (`backend/tests/test_chat_service.py`).
- `.env` est exclu de `.gitignore`, `.env.example` ne contient que des
  placeholders et rappelle explicitement de ne jamais committer de vrais
  secrets.
- L'app ne gère ni mots de passe, ni sessions, ni cookies : pas de stockage
  de données d'authentification à protéger côté backend.
- Le trafic HTTPS est délégué à la plateforme d'hébergement (Render) ; rien
  à faire côté code applicatif (pas de terminaison TLS custom).

### A03 — Injection : **OK**

- Pas de SQL (le projet n'utilise aucune base relationnelle côté données
  applicatives — le seul SGBD, Postgres pour Airflow, n'est piloté que par
  Airflow lui-même, sans requête utilisateur).
- Les payloads JSON sont validés par schéma Pydantic
  (`backend/schemas.py` : `ChatRequestSchema`, `QuartierStatsRequestSchema`,
  `PredictRequestSchema`) avant tout traitement métier (ORA-44).
- Recherche de quartier/type (`app.py`, `services/price_history.py`) utilise
  `str.contains` sur des colonnes pandas avec l'entrée utilisateur en texte
  littéral (pas de regex utilisateur interprétée telle quelle côté
  `ChatService`, qui échappe via `re.escape` avant `str.contains` —
  `services/chat_service.py` lignes 266, 332).
- Pas d'`eval`, `exec`, `pickle.loads` sur données non fiables, ni
  `os.system`/`subprocess` avec entrée utilisateur (recherche exhaustive sans
  résultat dans `backend/`).
- Le prompt envoyé à Gemini (`services/chat_service.py::_build_prompt`)
  interpole `message`/`context` fournis par le client. C'est une injection de
  prompt potentielle (le modèle IA peut être influencé), mais bornée : taille
  plafonnée (`MAX_USER_MESSAGE_LENGTH`/`MAX_CONTEXT_LENGTH` = 2000
  caractères, ORA-38), pas d'accès outil/exécution côté serveur depuis la
  réponse du modèle, et impact limité au texte de réponse chatbot affiché
  (pas de RCE, pas d'accès aux données d'autres utilisateurs). Accepté tel
  quel pour une démo, déjà traité par ORA-38.

### A04 — Insecure Design : **OK**

- Séparation nette scan de quartier (statistiques réelles CSV) vs prédiction
  ML (`/api/quartier-stats` ne fait explicitement pas appel au modèle,
  documenté dans le docstring de la route).
- Le chatbot a une réponse "groundée" (calculs locaux déterministes) qui
  prend le pas sur l'appel Gemini quand c'est possible
  (`get_chat_result`), réduisant la dépendance à un tiers pour les cas
  fréquents (comparaison, recommandation).
- Limites de taux différenciées (`/api/chat` plus strict que le défaut
  global) pour protéger un quota tiers partagé (ORA-41/45).
- Erreurs applicatives renvoient des messages génériques côté chat/health,
  mais **certaines routes renvoient `str(e)` brut** au client
  (`/api/quartier-stats` ligne ~345, `/api/predict` ligne ~487). Voir
  constat priorisé ci-dessous (A05).

### A05 — Security Misconfiguration : **À corriger (partiellement corrigé ici)**

Constats :
1. **En-têtes de sécurité HTTP absents** — aucun `X-Content-Type-Options`,
   `X-Frame-Options`, ni `Referrer-Policy` n'était défini sur les réponses
   Flask. **Corrigé dans ce commit** : ajout d'un hook `after_request` dans
   `backend/app.py` définissant ces trois en-têtes (pas de `Content-Security-
   Policy` ajoutée côté API, l'app ne servant que du JSON, jamais de
   HTML/JS — une CSP a plus de sens côté SPA frontend si besoin, hors
   périmètre de ce correctif trivial).
2. **Messages d'erreur bruts renvoyés au client** dans `/api/quartier-stats`
   (`return jsonify({"error": str(e)}), 500`) et `/api/predict`
   (`f"Erreur lors de la prédiction : {e}"`). Risque faible ici (pas de
   stack trace complète, exceptions pandas/sklearn généralement peu
   sensibles), mais c'est une fuite d'information potentielle (chemins,
   noms de colonnes internes). Non corrigé dans ce commit (changement de
   comportement des réponses d'erreur, à traiter consciemment plutôt qu'en
   correctif "trivial"). Voir priorisation.
3. `FLASK_DEBUG` est bien désactivé par défaut et documenté comme "à ne
   jamais activer en prod" dans `.env.example` — OK.
4. `backend/requirements.txt` et `frontend/package.json` **ne pinnent pas
   des versions exactes** (pas de `==`, seulement des ranges `^` côté
   frontend, verrouillé par `package-lock.json` + `npm ci` en CI ; côté
   backend, aucune version du tout). Voir A06.
5. Le Dockerfile Airflow bascule bien en utilisateur non-root (`USER
   airflow`) après l'installation système — OK. Le Dockerfile backend ne
   déclare pas de `USER` non-root explicite (tourne en root dans le
   conteneur) : risque faible en pratique (pas de secrets de build, image
   éphémère), mais s'écarte du principe de moindre privilège. Voir
   priorisation.

### A06 — Vulnerable and Outdated Components : **À corriger (mineur)**

- Aucun outil de scan de dépendances (pas de Dependabot, pas de `pip-audit`
  ni `npm audit` dans `.github/workflows/ci.yml`).
- `backend/requirements.txt` liste des paquets **sans version épinglée**
  (`pandas`, `Flask`, `google-genai`, etc.) : un correctif de sécurité amont
  ou une régression peuvent être tirés silencieusement au prochain build,
  sans visibilité ni reproductibilité garantie.
- `scripts/requirements.txt` est, à l'inverse, intégralement pinné (bonne
  pratique déjà en place là où c'est fait).
- Le frontend utilise `npm ci` en CI (respecte `package-lock.json`) — la
  reproductibilité est meilleure côté frontend que côté backend.

### A07 — Identification and Authentication Failures : **Risque accepté (renvoi ORA-46)**

Pas de compte utilisateur, pas de session, pas de mot de passe applicatif
côté API publique — cohérent avec l'absence totale d'authentification
constatée en A01. Le seul système avec authentification (Airflow webserver)
exige des identifiants forts définis via variables d'environnement
obligatoires (ORA-43), sans défaut faible committé — OK sur ce périmètre
restreint.

### A08 — Software and Data Integrity Failures : **OK**

- Le pipeline CD (`deploy` dans `ci.yml`) ne se déclenche que si tous les
  jobs de test (`backend`, `scrapers`, `frontend`, `e2e`) réussissent au
  préalable (`needs:` + condition explicite `success()`), empêchant un
  déploiement sur du code non validé.
- Les modèles ML (`price_predictor_<ville>.pkl`, un par ville depuis
  ORA-154) sont versionnés dans le dépôt avec un pipeline d'entraînement
  déterministe documenté — pas de désérialisation d'un artefact modèle
  provenant d'une source non fiable/externe à chaque démarrage.
- Pas de mécanisme d'auto-update / téléchargement de code exécutable à
  l'exécution.

### A09 — Security Logging and Monitoring Failures : **Risque accepté**

- Les erreurs sont journalisées via `print(...)` côté serveur (`app.py`,
  `chat_service.py`) : suffisant pour une démo avec logs consultés
  manuellement (Render), mais pas de corrélation structurée, pas d'alerting
  automatique sur pics d'erreurs/tentatives suspectes.
- Le monitoring de dérive modèle (`model-drift-monitor.yml`, ORA-33) et le
  canari de sélecteurs scraper (`scraper-selector-canary.yml`, ORA-21)
  couvrent la supervision *fonctionnelle*, pas la sécurité applicative à
  proprement parler. Acceptable pour le périmètre et l'échelle du projet
  (portfolio, trafic faible) ; à revisiter si le trafic ou la surface
  d'attaque augmentent.

### A10 — Server-Side Request Forgery (SSRF) : **OK**

- Aucune route backend ne construit une URL à partir d'une entrée
  utilisateur pour effectuer une requête sortante. Les seuls appels HTTP
  sortants identifiés sont : (1) les scrapers (`scripts/scraper_*.py`) vers
  des sites immobiliers fixes, exécutés hors requête utilisateur (pipeline
  Airflow planifié), et (2) l'appel au SDK Gemini
  (`services/chat_service.py::_generate_with_gemini`) vers une API tierce
  fixe, avec un prompt textuel (pas une URL) comme entrée variable.
- `api_overpass.py` interroge l'API Overpass (OSM) avec une requête
  construite côté pipeline, sans entrée utilisateur externe au moment de
  l'exécution.

## Constat complémentaire : absence d'authentification (hors périmètre)

Comme demandé, ce point est noté ici pour mémoire mais **non traité** par
cette revue : l'absence totale d'authentification sur les routes API est un
choix produit assumé pour une démonstration portfolio publique. La décision
(rester sans authentification, ou introduire un mécanisme léger — clé API,
authentification basique sur les routes sensibles, etc.) relève du ticket
**ORA-46**, traité en parallèle. Ne pas dupliquer ce travail ici.

## Correctif appliqué dans ce commit

- Ajout d'en-têtes de sécurité HTTP de base (`X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy`) via un hook `after_request` dans
  `backend/app.py`. Changement sans impact fonctionnel (aucune route, aucun
  code de statut, aucun corps de réponse modifié) ; validé par la suite de
  tests existante (`backend/tests/`, 131 tests, tous passants).

## Priorisation des correctifs restants

| # | Constat | Sévérité | Fichiers concernés | Action recommandée |
|---|---|---|---|---|
| 1 | Pas de scan automatisé de vulnérabilités des dépendances (pas de Dependabot / `pip-audit` / `npm audit` en CI) | Moyenne | `.github/workflows/ci.yml` | Ajouter Dependabot (config GitHub native) et/ou une étape `pip-audit`/`npm audit --audit-level=high` en CI |
| 2 | `backend/requirements.txt` sans versions épinglées | Moyenne | `backend/requirements.txt` | Générer un lock (`pip freeze` / `pip-compile`) pour builds reproductibles et audités |
| 3 | Messages d'erreur bruts (`str(e)`) renvoyés au client sur `/api/quartier-stats` et `/api/predict` | Faible | `backend/app.py` | Remplacer par un message générique côté client + log détaillé côté serveur uniquement (changement de comportement des réponses d'erreur, à traiter volontairement, pas en correctif trivial) |
| 4 | Conteneur backend tourne en root (pas de `USER` non-root dans `backend/Dockerfile`) | Faible | `backend/Dockerfile` | Ajouter un utilisateur applicatif non-root, à valider avec les volumes montés (`./backend:/app`) qui pourraient nécessiter un ajustement de permissions |
| 5 | Logging non structuré (`print`), pas d'alerting sécurité | Faible / accepté | `backend/app.py`, `services/chat_service.py` | Pas d'action requise à l'échelle actuelle du projet ; envisager un logger structuré si le trafic augmente |
| 6 | Absence totale d'authentification sur les routes API | Décision produit | `backend/app.py` | Hors périmètre ORA-69 : décision et implémentation portées par **ORA-46** |

Aucun constat de sévérité "Élevée"/bloquante n'a été identifié : les points
1 à 5 sont des améliorations de posture de sécurité, pas des vulnérabilités
exploitables activement identifiées dans le code actuel. Le point 6 est une
décision produit déjà suivie par un autre ticket.

## Verdict global

L'application est **globalement saine** du point de vue OWASP Top 10 pour
son contexte (démo portfolio publique, sans données personnelles sensibles,
sans compte utilisateur). CORS, rate limiting, secrets et validation de
schéma — déjà traités en amont — couvrent les risques les plus significatifs.
Les constats restants (dépendances non épinglées/non scannées, messages
d'erreur un peu trop verbeux, conteneur backend en root) sont des
améliorations de durcissement à faible risque, sans exploitabilité
démontrée, et peuvent être traités dans des tickets de suivi dédiés sans
bloquer une mise en production.
