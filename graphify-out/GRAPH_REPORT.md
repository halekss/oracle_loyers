# Graph Report - oracle_loyers  (2026-09-25)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1977 nodes · 3117 edges · 183 communities (118 shown, 65 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 165 edges (avg confidence: 0.78)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d085df84`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_scraper_extraction_fixtures.py
- monitor_drift.py
- train_model.py
- detail_cavaliers
- app.py
- request_with_retry
- AnnoncesStoreTest
- clean_immo.py
- App.jsx
- ChatService
- build_report_html
- CheckUrlStatusBrowserTest
- get_connection
- build_feature_row
- resolve_quartier_filter
- generate_map.py
- _geocode
- test_scraper_utils.py
- test_playwright_selectors.py
- ChatRequestSchema
- localisation_texte.py
- recheck_dead_annonces.py
- AnnonceCard.jsx
- merge_cavaliers
- run_fusion
- prepare_new_city.py
- annonces_store.py
- data_fusion.py
- LoggingConfigTest
- GetTileTest
- scraper_paruvendu.py
- useAnnonceDetail.js
- scraper_seloger.py
- step_flag_expired
- AdresseDuBienTest
- normalize_text
- QuartierStatsRouteTest
- AnnonceDetailModal.jsx
- devDependencies
- API Contract (Oracle des Loyers)
- ChatServiceTest
- RowsToVerifyTest
- pick_user_agent
- scraper_vizzit.py
- AnnoncesRoutesTest
- ModelRegressionTest
- scraper_pap.py
- clean_immo.py
- DataLoader
- PredictRouteTest
- StepQuartiersTest
- SearchForm.jsx
- scraper_utils.py
- EnrichDescriptionsTest
- GeocodageTest
- RateLimitBehaviorTest
- dependencies
- ChatOracle.jsx
- archive_stale_rows
- extract_postal_code
- resolve_seloger_lieu
- ErrorBoundary
- match_quartier
- test_chat_service.py
- File Structure
- Scraper extraction fixture tests (ORA-19)
- verify_annonces_async.py (aiohttp HTTP verifier)
- Map postMessage Contract
- get_map_tile
- decide_promotion
- MergeAllVillesTest
- test_clean_immo_steps.py
- test_generate_map.py
- File Structure
- scraper_orpi.py
- PruneDeadMapListingsTest
- extract_type
- ReportPdfRouteTest
- BuildBridgeMessageScriptTest
- BuildImmoPopupHtmlTest
- VerifyAnnoncesTest
- PanelNav.jsx
- api.js
- computeHomeStats
- computeQuartierOptions
- train_model.py (XGBoost per city)
- generate_map.py (Folium static map)
- QuartierStatsRequestSchema
- clean_price_integer
- clean_surface
- resolve_quartier
- LoadLayersConfigTest
- CheckUrlStatusTest
- scripts
- GetChromeDriverOptionsTest
- PruneDeadAnnoncesTest
- test_rollback_model.py
- RuntimeConfigTest
- package.json
- load_site_config
- format_description
- fetch_lyon_arrondissements.py
- geocodage.py
- HealthRouteTest
- GeocodingJitterTest
- ResolveLilleQuartierHintTest
- StepFeaturesTest
- StepPruneExpiredTest
- WriteMapMetadataTest
- SanitizeListingUrlTest
- LilleQuartiersGeojsonTest
- LooksLikeSoft404Test
- Airflow DAG oracle_annonces_pipeline (weekly)
- QuartierAmbigu.jsx
- POST /api/quartier-stats
- fetch_lille_quartiers.py
- ChatRouteTest
- QuartierHistoriqueRouteTest
- BuildShapesFromCavaliersTest
- MatchQuartierLilleTest
- StepSyncAnnoncesStoreTest
- BuildImmoTooltipHtmlTest
- ComputeLayerCountsTest
- LoadGeojsonFileTest
- CheckUrlStatusAsyncTest
- Tech architecture (React, Flask, XGBoost, Gemini, Docker)
- CavaliersDetail.jsx
- HomeOverview.jsx
- get_db_connection
- is_context_safe
- ListingsRouteTest
- BuildTitreTest
- ResolveVillePathsTest
- vite.config.js
- oracle_annonces_dag.py
- oracle_cavaliers_dag.py
- oracle_cleanup_dag.py
- autoprefixer
- sentry-sdk[flask]
- step_prune_expired
- Vite Build Tool
- eslint-plugin-react-hooks
- eslint-plugin-react-refresh
- globals
- @playwright/test
- tailwindcss
- @testing-library/jest-dom
- @testing-library/user-event
- @types/react
- @types/react-dom
- Data science deps (pandas, scikit-learn, numpy, scipy, joblib, shapely)
- Flask stack (Flask, flask-cors, flask-limiter, flasgger, pydantic)
- oracle-network bridge
- Frontend README (Vite/React template)
- React Logo (react.svg)
- CI/CD to Render and dependency scan (ORA-64/65)
- Application Security Review (OWASP Top 10) — ORA-69
- OWASP A01: Broken Access Control — risk accepted (ORA-46)
- OWASP A02: Cryptographic Failures — OK
- OWASP A03: Injection — OK
- OWASP A04: Insecure Design — OK
- OWASP A05: Security Misconfiguration — partially corrected
- OWASP A07: Identification and Authentication Failures — risk accepted (ORA-46)
- OWASP A10: Server-Side Request Forgery — OK
- scraper_century_21.py

