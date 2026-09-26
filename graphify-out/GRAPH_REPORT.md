# Graph Report - oracle_loyers  (2026-09-27)

## Corpus Check
- 223 files · ~561,277 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2301 nodes · 3601 edges · 221 communities (138 shown, 83 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `48abbaf5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- CalquesView.jsx
- record_model_metadata
- monitor_drift.py
- localisation_texte.py
- app.py
- AnnoncesStoreTest
- complete_data_extraction.py
- recheck_dead_annonces.py
- scraper_orpi.py
- build_feature_row
- generate_map.py
- ChatService
- build_report_html
- App.jsx
- RowsToVerifyTest
- compute_price_history
- test_scraper_utils.py
- GetTileTest
- scraper_vizzit.py
- _geocode
- test_playwright_selectors.py
- AnnonceCard.jsx
- CavaliersRadiusServiceTest
- merge_cavaliers
- prepare_new_city.py
- clean_immo.py
- CavaliersRadiusService
- CavaliersRequestSchema
- get_connection
- ChatOracle.jsx
- scraper_utils.py
- LoggingConfigTest
- AdresseDuBienTest
- pick_user_agent
- archive_stale_rows
- summarize_cavaliers
- GeocodageTest
- BuildBridgeMessageScriptTest
- useAnnonceDetail.js
- test_data_fusion.py
- run_fusion
- normalize_text
- QuartierStatsRouteTest
- step_flag_expired
- devDependencies
- AnnonceDetailModal.jsx
- MergeAllVillesTest
- AnnoncesRoutesTest
- ChatServiceTest
- 4 cavaliers (Vice, Gentrification, Nuisance, Superstition) POI layers
- atomic_csv_writer
- API_CONTRACT.md (Contrat API)
- ChatRequestSchema
- step_archive_hors_master
- data_fusion.py
- MainRegeneratesAWorkingLyonMapTest
- ModelRegressionTest
- RunFusionSelogerLieuTest
- PredictRouteTest
- StepQuartiersTest
- SearchForm.jsx
- annonces_store.py
- test_scraper_extraction_fixtures.py
- Modèle XGBoost par ville (price_predictor_<slug>.pkl, ORA-154)
- CavaliersRouteTest
- RateLimitBehaviorTest
- dependencies
- api.js
- extract_postal_code
- resolve_seloger_lieu
- enrich_annonce_detail
- ErrorBoundary
- MAP_CONTRACT.md (Contrat postMessage carte)
- resolve_quartier_filter
- chat
- detail_cavaliers
- match_quartier
- test_chat_service.py
- test_generate_map.py
- File Structure
- PruneDeadMapListingsTest
- QuartierStatsRequestSchema
- test_clean_immo_steps.py
- LoadLayersConfigTest
- File Structure
- clean_immo.py
- CheckUrlStatusBrowserTest
- rollback_model.py
- extract_type
- ReportPdfRouteTest
- BuildImmoPopupHtmlTest
- PanelNav.jsx
- computeHomeStats
- computeQuartierOptions
- decide_promotion
- scraper_seloger.py
- generate_map.py (carte Folium)
- data_versioning.py
- clean_price_integer
- clean_surface
- resolve_quartier
- DedoublonnerTest
- BuildCavalierMarkersScriptTest
- CheckUrlStatusTest
- scripts
- MemoryStorage
- Plan: non-destructive dead-listing cleanup (ORA-134 bis)
- VerifyAnnoncesTest
- GetChromeDriverOptionsTest
- train_model.py
- RuntimeConfigTest
- package.json
- Tests d'extraction par fixtures HTML (ORA-19)
- POST /api/annonces/<id>/click
- format_description
- fetch_lyon_arrondissements.py
- verify_annonces
- HealthRouteTest
- GeocodingJitterTest
- ResolveLilleQuartierHintTest
- StepFeaturesTest
- StepPruneExpiredTest
- WriteMapMetadataTest
- SanitizeListingUrlTest
- LilleQuartiersGeojsonTest
- QuartierAmbigu.jsx
- fetch_lille_quartiers.py
- ChatRouteTest
- QuartierHistoriqueRouteTest
- BuildShapesFromCavaliersTest
- MatchQuartierLilleTest
- StepSyncAnnoncesStoreTest
- load_existing_rows
- _fetch_all_annonces
- CavalierIconHtmlTest
- ComputeLayerCountsTest
- LoadGeojsonFileTest
- CavaliersDetail.jsx
- HomeOverview.jsx
- get_db_connection
- geocodage.py
- is_context_safe
- ListingsRouteTest
- BuildTitreTest
- BuildLayerGroupsScriptTest
- FocusStyleConstantTest
- ScaleScriptTest
- docker-compose service: airflow-init
- archive_model_version
- CheckUrlStatusAsyncTest
- vite.config.js
- site_files_config
- oracle_annonces_dag.py
- oracle_cavaliers_dag.py
- oracle_cleanup_dag.py
- autoprefixer
- Vite Build Tool
- docker-compose service: backend
- eslint-plugin-react-hooks
- eslint-plugin-react-refresh
- globals
- @playwright/test
- tailwindcss
- @testing-library/jest-dom
- @testing-library/user-event
- @types/react
- @types/react-dom
- Generated Folium map for Lille (map_pings_lille_calques)
- Data science deps (pandas, scikit-learn, numpy, scipy, joblib, shapely)
- Flask stack (Flask, flask-cors, flask-limiter, flasgger, pydantic)
- google-genai (Gemini client)
- rapidfuzz (fuzzy matching)
- sentry-sdk[flask]
- weasyprint (PDF export)
- xgboost==2.1.4 pin (ORA-152)
- oracle-network bridge
- Vite frontend HTML shell (fonts Inter/Archivo, ORA-170)
- Frontend README (Vite/React template)
- React Logo (react.svg)
- Legal / ethical decisions (ORA-80 epic)
- XGBoost training keeps archived listings
- Century21 detail page fixture
- Orpi detail page fixture
- Orpi results page fixture
- PAP detail page fixture (synthetic)
- ParuVendu detail page fixture
- ParuVendu h3 card layout fixture
- SeLoger detail page fixture (synthetic)
- Application Security Review (OWASP Top 10) — ORA-69
- OWASP A01: Broken Access Control — risk accepted (ORA-46)
- OWASP A02: Cryptographic Failures — OK
- OWASP A03: Injection — OK
- OWASP A04: Insecure Design — OK
- OWASP A05: Security Misconfiguration — partially corrected
- OWASP A07: Identification and Authentication Failures — risk accepted (ORA-46)
- OWASP A10: Server-Side Request Forgery — OK
- ResolveVillePathsTest

## God Nodes (most connected - your core abstractions)
1. `ChatService` - 51 edges
2. `AnnoncesStoreTest` - 36 edges
3. `build_report_html()` - 25 edges
4. `run_fusion()` - 24 edges
5. `App()` - 22 edges
6. `_geocode()` - 21 edges
7. `retry_with_backoff()` - 20 edges
8. `CavaliersRequestSchema` - 19 edges
9. `ChatServiceTest` - 19 edges
10. `pick_user_agent()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Proxy de tuiles CARTO (services/tile_proxy.py)` --semantically_similar_to--> `Décision ORA-46 : aucune authentification`  [INFERRED] [semantically similar]
  MAP_CONTRACT.md → API_CONTRACT.md
- `ORA-180: geocoding of listing addresses via IGN Geoplateforme` --semantically_similar_to--> `Geocoding of listing addresses (PRIVACY section)`  [INFERRED] [semantically similar]
  LEGAL_DECISIONS.md → PRIVACY.md
- `check_url_status_browser()` --calls--> `looks_like_soft_404()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `recheck_ambiguous()` --calls--> `_fetch_all_annonces()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `Fixture carte Vizzit (announce-card, prix en €)` --conceptually_related_to--> `Décision ORA-93/94 : aucune photo scrapée hébergée`  [AMBIGUOUS]
  scripts/tests/fixtures/vizzit_card_euro.html → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Airflow docker-compose services** — docker_compose_airflow_db, docker_compose_airflow_init, docker_compose_airflow_webserver, docker_compose_airflow_scheduler [EXTRACTED 1.00]
- **Tracking de clic d'annonce (carte et liste vers annonces.db)** — map_contract_annonce_click, api_contract_post_annonce_click, readme_annonces_db, api_contract_direct_redirect_decision [EXTRACTED 1.00]
- **Rayon des cavaliers : API, focus carte, style** — api_contract_get_cavaliers, map_contract_set_focus, map_contract_focus_style, readme_quatre_cavaliers [EXTRACTED 1.00]
- **clean_immo produit master CSV, annonces.db et archive depuis le même dataframe** — readme_clean_immo, readme_master_immo_final_csv, readme_annonces_db, readme_master_archive [EXTRACTED 1.00]
- **OWASP Top 10 (2021) Security Checklist** — security_review_a01_broken_access_control, security_review_a02_crypto_failures, security_review_a03_injection, security_review_a04_insecure_design, security_review_a05_security_misconfiguration, security_review_a06_vulnerable_components, security_review_a07_auth_failures, security_review_a08_integrity_failures, security_review_a09_logging_monitoring, security_review_a10_ssrf [EXTRACTED 1.00]
- **Fonds de carte overlays** — docs_mockups_vue_calques_fonds_de_carte, docs_mockups_vue_calques_metro_lines, docs_mockups_vue_calques_prix_m2_arrondissement, docs_mockups_vue_calques_dark_basemap [INFERRED 0.85]
- **Four cavalier POI layers filtered by radius and shown in legend** — docs_mockups_vue_calques_cavalier_vice, docs_mockups_vue_calques_cavalier_gentrification, docs_mockups_vue_calques_cavalier_nuisance, docs_mockups_vue_calques_cavalier_superstition, docs_mockups_vue_calques_rayon_selector, docs_mockups_vue_calques_map_legend [INFERRED 0.85]

## Communities (221 total, 83 thin omitted)

### Community 0 - "CalquesView.jsx"
Cohesion: 0.05
Nodes (37): CalquesView(), IMMO_KEYS, immoLayerByKey, LYON_LINE_CODES, quartiersLayer, RADIUS_OPTIONS, cavaliersDetail, facteurs (+29 more)

### Community 1 - "record_model_metadata"
Cohesion: 0.20
Nodes (8): load_active_model_metadata(), Lit les métadonnées (`metrics`, `model_version`) du modèle actuellement actif…, Écrit `<model_path>.meta.json`, référençant explicitement la version des…, record_model_metadata(), RecordModelMetadataTest, LoadActiveModelMetadataTest, PromotionGuardTriggersRollbackTest, Reproduit le flux de décision de train_model.py au niveau des fonctions qu'il…

### Community 2 - "monitor_drift.py"
Cohesion: 0.07
Nodes (29): CI Workflow (ci.yml), CI job: backend (pytest), CI job: dependency-scan (pip-audit, npm audit), CI job: deploy (Render deploy hooks, ORA-64), CI job: e2e (Playwright vs vite preview + Flask), CI job: frontend (lint, build, test), CI job: scrapers (pytest, excludes e2e), Model Drift Monitor Workflow (+21 more)

### Community 3 - "localisation_texte.py"
Cohesion: 0.14
Nodes (16): _candidats(), _nom_propre(), Adresse du bien extraite d'un texte libre (ORA-180) : « 52 rue André Bollier ».…, [(adresse, avec_numero)] acceptées dans une phrase brute., _clause_propre(), _evaluer(), extraire_zone(), localiser_par_texte() (+8 more)

### Community 4 - "app.py"
Cohesion: 0.07
Nodes (38): after_request, get_annonce_detail(), get_annonces(), get_cavaliers(), get_chat_rate_limit(), get_cors_origins(), get_default_rate_limits(), get_listings() (+30 more)

### Community 5 - "AnnoncesStoreTest"
Cohesion: 0.05
Nodes (4): AnnoncesStoreTest, ORA-173 : "€/m² croissant" (tri par défaut de la maquette 05) — prix_m2 n'est…, `NULLIF(surface, 0)` -> NULL pour une surface manquante : SQLite trie NULL…, Le frontend envoie le slug de la ville active ("lyon"), la colonne stocke…

### Community 6 - "complete_data_extraction.py"
Cohesion: 0.06
Nodes (29): advert_id(), coordinates_from_api_response(), extract_coordinates_from_html(), fetch_api_coordinates(), get_gps_from_url(), process_row(), URL de recherche Vizzit d'une ville (scraping_config.json), sans tranche de…, Identifiant d'annonce Vizzit : dernier segment de l'URL de la fiche. (+21 more)

### Community 7 - "recheck_dead_annonces.py"
Cohesion: 0.10
Nodes (19): prune_dead_map_listings(), Nettoyage ponctuel des annonces mortes dans master_immo_final.csv + carte…, Écrit dans un fichier temporaire puis remplace `path` via os.replace (atomique)…, Vérifie chaque url de `csv_path` (HTTP puis navigateur headless pour les…, _write_csv_atomically(), check_url_status_browser(), looks_like_challenge_page(), looks_like_valid_listing() (+11 more)

### Community 8 - "scraper_orpi.py"
Cohesion: 0.08
Nodes (23): _fetch_geocodage(), geocode_adresse(), load_page(), checkpoint(), load_page(), parse_quartier(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Nom de quartier seul depuis le libellé de localisation Orpi ("Lyon 8-… (+15 more)

### Community 9 - "build_feature_row"
Cohesion: 0.11
Nodes (16): build_feature_row(), compute_distance_features(), haversine_distance_m(), normalize_type_bien(), normalize_type_local(), Construit le vecteur de features attendu par le modèle à partir du payload…, Normalise un type de bien utilisateur (T1, studio, T4+...) vers une catégorie…, Normalise le type de bien brut (Appartement/Maison/Studio), 'Appartement' par… (+8 more)

### Community 10 - "generate_map.py"
Cohesion: 0.09
Nodes (31): build_bridge_message_script(), build_cavalier_markers_script(), build_immo_popup_html(), build_immo_tooltip_html(), build_layer_groups_script(), build_scale_script(), cavalier_icon_html(), compute_layer_counts() (+23 more)

### Community 12 - "build_report_html"
Cohesion: 0.11
Nodes (15): build_report_html(), _ecart_html(), _ecart_pct(), _escape(), _format_m2(), _format_price(), _quartile_stats(), Rend le rapport d'estimation en PDF (bytes), via WeasyPrint (ORA-121). (+7 more)

### Community 13 - "App.jsx"
Cohesion: 0.11
Nodes (14): App(), renderEstimationView(), renderScanView(), renderSummaryChip(), makePanelFallback(), MOBILE_TABS, useIsDesktop(), PanelSheet() (+6 more)

### Community 14 - "RowsToVerifyTest"
Cohesion: 0.12
Nodes (9): Integration test: mix of all statuses with various verification timestamps., Test the date-arithmetic logic of _rows_to_verify (TTL/staleness detection)., Row with statut='active' and derniere_verification_http older than ttl_days →…, Row with statut='active' and derniere_verification_http within ttl_days → NOT…, Row with statut='active' and missing/empty derniere_verification_http →…, Row with statut='active' and NaT derniere_verification_http → included., Row with statut='a_verifier' regardless of derniere_verification_http → always…, Row with statut='inactive' → never included (even with stale/missing timestamp). (+1 more)

### Community 15 - "compute_price_history"
Cohesion: 0.28
Nodes (6): compute_price_history(), _filter_quartier(), Calcule l'évolution du prix moyen/m² pour `quartier` à travers tous les…, ComputePriceHistoryTest, ORA-110 : même matching partagé (fuzzy) que /api/quartier-stats, au lieu d'un…, _write_manifest()

### Community 16 - "test_scraper_utils.py"
Cohesion: 0.11
Nodes (10): find_first(), Décide si la pagination d'un scraper doit continuer après une page où…, Essaie chaque sélecteur CSS de `selectors` dans l'ordre sur `element` et…, should_continue_pagination(), BlankShortDescriptionsTest, CleanDescriptionTest, FakeElement, FindFirstTest (+2 more)

### Community 17 - "GetTileTest"
Cohesion: 0.07
Nodes (13): DataLoader, Charge le CSV en mémoire et applique un nettoyage de base., Renvoie le DataFrame brut., clean_input_data(), format_prediction_response(), guess_room_count_smart(), Nettoie les données entrantes., Devine le type de logement (T1, T2...) basé sur la surface si l'information est… (+5 more)

### Community 18 - "scraper_vizzit.py"
Cohesion: 0.11
Nodes (26): apply_price_band(), build_page_url(), clean_card_text(), decode_data_o_link(), est_en_euros(), find_attr(), find_text(), find_text_content() (+18 more)

### Community 19 - "_geocode"
Cohesion: 0.16
Nodes (6): AdresseGeocodeeTest, _geocode(), _geocodeur(), OrdrePrioriteLocalisationTest, Une annonce, colonnes par défaut vides ; renvoie le df après step_geocoding., _sans_reseau()

### Community 20 - "test_playwright_selectors.py"
Cohesion: 0.12
Nodes (19): expectedFailure, assert_selector_canary(), Century21SelectorCanaryTest, find_cards(), find_first_locator_text(), new_page(), OrpiSelectorCanaryTest, PapSelectorCanaryTest (+11 more)

### Community 21 - "AnnonceCard.jsx"
Cohesion: 0.14
Nodes (20): AnnonceCard(), AnnonceIllustration(), formatPrice(), ILLUSTRATION_BY_CATEGORY, baseAnnonce, formatM2(), formatPrice(), formatShortDate() (+12 more)

### Community 22 - "CavaliersRadiusServiceTest"
Cohesion: 0.11
Nodes (9): Raccourci pratique (tests) : l'entrée de `result["cavaliers_detail"]` dont…, CavaliersRadiusServiceNoRadiusTest, CavaliersRadiusServiceTest, Le fichier Lille fixture a un BOM (utf-8-sig) : si le service le lisait en…, Rayon « Aucun » (ORA-183, v3) : totaux à l'échelle de la ville, sans filtre de…, 3 lieux Vice à Lyon (Le Bar Proche 100m, Le Bar Loin 800m, Kebab King 400m) :…, Lille (fixture LILLE_ROWS) n'a que du Vice : à l'échelle d'une ville, une…, Le Bar Loin (800m) et l'École du Coin (800m) n'entrent que dans le rayon 1000m… (+1 more)

### Community 23 - "merge_cavaliers"
Cohesion: 0.13
Nodes (14): get_cavaliers_data(), merge_cavaliers(), Lit le nom de la ville active (`villes.<ville_active>.nom`) depuis…, Résout le nom d'affichage d'une ville depuis son slug, indépendamment de…, Fusionne les cavaliers déjà connus avec les cavaliers fraîchement extraits.…, Récupère la liste complète des lieux pour chaque catégorie et fusionne avec le…, resolve_active_city_name(), resolve_city_name() (+6 more)

### Community 24 - "prepare_new_city.py"
Cohesion: 0.17
Nodes (14): build_config_skeleton(), build_report(), classify(), fetch_arrondissements(), fetch_commune(), fetch_shared_postal_codes(), _get(), main() (+6 more)

### Community 25 - "clean_immo.py"
Cohesion: 0.09
Nodes (38): build_shapes_from_cavaliers(), build_titre(), clean_zipcode(), determine_type_local(), extract_seloger_quartier_slug(), get_nearest_distance_and_count(), get_point_for_zipcode(), get_point_in_circle() (+30 more)

### Community 26 - "CavaliersRadiusService"
Cohesion: 0.13
Nodes (12): phrase_for(), Phrase concrète pour un `poi` connu (POI_PHRASES) ou, à défaut, une phrase…, CavaliersRadiusService, _parse_categorie_cavalier(), Vice - Sex-shop" -> ("vice", "sex-shop") — même normalisation que…, Calcule en direct (haversine, sans passer par les colonnes précalculées à 500m…, Lit un CSV cavaliers_<ville>.csv en utf-8-sig (BOM déjà rencontré sur le…, Une catégorie, rayon "Aucun" : total et détail par sous-catégorie sur… (+4 more)

### Community 27 - "CavaliersRequestSchema"
Cohesion: 0.14
Nodes (6): CavaliersRequestSchema, La query string GET ne transporte que des chaînes : "none" (toute casse) est la…, CavaliersRequestSchemaTest, Rayon "Aucun" (ORA-183, v3) : le sélecteur segmenté envoie la valeur "none"…, Non-régression : seul un "none" explicite retire le rayon — un appel qui omet…, field_validator

### Community 28 - "get_connection"
Cohesion: 0.12
Nodes (21): log_annonce_click(), Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le…, Alimente la table SQLite `annonces` (services/annonces_store.py) à partir du…, step_sync_annonces_store(), count_clicks(), get_annonce_by_id(), get_annonce_by_url(), get_connection() (+13 more)

### Community 29 - "ChatOracle.jsx"
Cohesion: 0.28
Nodes (8): ALL_TYPES, buildChatContext(), ChatOracle(), DEFAULT_MESSAGES, describeChatError(), ApiError, loadChatHistory(), saveChatHistory()

### Community 30 - "scraper_utils.py"
Cohesion: 0.13
Nodes (19): fetch_description(), fetch_page(), find_description_bs4(), find_image_bs4(), find_lien_partiel(), Lien de l'annonce : le titre s'il est un <a>, sinon le premier lien…, Équivalent BeautifulSoup de `selenium_description_fetcher` : premier texte de…, Description libre d'une annonce ParuVendu ("" si l'annonce n'existe plus ou n'a… (+11 more)

### Community 31 - "LoggingConfigTest"
Cohesion: 0.10
Nodes (7): configure_logging(), init_sentry(), Configuration centralisée de l'observabilité applicative du backend (ORA-63).…, Configure le logger racine du process avec un format structuré et un niveau…, Initialise sentry-sdk pour capturer automatiquement les exceptions non gérées…, LoggingConfigTest, Vérifie le logger structuré centralisé (ORA-63) : niveau par défaut, prise en…

### Community 32 - "AdresseDuBienTest"
Cohesion: 0.20
Nodes (5): extraire_adresse(), localiser_adresse(), (adresse | None, raison courte). Contradiction = None., Premier texte (dans l'ordre donné) qui décide ; une contradiction est…, AdresseDuBienTest

### Community 33 - "pick_user_agent"
Cohesion: 0.15
Nodes (10): Re-teste chaque annonce de `db_path` en HTTP, puis escalade au navigateur…, recheck_ambiguous(), load_site_config(), pick_proxy(), pick_user_agent(), Choisit un proxy au hasard dans le pool configuré (ORA-18), désactivé par…, Charge la config de la ville active (URL de recherche, paramètre de pagination)…, Choisit un User-Agent réaliste au hasard dans le pool configuré (rotation,… (+2 more)

### Community 34 - "archive_stale_rows"
Cohesion: 0.15
Nodes (6): archive_stale_rows(), Déplace de `rows_by_lien` vers `<output>_archive.csv` les annonces non revues…, ArchiveStaleRowsTest, EnrichDescriptionsTest, _Logger, ORA-161 : visite des pages détail plafonnée, sans jamais insister en cas de…

### Community 35 - "summarize_cavaliers"
Cohesion: 0.22
Nodes (8): list_poi_types(), Introspecte les colonnes `dist_<catégorie>_<poi>` réellement présentes dans…, Résume les 4 "Cavaliers" (Vice, Gentrification, Nuisance, Superstition) pour un…, summarize_cavaliers(), ListPoiTypesTest, Non-régression : /api/quartier-stats et le PDF n'appellent summarize_cavaliers…, _row(), SummarizeCavaliersTest

### Community 37 - "BuildBridgeMessageScriptTest"
Cohesion: 0.11
Nodes (7): BuildBridgeMessageScriptTest, Contrat postMessage carte (ORA-125) : la carte générée ne doit traiter un…, Remplace l'ancienne correspondance par texte de <label> (fragile, cassait dès…, ORA-105 : recentrage sur la bounding-box des résultats filtrés., L'URL du proxy de tuiles arrive au runtime (dépend du déploiement) : validée…, v3 (ORA-183) : tous les pings d'un cavalier actif restent visibles, rayon actif…, Un second SET_FOCUS (nouveau rayon) ne doit pas laisser l'ancien cercle affiché…

### Community 38 - "useAnnonceDetail.js"
Cohesion: 0.17
Nodes (13): AnnoncesList(), loadAnnonces(), SORT_OPTIONS, useAnnonceDetail(), useFavorites(), deriveSource(), getTypeCategory(), KNOWN_CATEGORIES (+5 more)

### Community 39 - "test_data_fusion.py"
Cohesion: 0.15
Nodes (7): CP de repli pour une ville (cf. extract_postal_code). Fail-fast plutôt que de…, resolve_default_cp(), LoadDeclaredVillesTest, PostalCodeFromUrlTest, Le fichier GPS Vizzit (complete_data_extraction.py) n'a pas de colonne `Image`…, ResolveDefaultCpTest, RunFusionVizzitImageTest

### Community 40 - "run_fusion"
Cohesion: 0.18
Nodes (8): Fusionne les CSV scrapés en base_de_donnees_immo_complet.csv. Par défaut…, run_fusion(), ORA-134 : la colonne DerniereVue des scrapers doit survivre à la fusion sous le…, ORA-161 : la description libre scrapée sur la page détail (colonne…, ORA-153 : chaque DAG annonces tourne désormais indépendamment par ville.…, RunFusionDateDernierScanTest, RunFusionDescriptionDetailTest, RunFusionPerVilleTest

### Community 41 - "normalize_text"
Cohesion: 0.24
Nodes (6): compact_text(), normalize_text(), searchable_text(), CompactTextTest, NormalizeTextTest, SearchableTextTest

### Community 42 - "QuartierStatsRouteTest"
Cohesion: 0.11
Nodes (6): QuartierStatsRouteTest, ORA-110 : le endpoint utilise désormais le matching partagé (fuzzy) au lieu…, ORA-111 : message différencié aucun résultat vs quartier ambigu., ORA-111 : suggestions renvoyées quand plusieurs quartiers sont proches., ORA-167 : min/P25/médiane/P75/max calculés sur tous les biens filtrés, pas sur…, ORA-122/ORA-128/ORA-177 : échantillon de biens comparables réels, pour le…

### Community 43 - "step_flag_expired"
Cohesion: 0.18
Nodes (5): `sur_carte` : True si l'annonce a été revue lors du dernier scrape de son…, Fusionne `df` (résultat frais de data_fusion.py) avec le…, step_flag_expired(), _vu_au_dernier_scrape(), StepFlagExpiredTest

### Community 44 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, devDependencies, eslint, @eslint/js, jsdom, postcss, @testing-library/react (+9 more)

### Community 45 - "AnnonceDetailModal.jsx"
Cohesion: 0.33
Nodes (6): AnnonceDetailContent(), CATEGORY_STYLES, formatM2(), formatPrice(), AnnonceDetailModal(), detail

### Community 46 - "MergeAllVillesTest"
Cohesion: 0.33
Nodes (4): merge_all_villes(), L'Oracle des Loyers — Fusion des cavaliers par ville Concatène les…, MergeAllVillesTest, ORA-153 : avant ce script, rien ne produisait cavaliers_all.csv automatiquement…

### Community 49 - "4 cavaliers (Vice, Gentrification, Nuisance, Superstition) POI layers"
Cohesion: 0.13
Nodes (16): Mockup: Vue Calques (Calques & 4 cavaliers), Cavalier Gentrification, Cavalier Nuisance, Cavalier Superstition, Cavalier Vice (Bar, Tabac, CBD Shop, Kebab), Couleur des annonces toggle (Écart / Type), Dark CARTO / OpenStreetMap basemap (Lyon, Ainay T2 context), Fonds de carte toggles (Métro & stations, Funiculaires, €/m² par arrondissement) (+8 more)

### Community 50 - "atomic_csv_writer"
Cohesion: 0.18
Nodes (8): atomic_csv_writer(), Écrit dans un fichier temporaire à côté de `output_path` et ne remplace ce…, checkpoint(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, checkpoint(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, checkpoint(), AtomicCsvWriterTest

### Community 51 - "API_CONTRACT.md (Contrat API)"
Cohesion: 0.19
Nodes (15): API_CONTRACT.md (Contrat API), Résolution floue du quartier (text_matching.py), GET /api/annonces/<id>, GET /api/cavaliers, Décision ORA-46 : aucune authentification, POST /api/chat (Immotep), POST /api/quartier-stats, POST /api/report/pdf (WeasyPrint) (+7 more)

### Community 52 - "ChatRequestSchema"
Cohesion: 0.18
Nodes (10): ChatRequestSchema, ComparableSchema, FacteurSchema, PdfReportRequestSchema, PredictRequestSchema, PriceHistoryPointSchema, Schémas de validation des payloads pour les routes Flask actives (/api/chat,…, ChatRequestSchemaTest (+2 more)

### Community 53 - "step_archive_hors_master"
Cohesion: 0.21
Nodes (7): load_sites_actifs(), Retire les colonnes `nom.1`, `nom.2`… que pandas crée à la lecture d'un CSV…, Clés des sites actifs (`sites_actifs` de scraping_config.json, ex. {'vizzit',…, Le master ne garde que les annonces scrapées au dernier run de leur (ville,…, _sans_colonnes_dupliquees(), step_archive_hors_master(), StepArchiveHorsMasterTest

### Community 54 - "data_fusion.py"
Cohesion: 0.16
Nodes (14): dedoublonner(), _distance_m(), load_sites_actifs(), normalize_lieu(), postal_code_from_url(), Clés des sites actifs (`sites_actifs` de scraping_config.json), ou None si…, Début du texte libre de l'annonce, normalisé (lettres/chiffres seuls), ou None…, Même prix/surface/type/CP (déjà vrai ici) ET une preuve d'identité : même début… (+6 more)

### Community 55 - "MainRegeneratesAWorkingLyonMapTest"
Cohesion: 0.13
Nodes (5): MainRegeneratesAWorkingLyonMapTest, Test d'intégration (données réelles versionnées, backend/data/) : exécute…, Ordre textuel : oracleCavalierMarkers doit être à l'intérieur du callback…, Un seul marker par lieu (folium.Marker/DivIcon, cf. cavalier_icon_html) — plus…, ORA-183 (v3) : une seule légende (React, MapComponent) — celle générée côté…

### Community 56 - "ModelRegressionTest"
Cohesion: 0.17
Nodes (8): ModelRegressionTest, PredictEndpointRegressionTest, _prepare_features(), ORA-154 : un modèle XGBoost distinct par ville plutôt que `ville` en feature…, Non-régression explicite du bug corrigé par ORA-30 : /api/predict renvoyait…, Reproduit exactement le prétraitement de train_model.py (ORA-154, ORA-155),…, Remplace backend/scripts/test_prediction.py (script manuel, échantillon…, VilleExcludedFromFeaturesTest

### Community 58 - "PredictRouteTest"
Cohesion: 0.14
Nodes (4): PredictRouteTest, ORA-154 : la panne d'un modèle ne doit plus dégrader toutes les villes — seule…, ORA-152 : un modèle qui prédit un loyer négatif (ex. pickle XGBoost désérialisé…, Un loyer exactement nul n'est pas plus plausible qu'un loyer négatif.

### Community 60 - "SearchForm.jsx"
Cohesion: 0.30
Nodes (8): formatEuros(), SearchForm(), splitAtMatch(), quartierOptions, TYPE_FILTERS, normalizeText(), loadRecentSearches(), pushRecentSearch()

### Community 61 - "annonces_store.py"
Cohesion: 0.19
Nodes (9): check_url_status(), looks_like_soft_404(), Nettoyage ponctuel des annonces mortes dans annonces.db (ORA-134). Le pipeline…, True si `html_text` contient un des `SOFT_404_PATTERNS` (insensible à la casse)., Vérifie une url en direct. Renvoie True (confirmée morte : 404/410, ou soft-404…, check_url_status_async(), Vérification HTTP asynchrone des annonces à statut incertain (ORA-134 bis, tier…, Version asynchrone de check_url_status (prune_dead_annonces.py) : même contrat… (+1 more)

### Community 62 - "test_scraper_extraction_fixtures.py"
Cohesion: 0.05
Nodes (21): bs4_first_attr(), bs4_first_text(), bs4_select_first_matching(), Century21ExtractionTest, DetailDescriptionExtractionTest, _FakeElement, load_fixture(), OrpiExtractionTest (+13 more)

### Community 63 - "Modèle XGBoost par ville (price_predictor_<slug>.pkl, ORA-154)"
Cohesion: 0.17
Nodes (13): Niveau de confiance (Faible/Moyenne/Élevée), GET /api/health, POST /api/predict, POST /api/quartier-historique, DAG oracle_annonces_pipeline (hebdomadaire), DAG oracle_cavaliers_pipeline_<slug> (mensuel, par ville), cavaliers_all.csv, Versioning des snapshots de données (data_versioning.py) (+5 more)

### Community 65 - "RateLimitBehaviorTest"
Cohesion: 0.15
Nodes (4): RateLimitBehaviorTest, RateLimitConfigTest, ORA-118 : le frontend a besoin de X-RateLimit-Remaining pour afficher un…, Sans Access-Control-Expose-Headers, fetch() côté frontend ne peut pas lire ces…

### Community 66 - "dependencies"
Cohesion: 0.15
Nodes (13): dependencies, leaflet, react, react-dom, react-leaflet, react-markdown, remark-gfm, leaflet (+5 more)

### Community 67 - "api.js"
Cohesion: 0.20
Nodes (12): defaultDetail, defaultFacteurs, renderCavaliersRadius(), useCavaliersRadius(), api, API_URL, apiFetchOptions(), classifyResponseError() (+4 more)

### Community 68 - "extract_postal_code"
Cohesion: 0.29
Nodes (3): extract_postal_code(), Normalise le CP (69XXX ou 59XXX). `default_cp` est le repli utilisé quand aucun…, ExtractPostalCodeTest

### Community 69 - "resolve_seloger_lieu"
Cohesion: 0.27
Nodes (4): CP réel déduit du champ `Lieu` de SeLoger, ou du premier segment d'`Infos`…, resolve_seloger_lieu(), ORA-71 POC follow-up : le champ Lieu de SeLoger contient parfois une vraie…, ResolveSelogerLieuTest

### Community 70 - "enrich_annonce_detail"
Cohesion: 0.35
Nodes (4): enrich_annonce_detail(), ORA-174 (maquette 06, "Fiche annonce") : enrichit une annonce issue…, _dataset_row(), EnrichAnnonceDetailTest

### Community 72 - "MAP_CONTRACT.md (Contrat postMessage carte)"
Cohesion: 0.20
Nodes (12): Procédure : ajouter un type de message, Message FLY_TO, Message FLY_TO_BOUNDS, FOCUS_STYLE (mise en avant rayon), Piège ordre de rendu Folium (window load), MAP_CONTRACT.md (Contrat postMessage carte), mapLayers.config.json (config partagée des calques, ORA-130), Légende React (MapLegend.jsx) (+4 more)

### Community 73 - "resolve_quartier_filter"
Cohesion: 0.31
Nodes (5): Résolution d'une recherche utilisateur (texte libre) en un sous-ensemble du…, Sous-ensemble de `df` correspondant à la recherche `quartier_input`, et les…, resolve_quartier_filter(), _df(), ResolveQuartierFilterTest

### Community 74 - "chat"
Cohesion: 0.18
Nodes (12): chat(), get_map_tile(), Proxy des tuiles CARTO du fond de carte : la clé API reste côté serveur…, Chatbot Immotep : réponse groundée sur les données réelles, ou via Gemini. ---…, build_upstream_url(), get_tile(), is_valid_tile(), Proxy des tuiles du fond de carte CARTO. CARTO exige une clé API sur ses… (+4 more)

### Community 75 - "detail_cavaliers"
Cohesion: 0.27
Nodes (5): detail_cavaliers(), Détail complet des 4 Cavaliers pour un sous-ensemble d'annonces (ORA-172,…, DetailCavaliersTest, ORA-172 : contrairement à summarize_cavaliers (1 phrase, le POI dominant), le…, Reproduit "Rien dans le rayon. Pompes funèbres les plus proches à 573 m."…

### Community 76 - "match_quartier"
Cohesion: 0.29
Nodes (4): match_quartier(), Fait correspondre `query` (texte libre, éventuellement fautif ou noyé dans une…, MatchQuartierTest, ORA-109 : tolérance aux fautes de frappe sur les quartiers connus.

### Community 77 - "test_chat_service.py"
Cohesion: 0.20
Nodes (4): ExtractLocationsFuzzyMatchingTest, FakeClient, FakeModels, ORA-109 : la recherche de quartier tolère les fautes de frappe.

### Community 78 - "test_generate_map.py"
Cohesion: 0.17
Nodes (4): BuildImmoTooltipHtmlTest, FilterByVilleTest, Aucune clé, ni URL CARTO, dans la carte générée (fichier versionné)., TileLayerNeverEmbedsAKeyTest

### Community 79 - "File Structure"
Cohesion: 0.18
Nodes (10): File Structure, Global Constraints, Nettoyage non-destructif des annonces mortes — Implementation Plan, Prochaines étapes après ce plan (hors scope, à netifier séparément si besoin), Self-Review, Task 1: Migration DB non-destructive + statut dans `annonces_store.py`, Task 2: Fusion préservante dans `clean_immo.py` (remplace le drop TTL), Task 3: Vérificateur HTTP asynchrone (`verify_annonces_async.py`) (+2 more)

### Community 82 - "test_clean_immo_steps.py"
Cohesion: 0.20
Nodes (3): GetPointForZipcodeZonesLimitrophesTest, StepIdsTest, StepTypesTest

### Community 83 - "LoadLayersConfigTest"
Cohesion: 0.20
Nodes (4): LoadLayersConfigTest, ORA-130 : la liste des calques (nom Folium/TOGGLE_LAYER, visibilité par défaut,…, Non-régression ORA-130 : le refactor ne doit rien changer à l'état initial des…, Source unique (mapLayers.config.json) couleur+forme, lue à la fois par ce…

### Community 84 - "File Structure"
Cohesion: 0.20
Nodes (9): File Structure, Global Constraints, Note pour la suite (hors scope de ce plan), Self-Review, Séparation affichage carte / archive ML Implementation Plan, Task 1: `annonces_store.py` — statut 2-états, premiere_vue/derniere_vue, table `historique_prix`, Task 2: `clean_immo.py` — diff de scrape simplifié (2 états) + retrait du tier HTTP, Task 3: Filtrage affichage (carte + API) + vocabulaire XGBoost (+1 more)

### Community 85 - "clean_immo.py"
Cohesion: 0.24
Nodes (10): ORA-180: geocoding of listing addresses via IGN Geoplateforme, annonces_store.py changes (premiere_vue, derniere_vue, record_price_observation), historique_prix table (append-only price history), price_evolution.py compute_price_trend, step_flag_expired (clean_immo.py, 2-state merge), step_flag_expired (3-state preserving merge), Geocoding of listing addresses (PRIVACY section), clean_immo.py (+2 more)

### Community 86 - "CheckUrlStatusBrowserTest"
Cohesion: 0.09
Nodes (4): CheckUrlStatusBrowserTest, LooksLikeChallengePageTest, LooksLikeValidListingTest, RecheckAmbiguousTest

### Community 87 - "rollback_model.py"
Cohesion: 0.17
Nodes (6): Revenir à une version antérieure du modèle price_predictor_<ville>.pkl sans…, price_predictor_<ville>.pkl pour le slug donné — un modèle distinct par ville…, resolve_model_path(), ORA-154 : un modèle distinct par ville — price_predictor_<ville>.pkl, pas un…, ResolveModelPathTest, RollbackModelTest

### Community 88 - "extract_type"
Cohesion: 0.36
Nodes (3): extract_type(), Détermine le type de bien (Maison, Appartement, Studio, Coloc)., ExtractTypeTest

### Community 89 - "ReportPdfRouteTest"
Cohesion: 0.22
Nodes (3): ORA-122 : enrichissement du rapport (historique de prix, biens comparables)., ORA-177 : champs ajoutés pour aligner le rapport sur la maquette 09 (case…, ReportPdfRouteTest

### Community 91 - "PanelNav.jsx"
Cohesion: 0.33
Nodes (4): ICON_PROPS, icons, PanelNav(), PANEL_VIEWS

### Community 92 - "computeHomeStats"
Cohesion: 0.44
Nodes (7): arrondissementLabel(), computeHomeStats(), groupMedianPrixM2(), isFiniteNumber(), isLocated(), median(), listings

### Community 93 - "computeQuartierOptions"
Cohesion: 0.39
Nodes (7): arrondissementLabel(), computeQuartierOptions(), isFiniteNumber(), isLocated(), median(), mostFrequent(), listings

### Community 94 - "decide_promotion"
Cohesion: 0.31
Nodes (4): decide_promotion(), Décide si un modèle nouvellement entraîné doit remplacer le modèle actif.…, DecidePromotionTest, ORA-34 : un ré-entraînement automatique (DAG Airflow quotidien) ne doit jamais…

### Community 95 - "scraper_seloger.py"
Cohesion: 0.20
Nodes (8): checkpoint(), load_page(), parse_title_attribute(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Parse 'Type - Lieu - Prix - Infos' format. Returns None if format unrecognized., canonical_url(), Retire la query string et le fragment d'une URL d'annonce. Régression réelle…, SeLoger scraper test fixture (HTML)

### Community 96 - "generate_map.py (carte Folium)"
Cohesion: 0.29
Nodes (8): GET /api/listings, folium, ORA-67/93: scraper compliance with robots.txt/CGU, ORA-94: photo hosting decision (superseded by ORA-134 hotlink), Display filter statut=active (api/listings, generate_map), generate_map.py (carte Folium), master_immo_final.csv (Gold Standard), Décision ORA-106 : pré-rendu statique de la carte

### Community 97 - "data_versioning.py"
Cohesion: 0.33
Nodes (4): Archive un instantané content-addressé de `csv_path` dans `snapshots_dir` et…, _sha256_of_file(), snapshot_dataset(), SnapshotDatasetTest

### Community 98 - "clean_price_integer"
Cohesion: 0.39
Nodes (3): clean_price_integer(), Convertit en entier (supprime €, cc, espaces, points)., CleanPriceIntegerTest

### Community 99 - "clean_surface"
Cohesion: 0.39
Nodes (3): clean_surface(), Extrait le nombre avant 'm2'., CleanSurfaceTest

### Community 100 - "resolve_quartier"
Cohesion: 0.36
Nodes (4): Résout `query` vers le libellé canonique d'un quartier de `known_quartiers`, ou…, resolve_quartier(), ORA-110 : point d'entrée unique utilisé par /api/quartier-stats, /api/quartier-…, ResolveQuartierTest

### Community 102 - "BuildCavalierMarkersScriptTest"
Cohesion: 0.25
Nodes (4): BuildCavalierMarkersScriptTest, Référence JS de chaque marker de cavalier (variable Folium + lat/lng + famille)…, SET_FOCUS (build_bridge_message_script) lit `entry.color` pour dessiner le halo…, Doit rester accessible une fois englobé dans une fonction (le callback…

### Community 103 - "CheckUrlStatusTest"
Cohesion: 0.10
Nodes (3): CheckUrlStatusTest, LooksLikeSoft404Test, PruneDeadAnnoncesTest

### Community 104 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, test, test:e2e, test:watch

### Community 106 - "Plan: non-destructive dead-listing cleanup (ORA-134 bis)"
Cohesion: 0.32
Nodes (8): Plan: separate map display from ML archive (ORA-144), Two-state status active/archivee driven by scrape diff, Plan: non-destructive dead-listing cleanup (ORA-134 bis), Non-destructive cleanup principle (never delete rows), oracle_cleanup_pipeline Airflow DAG (daily), Three-state status active/a_verifier/inactive, annonces_store.update_statut, verify_annonces_async.py (aiohttp HTTP verifier)

### Community 109 - "train_model.py"
Cohesion: 0.36
Nodes (7): load_declared_villes(), Villes déclarées dans scraping_config.json (ORA-71) : ajouter une ville au JSON…, Restaure `model_path` à la version archivée `model_version`. `versions_dir`…, rollback_to(), Entraîne, évalue et (si le garde-fou de régression le permet) promeut un modèle…, resolve_ville_nom(), train()

### Community 113 - "package.json"
Cohesion: 0.29
Nodes (6): name, overrides, vite, private, type, version

### Community 114 - "Tests d'extraction par fixtures HTML (ORA-19)"
Cohesion: 0.29
Nodes (7): CD Render + dependency-scan (ORA-64/65), Décision ORA-93/94 : aucune photo scrapée hébergée, Canari Playwright des sélecteurs (ORA-20/21), Décision revue robots.txt (ORA-67), Tests d'extraction par fixtures HTML (ORA-19), Scraper Vizzit (scraper_vizzit.py), Fixture carte Vizzit (announce-card, prix en €)

### Community 115 - "POST /api/annonces/<id>/click"
Cohesion: 0.40
Nodes (6): Décision ORA-86 : redirection directe sans modal, GET /api/annonces, POST /api/annonces/<id>/click, Message ANNONCE_CLICK (iframe → React), Vérification d'origine postMessage (ORA-125), annonces.db (store SQLite)

### Community 116 - "format_description"
Cohesion: 0.47
Nodes (3): format_description(), Nettoie la description pour l'affichage final., FormatDescriptionTest

### Community 117 - "fetch_lyon_arrondissements.py"
Cohesion: 0.53
Nodes (5): fetch_arrondissement_boundary(), main(), ordinal_label(), Récupère une fois les polygones des 9 arrondissements de Lyon (Nominatim/ OSM)…, Récupère le polygone GeoJSON d'un arrondissement de Lyon via Nominatim.

### Community 118 - "verify_annonces"
Cohesion: 0.33
Nodes (6): Vérifie les annonces éligibles (cf. `_rows_to_verify`) et met à jour leur…, Sélectionne les lignes à vérifier : statut a_verifier, ou active avec…, _rows_to_verify(), verify_annonces(), Met à jour uniquement le statut (et la date de dernière vérification HTTP)…, update_statut()

### Community 119 - "HealthRouteTest"
Cohesion: 0.33
Nodes (3): HealthRouteTest, ORA-154 : un modèle distinct par ville — /api/health expose l'état de chacun…, ORA-171 : "entraîné sur N annonces" (maquette 03) doit venir du dernier run…

### Community 127 - "QuartierAmbigu.jsx"
Cohesion: 0.47
Nodes (4): formatEuros(), QuartierAmbigu(), ambiguous, quartierOptions

### Community 128 - "fetch_lille_quartiers.py"
Cohesion: 0.50
Nodes (4): fetch_boundary(), main(), Récupère une fois les contours réels des quartiers de Lille (+ Lomme,…, Renvoie une Feature GeoJSON polygonale pour `nom`, ou None si OSM n'a pas de…

### Community 134 - "load_existing_rows"
Cohesion: 0.39
Nodes (3): load_existing_rows(), Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble…, LoadExistingRowsTest

### Community 135 - "_fetch_all_annonces"
Cohesion: 0.33
Nodes (6): _fetch_all_annonces(), prune_dead_annonces(), Snapshot complet (id, url, titre) pris avant toute suppression : évite le bug…, Vérifie chaque annonce de `db_path` (DEFAULT_DB_PATH si None) et supprime…, delete_annonce(), Retire une annonce (et ses clics associés) du store, par `url` ou `annonce_id`…

### Community 139 - "CavaliersDetail.jsx"
Cohesion: 0.50
Nodes (3): CATEGORY_STYLES, CavaliersDetail(), detail

### Community 140 - "HomeOverview.jsx"
Cohesion: 0.60
Nodes (4): formatEuros(), HomeOverview(), numberFmt, QuartierRow()

### Community 142 - "get_db_connection"
Cohesion: 0.50
Nodes (4): get_db_connection(), init_db(), Initialise la table 'annonces' si elle n'existe pas., Crée une connexion à la base de données.

### Community 143 - "geocodage.py"
Cohesion: 0.47
Nodes (5): _charger_cache(), geocoder(), _interroger(), Géocodage d'une adresse de Lyon via la Géoplateforme de l'IGN (ORA-180).…, {'lat', 'lon', 'precision': 'numero'|'rue', 'cp'} ou None ('lyon' ou 'lille').…

### Community 145 - "is_context_safe"
Cohesion: 0.67
Nodes (3): extract_address_hybrid(), is_context_safe(), Vérifie si le texte précédant l'adresse contient des mots interdits (proche,…

### Community 151 - "docker-compose service: airflow-init"
Cohesion: 0.50
Nodes (4): docker-compose service: airflow-db (postgres:14), docker-compose service: airflow-init, docker-compose service: airflow-scheduler, docker-compose service: airflow-webserver

### Community 152 - "archive_model_version"
Cohesion: 0.50
Nodes (3): archive_model_version(), Conserve une copie du modèle sous un nom versionné (hash du binaire), pour…, ArchiveModelVersionTest

### Community 155 - "site_files_config"
Cohesion: 0.50
Nodes (3): Config des fichiers 'classiques' (hors Vizzit) pour une ville donnée, à partir…, site_files_config(), SiteFilesConfigTest

## Ambiguous Edges - Review These
- `Fixture carte Vizzit (announce-card, prix en €)` → `Décision ORA-93/94 : aucune photo scrapée hébergée`  [AMBIGUOUS]
  scripts/tests/fixtures/vizzit_card_euro.html · relation: conceptually_related_to

## Knowledge Gaps
- **171 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+166 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **83 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Fixture carte Vizzit (announce-card, prix en €)` and `Décision ORA-93/94 : aucune photo scrapée hébergée`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `ChatService` connect `ChatService` to `ChatServiceTest`, `normalize_text`, `app.py`, `test_chat_service.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `CavaliersRadiusService` connect `CavaliersRadiusService` to `app.py`, `CavaliersRadiusServiceTest`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `summarize_cavaliers()` connect `summarize_cavaliers` to `CavaliersRadiusService`, `app.py`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ChatService` (e.g. with `ChatServiceTest` and `ExtractLocationsFuzzyMatchingTest`) actually correct?**
  _`ChatService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `run_fusion()` (e.g. with `clean_price_integer()` and `clean_surface()`) actually correct?**
  _`run_fusion()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _171 weakly-connected nodes found - possible documentation gaps or missing edges._