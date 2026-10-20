# Oracle des loyers — règles pour Claude

- Répondre **toujours en français**.
- **Ports figés** (ne jamais changer) : backend Flask `5000`, frontend Vite `5174`, Airflow `8082→8080`. Registre global : `~/ProjetsWSL/PORTS.md`.
- **Pas de commit/push sans demande explicite.** Quand on commit : inclure `graphify-out/` dans le même commit, jamais à part.
- **`sudo` impossible** (pas de terminal) : donner la commande à l'utilisateur pour qu'il la lance avec `! sudo …`.
- **Python** : `backend/.venv/bin/python` (le shell est zsh, `python` n'existe pas).
- **Docker** : si `docker` échoue (intégration WSL), utiliser le skill `docker-wsl-fallback` ; vérifier d'abord que Docker Desktop tourne.
- **Lancer le pipeline** (ne pas redonner les commandes une par une) : scrapers `scripts/run_scrapers.sh [lille|lyon]` (toutes les villes sans argument), puis fusion→clean→modèle→carte via `docker exec oracle_airflow_scheduler airflow dags trigger oracle_annonces_pipeline`. Les villes viennent de `scripts/scraping_config.json`. `run_scrapers.sh` déclenche lui-même le DAG à la fin (plus de créneau 22h : il fusionnait des CSV à moitié scrapés) ; le DAG doit rester **non pausé**.
- **Parité Lille / Lyon** : toute amélioration (scrapers, géoloc, fusion, clean, map, modèle) appliquée à une ville l'est aussi à l'autre.
- **Scrapers** : ne garder que les annonces nouvellement scrapées (pas de re-traitement de l'historique).
- **Doublons et historique des prix (réglé, ne pas casser)** : le master = annonces vues au dernier run des sites actifs ; une seule annonce gardée par vrai doublon (`data_fusion.dedoublonner` : même clé prix/surface/type/CP + même texte, photo ou position à 30 m — jamais un `drop_duplicates` sur la seule clé) ; les annonces non revues partent dans `master_archive.csv` / `<site>_archive.csv` pour l'évolution des prix, et rien n'est archivé si le run est incomplet. Cf. commits 1faaeee, 7e97f5d, ORA-182.
- Une consigne donnée une fois reste valable : si elle est durable, l'ajouter ici.