## God Nodes (most connected - your core abstractions)
1. `ChatService` - 51 edges
2. `AnnoncesStoreTest` - 36 edges
3. `build_report_html()` - 25 edges
4. `run_fusion()` - 22 edges
5. `_geocode()` - 21 edges
6. `retry_with_backoff()` - 20 edges
7. `ChatServiceTest` - 19 edges
8. `pick_user_agent()` - 18 edges
9. `App()` - 18 edges
10. `BuildReportHtmlTest` - 16 edges

## Surprising Connections (you probably didn't know these)
- `ORA-180: geocoding of listing addresses via IGN Geoplateforme` --semantically_similar_to--> `Geocoding of listing addresses (PRIVACY section)`  [INFERRED] [semantically similar]
  LEGAL_DECISIONS.md → PRIVACY.md
- `generate_map.py` --semantically_similar_to--> `generate_map.py (Folium static map)`  [INFERRED] [semantically similar]
  MAP_CONTRACT.md → README.md
- `recheck_ambiguous()` --calls--> `_fetch_all_annonces()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `check_url_status_browser()` --calls--> `looks_like_soft_404()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `docker-compose service: airflow-scheduler` --references--> `Airflow DAG oracle_annonces_pipeline (weekly)`  [INFERRED]
  docker-compose.yml → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Airflow docker-compose services** — docker_compose_airflow_db, docker_compose_airflow_init, docker_compose_airflow_webserver, docker_compose_airflow_scheduler [EXTRACTED 1.00]
- **Weekly annonces ETL pipeline** — readme_data_fusion, readme_clean_immo, readme_train_model, readme_generate_map [EXTRACTED 1.00]
- **Map postMessage message types** — map_contract_fly_to, map_contract_fly_to_bounds, map_contract_set_tile_url, map_contract_toggle_layer, map_contract_annonce_click [EXTRACTED 1.00]
- **OWASP Top 10 (2021) Security Checklist** — security_review_a01_broken_access_control, security_review_a02_crypto_failures, security_review_a03_injection, security_review_a04_insecure_design, security_review_a05_security_misconfiguration, security_review_a06_vulnerable_components, security_review_a07_auth_failures, security_review_a08_integrity_failures, security_review_a09_logging_monitoring, security_review_a10_ssrf [EXTRACTED 1.00]

## Communities (183 total, 65 thin omitted)

### Community 0 - "test_scraper_extraction_fixtures.py"
Cohesion: 0.06
Nodes (19): bs4_first_attr(), bs4_first_text(), bs4_select_first_matching(), Century21ExtractionTest, DetailDescriptionExtractionTest, _FakeElement, load_fixture(), OrpiExtractionTest (+11 more)

### Community 1 - "monitor_drift.py"
Cohesion: 0.07
Nodes (29): CI Workflow (ci.yml), CI job: backend (pytest), CI job: dependency-scan (pip-audit, npm audit), CI job: deploy (Render deploy hooks, ORA-64), CI job: e2e (Playwright vs vite preview + Flask), CI job: frontend (lint, build, test), CI job: scrapers (pytest, excludes e2e), Model Drift Monitor Workflow (+21 more)

### Community 2 - "train_model.py"
Cohesion: 0.10
Nodes (20): load_declared_villes(), Villes déclarées dans scraping_config.json (ORA-71) : ajouter une ville au JSON…, archive_model_version(), Conserve une copie du modèle sous un nom versionné (hash du binaire), pour…, Archive un instantané content-addressé de `csv_path` dans `snapshots_dir` et…, Écrit `<model_path>.meta.json`, référençant explicitement la version des…, record_model_metadata(), _sha256_of_file() (+12 more)

### Community 3 - "detail_cavaliers"
Cohesion: 0.11
Nodes (17): enrich_annonce_detail(), ORA-174 (maquette 06, "Fiche annonce") : enrichit une annonce issue…, detail_cavaliers(), list_poi_types(), _phrase_for(), Détail complet des 4 Cavaliers pour un sous-ensemble d'annonces (ORA-172,…, Introspecte les colonnes `dist_<catégorie>_<poi>` réellement présentes dans…, Résume les 4 "Cavaliers" (Vice, Gentrification, Nuisance, Superstition) pour un… (+9 more)

### Community 4 - "app.py"
Cohesion: 0.07
Nodes (37): after_request, chat(), get_annonces(), get_chat_rate_limit(), get_cors_origins(), get_default_rate_limits(), get_listings(), get_quartier_historique() (+29 more)

