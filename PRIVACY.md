# Politique de rétention des données — Oracle des Loyers

Ce document liste, pour chaque type de donnée à caractère personnel traitée par l'application, ce qui est collecté, pourquoi, combien de temps, et où. Il fait référence en cas de question sur la conformité RGPD (application francophone).

> **Contexte** : ce projet est un portfolio/démonstrateur technique, sans société éditrice ni délégué à la protection des données (DPO) identifié. En cas de mise en production réelle avec de vrais utilisateurs, une section « responsable de traitement / contact » devrait être ajoutée avant tout déploiement public.

---

## Résumé

| Donnée | Collectée ? | Persistée ? | Durée de rétention |
|---|---|---|---|
| Messages du chatbot (`/api/chat`) | Oui, transitoirement | **Non** (voir ci-dessous) | Aucune (traités puis oubliés) |
| Adresse IP (rate limiting) | Oui | En mémoire uniquement | Fenêtre glissante (1h/1j), perdue au redémarrage du serveur |
| Cookies | Non | — | — |
| Compte utilisateur / authentification | Non (aucun compte n'existe) | — | — |
| `localStorage` / `sessionStorage` navigateur | Non | — | — |
| Outil d'analytics / tracking tiers | Non | — | — |
| Annonces immobilières scrapées | Oui (données publiques de tiers, pas des utilisateurs de l'app) | Oui (CSV versionnés) | Voir conformité CGU des sites sources (ORA-67/ORA-93, hors périmètre de ce document) |

---

## 1. Messages du chatbot Immotep (`POST /api/chat`)

- **Ce qui est envoyé** : le message tapé par l'utilisateur et un `context` optionnel (résumé du dernier scan de quartier), bornés à 2000 caractères chacun (voir [`API_CONTRACT.md`](./API_CONTRACT.md)).
- **Traitement** : le backend (`backend/services/chat_service.py`) construit un prompt et, si nécessaire, appelle l'API **Google Gemini** pour générer une réponse. Le message quitte donc l'infrastructure du projet pour être traité par Google — voir la [politique de confidentialité Google](https://policies.google.com/privacy) pour le traitement côté fournisseur.
- **Persistance côté projet** : **aucune**. Il n'existe plus de mécanisme de sauvegarde des conversations : `conversation_manager.py` (SQLite, table `conversations`) et le fichier `backend/data/conversations.db` qu'il alimentait ont été supprimés (voir ORA-36/ORA-40) car non branchés sur une route active. Un message traité par `/api/chat` n'est conservé nulle part côté serveur une fois la réponse renvoyée.
- **Côté client** : l'historique de la conversation vit uniquement dans l'état React de l'onglet ouvert (`ChatOracle.jsx`) — perdu à la fermeture ou au rechargement de la page, jamais écrit dans `localStorage`/`sessionStorage`/cookies.

> Note historique : `conversations.db` contenait des échanges de test de développement (janvier 2026). Le fichier a été retiré de l'arborescence courante du dépôt ; il reste néanmoins présent dans l'historique Git jusqu'à une éventuelle réécriture d'historique (action destructive volontairement hors périmètre de cette politique — à évaluer séparément si nécessaire).

**Si la persistance des conversations est un jour réactivée**, cette politique devra être mise à jour avant activation avec, a minima : une durée de rétention définie (ex. 30 jours), un mécanisme de purge automatique, et une base légale explicite (consentement ou intérêt légitime documenté).

## 2. Adresse IP (rate limiting)

- **Ce qui est traité** : l'adresse IP du client, utilisée comme clé par Flask-Limiter (`backend/app.py`) pour appliquer les limites de requêtes (`RATE_LIMIT_DEFAULT`, `RATE_LIMIT_CHAT`).
- **Persistance** : stockage **en mémoire uniquement** (`storage_uri="memory://"`), propre à chaque instance du serveur. Aucune écriture sur disque ni base de données. Les compteurs expirent naturellement à la fin de leur fenêtre glissante (ex. 1 heure) et sont intégralement perdus au redémarrage du serveur.
- **Base légale** : intérêt légitime (protection contre l'abus/déni de service et préservation du quota Gemini partagé).

## 3. Ce qui n'est PAS collecté

- Pas de cookies (aucun mécanisme de session, d'authentification ou de tracking par cookie).
- Pas de compte utilisateur (aucune inscription, aucun mot de passe, aucune donnée de profil).
- Pas de `localStorage`/`sessionStorage` côté frontend.
- Pas d'outil d'analytics ou de tracking tiers (Google Analytics, Sentry, etc.) intégré à ce jour.

## 4. Annonces immobilières scrapées

Les annonces collectées par les scrapers (`scripts/scraper_*.py`) contiennent des données publiques publiées par des tiers (agences, particuliers) sur des sites d'annonces — ce ne sont pas des données des *utilisateurs de cette application*. Leur collecte est encadrée séparément par la conformité aux CGU/robots.txt des sites sources (voir les tickets dédiés ORA-67 et ORA-93), qui est un sujet distinct de la présente politique de rétention des données utilisateur.

---

*Dernière mise à jour : voir l'historique Git de ce fichier. Toute évolution de la collecte de données (nouvelle fonctionnalité, réactivation d'une persistance de conversation, ajout d'un outil d'analytics...) doit s'accompagner d'une mise à jour de ce document avant déploiement.*