### Community 5 - "request_with_retry"
Cohesion: 0.08
Nodes (19): extract_coordinates_from_html(), get_gps_from_url(), process_row(), Chemins d'entrée/sortie pour une ville donnée (slug scraping_config.json, ex:…, Coordonnées GPS (lat, lon) trouvées dans le HTML d'une fiche annonce, ou (None,…, Télécharge la page et en extrait les coordonnées GPS réelles., Fonction exécutée par chaque thread, resolve_paths() (+11 more)

### Community 6 - "AnnoncesStoreTest"
Cohesion: 0.05
Nodes (4): AnnoncesStoreTest, ORA-173 : "€/m² croissant" (tri par défaut de la maquette 05) — prix_m2 n'est…, `NULLIF(surface, 0)` -> NULL pour une surface manquante : SQLite trie NULL…, Le frontend envoie le slug de la ville active ("lyon"), la colonne stocke…

### Community 7 - "clean_immo.py"
Cohesion: 0.09
Nodes (36): build_shapes_from_cavaliers(), build_titre(), clean_zipcode(), determine_type_local(), extract_seloger_quartier_slug(), get_nearest_distance_and_count(), get_point_for_zipcode(), get_point_in_circle() (+28 more)

### Community 8 - "App.jsx"
Cohesion: 0.11
Nodes (19): App(), renderCalquesView(), renderEstimationView(), renderScanView(), renderSummaryChip(), makePanelFallback(), MOBILE_TABS, useIsDesktop() (+11 more)

### Community 10 - "build_report_html"
Cohesion: 0.11
Nodes (15): build_report_html(), _ecart_html(), _ecart_pct(), _escape(), _format_m2(), _format_price(), _quartile_stats(), Rend le rapport d'estimation en PDF (bytes), via WeasyPrint (ORA-121). (+7 more)

### Community 11 - "CheckUrlStatusBrowserTest"
Cohesion: 0.09
Nodes (4): CheckUrlStatusBrowserTest, LooksLikeChallengePageTest, LooksLikeValidListingTest, RecheckAmbiguousTest

### Community 12 - "get_connection"
Cohesion: 0.09
Nodes (29): get_annonce_detail(), log_annonce_click(), Détail d'une annonce par son id (ORA-85). --- tags: - Annonces parameters: -…, Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le…, Alimente la table SQLite `annonces` (services/annonces_store.py) à partir du…, step_sync_annonces_store(), _fetch_all_annonces(), prune_dead_annonces() (+21 more)

### Community 13 - "build_feature_row"
Cohesion: 0.11
Nodes (16): build_feature_row(), compute_distance_features(), haversine_distance_m(), normalize_type_bien(), normalize_type_local(), Construit le vecteur de features attendu par le modèle à partir du payload…, Normalise un type de bien utilisateur (T1, studio, T4+...) vers une catégorie…, Normalise le type de bien brut (Appartement/Maison/Studio), 'Appartement' par… (+8 more)

### Community 14 - "resolve_quartier_filter"
Cohesion: 0.15
Nodes (11): compute_price_history(), _filter_quartier(), Calcule l'évolution du prix moyen/m² pour `quartier` à travers tous les…, Résolution d'une recherche utilisateur (texte libre) en un sous-ensemble du…, Sous-ensemble de `df` correspondant à la recherche `quartier_input`, et les…, resolve_quartier_filter(), ComputePriceHistoryTest, ORA-110 : même matching partagé (fuzzy) que /api/quartier-stats, au lieu d'un… (+3 more)

### Community 15 - "generate_map.py"
Cohesion: 0.11
Nodes (27): build_bridge_message_script(), build_immo_popup_html(), build_immo_tooltip_html(), build_legend_and_scale_script(), build_legend_html(), compute_layer_counts(), filter_by_ville(), load_geojson_file() (+19 more)

### Community 16 - "_geocode"
Cohesion: 0.16
Nodes (6): AdresseGeocodeeTest, _geocode(), _geocodeur(), OrdrePrioriteLocalisationTest, Une annonce, colonnes par défaut vides ; renvoie le df après step_geocoding., _sans_reseau()

### Community 17 - "test_scraper_utils.py"
Cohesion: 0.11
Nodes (10): find_first(), Décide si la pagination d'un scraper doit continuer après une page où…, Essaie chaque sélecteur CSS de `selectors` dans l'ordre sur `element` et…, should_continue_pagination(), BlankShortDescriptionsTest, CleanDescriptionTest, FakeElement, FindFirstTest (+2 more)

### Community 18 - "test_playwright_selectors.py"
Cohesion: 0.12
Nodes (19): expectedFailure, assert_selector_canary(), Century21SelectorCanaryTest, find_cards(), find_first_locator_text(), new_page(), OrpiSelectorCanaryTest, PapSelectorCanaryTest (+11 more)

### Community 19 - "ChatRequestSchema"
Cohesion: 0.14
Nodes (11): ChatRequestSchema, ComparableSchema, FacteurSchema, PdfReportRequestSchema, PredictRequestSchema, PriceHistoryPointSchema, Schémas de validation des payloads pour les routes Flask actives (/api/chat,…, ChatRequestSchemaTest (+3 more)

### Community 20 - "localisation_texte.py"
Cohesion: 0.14
Nodes (16): _candidats(), _nom_propre(), Adresse du bien extraite d'un texte libre (ORA-180) : « 52 rue André Bollier ».…, [(adresse, avec_numero)] acceptées dans une phrase brute., _clause_propre(), _evaluer(), extraire_zone(), localiser_par_texte() (+8 more)

### Community 21 - "recheck_dead_annonces.py"
Cohesion: 0.17
Nodes (10): check_url_status_browser(), looks_like_challenge_page(), looks_like_valid_listing(), Re-vérification via navigateur furtif (undetected_chromedriver) des annonces…, True si `html_text` contient un signal de prix exploitable (montant chiffré, ou…, Vérifie une url via un vrai navigateur furtif. Renvoie True (confirmée morte),…, True si `html_text` correspond à une page de challenge anti-bot (CAPTCHA)…, get_scraper_logger() (+2 more)

### Community 22 - "AnnonceCard.jsx"
Cohesion: 0.16
Nodes (18): AnnonceCard(), formatPrice(), ILLUSTRATION_BY_CATEGORY, baseAnnonce, formatM2(), formatPrice(), formatShortDate(), historyPeriod() (+10 more)

### Community 23 - "merge_cavaliers"
Cohesion: 0.13
Nodes (14): get_cavaliers_data(), merge_cavaliers(), Lit le nom de la ville active (`villes.<ville_active>.nom`) depuis…, Résout le nom d'affichage d'une ville depuis son slug, indépendamment de…, Fusionne les cavaliers déjà connus avec les cavaliers fraîchement extraits.…, Récupère la liste complète des lieux pour chaque catégorie et fusionne avec le…, resolve_active_city_name(), resolve_city_name() (+6 more)

### Community 24 - "run_fusion"
Cohesion: 0.11
Nodes (12): Fusionne les CSV scrapés en base_de_donnees_immo_complet.csv. Par défaut…, run_fusion(), LoadDeclaredVillesTest, PostalCodeFromUrlTest, ORA-134 : la colonne DerniereVue des scrapers doit survivre à la fusion sous le…, ORA-161 : la description libre scrapée sur la page détail (colonne…, ORA-71 POC follow-up : run_fusion() doit résoudre le vrai lieu SeLoger (voire…, ORA-153 : chaque DAG annonces tourne désormais indépendamment par ville.… (+4 more)

### Community 25 - "prepare_new_city.py"
Cohesion: 0.17
Nodes (14): build_config_skeleton(), build_report(), classify(), fetch_arrondissements(), fetch_commune(), fetch_shared_postal_codes(), _get(), main() (+6 more)

### Community 26 - "annonces_store.py"
Cohesion: 0.13
Nodes (15): check_url_status(), looks_like_soft_404(), Nettoyage ponctuel des annonces mortes dans annonces.db (ORA-134). Le pipeline…, True si `html_text` contient un des `SOFT_404_PATTERNS` (insensible à la casse)., Vérifie une url en direct. Renvoie True (confirmée morte : 404/410, ou soft-404…, check_url_status_async(), Vérification HTTP asynchrone des annonces à statut incertain (ORA-134 bis, tier…, Vérifie les annonces éligibles (cf. `_rows_to_verify`) et met à jour leur… (+7 more)

### Community 27 - "data_fusion.py"
Cohesion: 0.14
Nodes (11): normalize_lieu(), postal_code_from_url(), CP de repli pour une ville (cf. extract_postal_code). Fail-fast plutôt que de…, Config des fichiers 'classiques' (hors Vizzit) pour une ville donnée, à partir…, Century 21' -> 'century21' : clé de l'option --sites., CP encodé dans l'URL d'une annonce Orpi (`.../annonce-location-…, resolve_default_cp(), site_files_config() (+3 more)

### Community 28 - "LoggingConfigTest"
Cohesion: 0.10
Nodes (7): configure_logging(), init_sentry(), Configuration centralisée de l'observabilité applicative du backend (ORA-63).…, Configure le logger racine du process avec un format structuré et un niveau…, Initialise sentry-sdk pour capturer automatiquement les exceptions non gérées…, LoggingConfigTest, Vérifie le logger structuré centralisé (ORA-63) : niveau par défaut, prise en…

### Community 29 - "GetTileTest"
Cohesion: 0.12
Nodes (4): BuildUpstreamUrlTest, GetTileTest, IsValidTileTest, TileRouteTest

### Community 30 - "scraper_paruvendu.py"
Cohesion: 0.13
Nodes (18): checkpoint(), fetch_description(), fetch_page(), find_description_bs4(), find_image_bs4(), find_lien_partiel(), Lien de l'annonce : le titre s'il est un <a>, sinon le premier lien…, Équivalent BeautifulSoup de `selenium_description_fetcher` : premier texte de… (+10 more)

### Community 31 - "useAnnonceDetail.js"
Cohesion: 0.14
Nodes (15): AnnonceIllustration(), AnnoncesList(), loadAnnonces(), SORT_OPTIONS, useAnnonceDetail(), useFavorites(), deriveSource(), getTypeCategory() (+7 more)

### Community 32 - "scraper_seloger.py"
Cohesion: 0.20
Nodes (8): checkpoint(), load_page(), parse_title_attribute(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Parse 'Type - Lieu - Prix - Infos' format. Returns None if format unrecognized., canonical_url(), Retire la query string et le fragment d'une URL d'annonce. Régression réelle…, SeLoger scraper test fixture (HTML)

### Community 33 - "step_flag_expired"
Cohesion: 0.18
Nodes (5): `sur_carte` : True si l'annonce a été revue lors du dernier scrape de son…, Fusionne `df` (résultat frais de data_fusion.py) avec le…, step_flag_expired(), _vu_au_dernier_scrape(), StepFlagExpiredTest

### Community 34 - "AdresseDuBienTest"
Cohesion: 0.20
Nodes (5): extraire_adresse(), localiser_adresse(), (adresse | None, raison courte). Contradiction = None., Premier texte (dans l'ordre donné) qui décide ; une contradiction est…, AdresseDuBienTest

### Community 35 - "normalize_text"
Cohesion: 0.24
Nodes (6): compact_text(), normalize_text(), searchable_text(), CompactTextTest, NormalizeTextTest, SearchableTextTest

### Community 36 - "QuartierStatsRouteTest"
Cohesion: 0.11
Nodes (6): QuartierStatsRouteTest, ORA-110 : le endpoint utilise désormais le matching partagé (fuzzy) au lieu…, ORA-111 : message différencié aucun résultat vs quartier ambigu., ORA-111 : suggestions renvoyées quand plusieurs quartiers sont proches., ORA-167 : min/P25/médiane/P75/max calculés sur tous les biens filtrés, pas sur…, ORA-122/ORA-128/ORA-177 : échantillon de biens comparables réels, pour le…

### Community 37 - "AnnonceDetailModal.jsx"
Cohesion: 0.33
Nodes (6): AnnonceDetailContent(), CATEGORY_STYLES, formatM2(), formatPrice(), AnnonceDetailModal(), detail

### Community 38 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, devDependencies, eslint, @eslint/js, jsdom, postcss, @testing-library/react (+9 more)

### Community 39 - "API Contract (Oracle des Loyers)"
Cohesion: 0.17
Nodes (16): API Contract (Oracle des Loyers), GET /api/health, Decision ORA-46: no authentication on routes, POST /api/chat (Immotep chatbot), POST /api/quartier-historique, POST /api/report/pdf (WeasyPrint), Rate limiting (Flask-Limiter), google-genai (Gemini client) (+8 more)

### Community 41 - "RowsToVerifyTest"
Cohesion: 0.12
Nodes (9): Integration test: mix of all statuses with various verification timestamps., Test the date-arithmetic logic of _rows_to_verify (TTL/staleness detection)., Row with statut='active' and derniere_verification_http older than ttl_days →…, Row with statut='active' and derniere_verification_http within ttl_days → NOT…, Row with statut='active' and missing/empty derniere_verification_http →…, Row with statut='active' and NaT derniere_verification_http → included., Row with statut='a_verifier' regardless of derniere_verification_http → always…, Row with statut='inactive' → never included (even with stale/missing timestamp). (+1 more)

### Community 42 - "pick_user_agent"
Cohesion: 0.13
Nodes (16): prune_dead_map_listings(), Nettoyage ponctuel des annonces mortes dans master_immo_final.csv + carte…, Écrit dans un fichier temporaire puis remplace `path` via os.replace (atomique)…, Vérifie chaque url de `csv_path` (HTTP puis navigateur headless pour les…, _write_csv_atomically(), Re-teste chaque annonce de `db_path` en HTTP, puis escalade au navigateur…, recheck_ambiguous(), _detect_local_chrome_major_version() (+8 more)

### Community 43 - "scraper_vizzit.py"
Cohesion: 0.18
Nodes (15): find_first_image_url(), Cherche la première balise <img> correspondant à l'un des `selectors` dans…, apply_price_band(), build_page_url(), checkpoint(), decode_data_o_link(), find_attr(), find_text() (+7 more)

### Community 45 - "ModelRegressionTest"
Cohesion: 0.17
Nodes (8): ModelRegressionTest, PredictEndpointRegressionTest, _prepare_features(), ORA-154 : un modèle XGBoost distinct par ville plutôt que `ville` en feature…, Non-régression explicite du bug corrigé par ORA-30 : /api/predict renvoyait…, Reproduit exactement le prétraitement de train_model.py (ORA-154, ORA-155),…, Remplace backend/scripts/test_prediction.py (script manuel, échantillon…, VilleExcludedFromFeaturesTest

### Community 46 - "scraper_pap.py"
Cohesion: 0.17
Nodes (7): checkpoint(), load_page(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, load_existing_rows(), Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble…, PAP scraper test fixture (HTML), LoadExistingRowsTest

### Community 47 - "clean_immo.py"
Cohesion: 0.18
Nodes (14): GET /api/annonces, ORA-180: geocoding of listing addresses via IGN Geoplateforme, annonces_store.py changes (premiere_vue, derniere_vue, record_price_observation), historique_prix table (append-only price history), price_evolution.py compute_price_trend, step_flag_expired (clean_immo.py, 2-state merge), step_flag_expired (3-state preserving merge), Geocoding of listing addresses (PRIVACY section) (+6 more)

### Community 48 - "DataLoader"
Cohesion: 0.18
Nodes (9): DataLoader, Charge le CSV en mémoire et applique un nettoyage de base., Renvoie le DataFrame brut., clean_input_data(), format_prediction_response(), guess_room_count_smart(), Nettoie les données entrantes., Devine le type de logement (T1, T2...) basé sur la surface si l'information est… (+1 more)

### Community 49 - "PredictRouteTest"
Cohesion: 0.14
Nodes (4): PredictRouteTest, ORA-154 : la panne d'un modèle ne doit plus dégrader toutes les villes — seule…, ORA-152 : un modèle qui prédit un loyer négatif (ex. pickle XGBoost désérialisé…, Un loyer exactement nul n'est pas plus plausible qu'un loyer négatif.

### Community 51 - "SearchForm.jsx"
Cohesion: 0.30
Nodes (8): formatEuros(), SearchForm(), splitAtMatch(), quartierOptions, TYPE_FILTERS, normalizeText(), loadRecentSearches(), pushRecentSearch()

### Community 52 - "scraper_utils.py"
Cohesion: 0.21
Nodes (6): atomic_csv_writer(), Écrit dans un fichier temporaire à côté de `output_path` et ne remplace ce…, load_details_config(), Utilitaires partagés entre les 6 scrapers (Century21, Orpi, PAP, ParuVendu,…, Réglages de la visite des pages détail (bloc `details` de scraping_config.json)…, AtomicCsvWriterTest

### Community 53 - "EnrichDescriptionsTest"
Cohesion: 0.25
Nodes (3): EnrichDescriptionsTest, _Logger, ORA-161 : visite des pages détail plafonnée, sans jamais insister en cas de…

### Community 55 - "RateLimitBehaviorTest"
Cohesion: 0.15
Nodes (4): RateLimitBehaviorTest, RateLimitConfigTest, ORA-118 : le frontend a besoin de X-RateLimit-Remaining pour afficher un…, Sans Access-Control-Expose-Headers, fetch() côté frontend ne peut pas lire ces…

### Community 56 - "dependencies"
Cohesion: 0.15
Nodes (13): dependencies, leaflet, react, react-dom, react-leaflet, react-markdown, remark-gfm, leaflet (+5 more)

### Community 57 - "ChatOracle.jsx"
Cohesion: 0.28
Nodes (8): ALL_TYPES, buildChatContext(), ChatOracle(), DEFAULT_MESSAGES, describeChatError(), ApiError, loadChatHistory(), saveChatHistory()

### Community 58 - "archive_stale_rows"
Cohesion: 0.32
Nodes (3): archive_stale_rows(), Déplace de `rows_by_lien` vers `<output>_archive.csv` les annonces non revues…, ArchiveStaleRowsTest

### Community 59 - "extract_postal_code"
Cohesion: 0.29
Nodes (3): extract_postal_code(), Normalise le CP (69XXX ou 59XXX). `default_cp` est le repli utilisé quand aucun…, ExtractPostalCodeTest

### Community 60 - "resolve_seloger_lieu"
Cohesion: 0.27
Nodes (4): CP réel déduit du champ `Lieu` de SeLoger, ou du premier segment d'`Infos`…, resolve_seloger_lieu(), ORA-71 POC follow-up : le champ Lieu de SeLoger contient parfois une vraie…, ResolveSelogerLieuTest

### Community 62 - "match_quartier"
Cohesion: 0.29
Nodes (4): match_quartier(), Fait correspondre `query` (texte libre, éventuellement fautif ou noyé dans une…, MatchQuartierTest, ORA-109 : tolérance aux fautes de frappe sur les quartiers connus.

### Community 63 - "test_chat_service.py"
Cohesion: 0.20
Nodes (4): ExtractLocationsFuzzyMatchingTest, FakeClient, FakeModels, ORA-109 : la recherche de quartier tolère les fautes de frappe.

### Community 64 - "File Structure"
Cohesion: 0.18
Nodes (10): File Structure, Global Constraints, Nettoyage non-destructif des annonces mortes — Implementation Plan, Prochaines étapes après ce plan (hors scope, à netifier séparément si besoin), Self-Review, Task 1: Migration DB non-destructive + statut dans `annonces_store.py`, Task 2: Fusion préservante dans `clean_immo.py` (remplace le drop TTL), Task 3: Vérificateur HTTP asynchrone (`verify_annonces_async.py`) (+2 more)

### Community 65 - "Scraper extraction fixture tests (ORA-19)"
Cohesion: 0.18
Nodes (11): ORA-67/93: scraper compliance with robots.txt/CGU, Scraper extraction fixture tests (ORA-19), Six scrapers (Century21, Orpi, PAP, SeLoger, ParuVendu, Vizzit), Playwright selector canary (ORA-20/21), Century21 detail page fixture, Orpi detail page fixture, Orpi results page fixture, PAP detail page fixture (synthetic) (+3 more)

### Community 66 - "verify_annonces_async.py (aiohttp HTTP verifier)"
Cohesion: 0.22
Nodes (11): Plan: separate map display from ML archive (ORA-144), Two-state status active/archivee driven by scrape diff, Plan: non-destructive dead-listing cleanup (ORA-134 bis), Non-destructive cleanup principle (never delete rows), oracle_cleanup_pipeline Airflow DAG (daily), Three-state status active/a_verifier/inactive, annonces_store.update_statut, verify_annonces_async.py (aiohttp HTTP verifier) (+3 more)

### Community 67 - "Map postMessage Contract"
Cohesion: 0.20
Nodes (10): Decision ORA-86: direct redirect, no intermediate modal, POST /api/annonces/<id>/click, ORA-94: photo hosting decision (superseded by ORA-134 hotlink), postMessage ANNONCE_CLICK (iframe to React), Map postMessage Contract, postMessage FLY_TO, postMessage FLY_TO_BOUNDS, Origin verification security (ORA-125) (+2 more)

### Community 68 - "get_map_tile"
Cohesion: 0.24
Nodes (9): get_map_tile(), Proxy des tuiles CARTO du fond de carte : la clé API reste côté serveur…, build_upstream_url(), get_tile(), is_valid_tile(), Proxy des tuiles du fond de carte CARTO. CARTO exige une clé API sur ses…, Coordonnées de tuile plausibles : 0 <= z <= MAX_ZOOM, x et y dans [0, 2^z)., URL CARTO d'une tuile (sans la clé : elle voyage en paramètre séparé). (+1 more)

### Community 69 - "decide_promotion"
Cohesion: 0.15
Nodes (9): decide_promotion(), load_active_model_metadata(), Lit les métadonnées (`metrics`, `model_version`) du modèle actuellement actif…, Décide si un modèle nouvellement entraîné doit remplacer le modèle actif.…, DecidePromotionTest, LoadActiveModelMetadataTest, PromotionGuardTriggersRollbackTest, ORA-34 : un ré-entraînement automatique (DAG Airflow quotidien) ne doit jamais… (+1 more)

### Community 70 - "MergeAllVillesTest"
Cohesion: 0.33
Nodes (4): merge_all_villes(), L'Oracle des Loyers — Fusion des cavaliers par ville Concatène les…, MergeAllVillesTest, ORA-153 : avant ce script, rien ne produisait cavaliers_all.csv automatiquement…

### Community 71 - "test_clean_immo_steps.py"
Cohesion: 0.20
Nodes (3): GetPointForZipcodeZonesLimitrophesTest, StepIdsTest, StepTypesTest

### Community 72 - "test_generate_map.py"
Cohesion: 0.20
Nodes (4): FilterByVilleTest, LegendAndScaleTest, Aucune clé, ni URL CARTO, dans la carte générée (fichier versionné)., TileLayerNeverEmbedsAKeyTest

### Community 73 - "File Structure"
Cohesion: 0.20
Nodes (9): File Structure, Global Constraints, Note pour la suite (hors scope de ce plan), Self-Review, Séparation affichage carte / archive ML Implementation Plan, Task 1: `annonces_store.py` — statut 2-états, premiere_vue/derniere_vue, table `historique_prix`, Task 2: `clean_immo.py` — diff de scrape simplifié (2 états) + retrait du tier HTTP, Task 3: Filtrage affichage (carte + API) + vocabulaire XGBoost (+1 more)

### Community 74 - "scraper_orpi.py"
Cohesion: 0.15
Nodes (10): _fetch_geocodage(), geocode_adresse(), checkpoint(), load_page(), parse_quartier(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Nom de quartier seul depuis le libellé de localisation Orpi ("Lyon 8-…, Décorateur retry/backoff générique pour les opérations de scraping instables… (+2 more)

### Community 76 - "extract_type"
Cohesion: 0.36
Nodes (3): extract_type(), Détermine le type de bien (Maison, Appartement, Studio, Coloc)., ExtractTypeTest

### Community 77 - "ReportPdfRouteTest"
Cohesion: 0.22
Nodes (3): ORA-122 : enrichissement du rapport (historique de prix, biens comparables)., ORA-177 : champs ajoutés pour aligner le rapport sur la maquette 09 (case…, ReportPdfRouteTest

### Community 78 - "BuildBridgeMessageScriptTest"
Cohesion: 0.22
Nodes (4): BuildBridgeMessageScriptTest, Contrat postMessage carte (ORA-125) : la carte générée ne doit traiter un…, ORA-105 : recentrage sur la bounding-box des résultats filtrés., L'URL du proxy de tuiles arrive au runtime (dépend du déploiement) : validée…

### Community 81 - "PanelNav.jsx"
Cohesion: 0.33
Nodes (4): ICON_PROPS, icons, PanelNav(), PANEL_VIEWS

### Community 82 - "api.js"
Cohesion: 0.33
Nodes (7): API_URL, apiFetchOptions(), classifyResponseError(), fetchWithClassification(), getApiBaseUrl(), LOCAL_HOSTS, parseRateLimitHeaders()

### Community 83 - "computeHomeStats"
Cohesion: 0.44
Nodes (7): arrondissementLabel(), computeHomeStats(), groupMedianPrixM2(), isFiniteNumber(), isLocated(), median(), listings

### Community 84 - "computeQuartierOptions"
Cohesion: 0.39
Nodes (7): arrondissementLabel(), computeQuartierOptions(), isFiniteNumber(), isLocated(), median(), mostFrequent(), listings

### Community 85 - "train_model.py (XGBoost per city)"
Cohesion: 0.29
Nodes (8): GET /api/listings, POST /api/predict, xgboost==2.1.4 pin (ORA-152), Display filter statut=active (api/listings, generate_map), XGBoost training keeps archived listings, master_immo_final.csv, Multi-city generality Lyon and Lille (ORA-71/153/154), train_model.py (XGBoost per city)

### Community 86 - "generate_map.py (Folium static map)"
Cohesion: 0.39
Nodes (8): folium, Generated Folium map for Lille (map_pings_lille_calques), Generated Folium map for Lyon (map_pings_lyon_calques), generate_map.py, mapLayers.config.json shared layer config (ORA-130), MapComponent.jsx, generate_map.py (Folium static map), Decision ORA-106: keep static pre-rendered map

### Community 88 - "clean_price_integer"
Cohesion: 0.39
Nodes (3): clean_price_integer(), Convertit en entier (supprime €, cc, espaces, points)., CleanPriceIntegerTest

### Community 89 - "clean_surface"
Cohesion: 0.39
Nodes (3): clean_surface(), Extrait le nombre avant 'm2'., CleanSurfaceTest

### Community 90 - "resolve_quartier"
Cohesion: 0.36
Nodes (4): Résout `query` vers le libellé canonique d'un quartier de `known_quartiers`, ou…, resolve_quartier(), ORA-110 : point d'entrée unique utilisé par /api/quartier-stats, /api/quartier-…, ResolveQuartierTest

### Community 91 - "LoadLayersConfigTest"
Cohesion: 0.25
Nodes (3): LoadLayersConfigTest, ORA-130 : la liste des calques (nom Folium/TOGGLE_LAYER, visibilité par défaut,…, Non-régression ORA-130 : le refactor ne doit rien changer à l'état initial des…

### Community 93 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, test, test:e2e, test:watch

### Community 96 - "test_rollback_model.py"
Cohesion: 0.29
Nodes (3): ORA-154 : un modèle distinct par ville — price_predictor_<ville>.pkl, pas un…, ResolveModelPathTest, RollbackModelTest

### Community 98 - "package.json"
Cohesion: 0.29
Nodes (6): name, overrides, vite, private, type, version

### Community 99 - "load_site_config"
Cohesion: 0.38
Nodes (3): load_site_config(), Charge la config de la ville active (URL de recherche, paramètre de pagination)…, LoadSiteConfigTest

### Community 100 - "format_description"
Cohesion: 0.47
Nodes (3): format_description(), Nettoie la description pour l'affichage final., FormatDescriptionTest

### Community 101 - "fetch_lyon_arrondissements.py"
Cohesion: 0.53
Nodes (5): fetch_arrondissement_boundary(), main(), ordinal_label(), Récupère une fois les polygones des 9 arrondissements de Lyon (Nominatim/ OSM)…, Récupère le polygone GeoJSON d'un arrondissement de Lyon via Nominatim.

### Community 102 - "geocodage.py"
Cohesion: 0.47
Nodes (5): _charger_cache(), geocoder(), _interroger(), Géocodage d'une adresse de Lyon via la Géoplateforme de l'IGN (ORA-180).…, {'lat', 'lon', 'precision': 'numero'|'rue', 'cp'} ou None ('lyon' ou 'lille').…

### Community 103 - "HealthRouteTest"
Cohesion: 0.33
Nodes (3): HealthRouteTest, ORA-154 : un modèle distinct par ville — /api/health expose l'état de chacun…, ORA-171 : "entraîné sur N annonces" (maquette 03) doit venir du dernier run…

### Community 112 - "Airflow DAG oracle_annonces_pipeline (weekly)"
Cohesion: 0.33
Nodes (6): docker-compose service: airflow-db (postgres:14), docker-compose service: airflow-init, docker-compose service: airflow-scheduler, docker-compose service: airflow-webserver, Airflow DAG oracle_annonces_pipeline (weekly), data_fusion.py

### Community 113 - "QuartierAmbigu.jsx"
Cohesion: 0.47
Nodes (4): formatEuros(), QuartierAmbigu(), ambiguous, quartierOptions

### Community 114 - "POST /api/quartier-stats"
Cohesion: 0.40
Nodes (5): cavaliers_factors.py (Cavaliers phrases), POST /api/quartier-stats, Fuzzy quartier text matching (text_matching.py), rapidfuzz (fuzzy matching), Les 4 Cavaliers (Gentrification, Vice, Nuisance, Superstition)

### Community 115 - "fetch_lille_quartiers.py"
Cohesion: 0.50
Nodes (4): fetch_boundary(), main(), Récupère une fois les contours réels des quartiers de Lille (+ Lomme,…, Renvoie une Feature GeoJSON polygonale pour `nom`, ou None si OSM n'a pas de…

### Community 125 - "Tech architecture (React, Flask, XGBoost, Gemini, Docker)"
Cohesion: 0.40
Nodes (5): docker-compose service: backend, docker-compose service: frontend (Vite dev), Vite frontend HTML shell (fonts Inter/Archivo, ORA-170), Tech architecture (React, Flask, XGBoost, Gemini, Docker), Decision ORA-119: Gemini + deterministic filtering, no local RAG

### Community 126 - "CavaliersDetail.jsx"
Cohesion: 0.50
Nodes (3): CATEGORY_STYLES, CavaliersDetail(), detail

### Community 127 - "HomeOverview.jsx"
Cohesion: 0.60
Nodes (4): formatEuros(), HomeOverview(), numberFmt, QuartierRow()

### Community 128 - "get_db_connection"
Cohesion: 0.50
Nodes (4): get_db_connection(), init_db(), Initialise la table 'annonces' si elle n'existe pas., Crée une connexion à la base de données.

### Community 129 - "is_context_safe"
Cohesion: 0.67
Nodes (3): extract_address_hybrid(), is_context_safe(), Vérifie si le texte précédant l'adresse contient des mots interdits (proche,…

### Community 182 - "scraper_century_21.py"
Cohesion: 0.18
Nodes (9): checkpoint(), load_page(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Date du jour (UTC) au format ISO — utilisée pour horodater la colonne…, `fetch_description(url)` pour `enrich_descriptions` avec un driver Selenium :…, selenium_description_fetcher(), today_iso(), Century21 scraper test fixture (HTML) (+1 more)

## Knowledge Gaps
- **134 isolated node(s):** `ambiguous`, `quartierOptions`, `CATEGORY_STYLES`, `detail`, `numberFmt` (+129 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **65 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ChatService` connect `ChatService` to `ChatServiceTest`, `normalize_text`, `app.py`, `test_chat_service.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `pick_user_agent()` connect `pick_user_agent` to `scraper_seloger.py`, `scraper_orpi.py`, `scraper_vizzit.py`, `scraper_pap.py`, `test_scraper_utils.py`, `test_playwright_selectors.py`, `scraper_utils.py`, `recheck_dead_annonces.py`, `scraper_century_21.py`, `scraper_paruvendu.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Why does `get_scraper_logger()` connect `recheck_dead_annonces.py` to `scraper_seloger.py`, `pick_user_agent`, `scraper_orpi.py`, `scraper_vizzit.py`, `scraper_pap.py`, `test_scraper_utils.py`, `scraper_utils.py`, `scraper_century_21.py`, `scraper_paruvendu.py`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ChatService` (e.g. with `ChatServiceTest` and `ExtractLocationsFuzzyMatchingTest`) actually correct?**
  _`ChatService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `run_fusion()` (e.g. with `clean_price_integer()` and `clean_surface()`) actually correct?**
  _`run_fusion()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `ambiguous`, `quartierOptions`, `CATEGORY_STYLES` to the rest of the system?**
  _134 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_scraper_extraction_fixtures.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0611764705882353 - nodes in this community are weakly interconnected._