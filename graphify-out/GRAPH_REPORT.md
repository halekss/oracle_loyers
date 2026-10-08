# Graph Report - wt-ci  (2026-10-08)

## Corpus Check
- 236 files · ~590,325 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2474 nodes · 3854 edges · 234 communities (145 shown, 89 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 179 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dcfd52e8`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- summarize_cavaliers
- CalquesView.jsx
- complete_data_extraction.py
- resolve_quartier_filter
- monitor_drift.py
- CavaliersRadiusServiceTest
- app.py
- pick_user_agent
- App.jsx
- clean_immo.py
- AnnoncesStoreTest
- AnnonceCard.jsx
- scraper_orpi.py
- merge_cavaliers
- generate_map.py
- build_report_html
- RowsToVerifyTest
- build_feature_row
- test_scraper_utils.py
- scraper_vizzit.py
- ChatService
- _geocode
- test_playwright_selectors.py
- localisation_texte.py
- useCavaliersRadius.test.js
- scraper_paruvendu.py
- prepare_new_city.py
- get_connection
- CavaliersRequestSchema
- CheckUrlStatusTest
- ResultCard.jsx
- schemas.py
- LoggingConfigTest
- normalize_text
- GetTileTest
- EnrichDescriptionsTest
- AnnoncesRoutesTest
- ChatServiceTest
- BuildBridgeMessageScriptTest
- scope_cavaliers_to_ville
- load_site_config
- test_data_fusion.py
- run_fusion
- annonces_store.py
- QuartierStatsRouteTest
- API_CONTRACT.md (Contrat API)
- annonces.db (SQLite store, ORA-112)
- step_flag_expired
- extract_type
- devDependencies
- clean_immo.py
- test_clean_immo_steps.py
- test_generate_map.py
- 4 cavaliers (Vice, Gentrification, Nuisance, Superstition) POI layers
- step_archive_hors_master
- data_fusion.py
- MainRegeneratesAWorkingLyonMapTest
- ModelRegressionTest
- generate_map.py
- record_model_metadata
- DataLoader
- match_quartier
- PredictRouteTest
- StepQuartiersTest
- SearchForm.jsx
- VizzitExtractionTest
- CavaliersRouteTest
- SyncDeactivatesHorsMasterTest
- GeocodageTest
- RateLimitBehaviorTest
- dependencies
- CavaliersRadiusServiceNoRadiusTest
- L'Oracle des Loyers
- bs4_first_text
- extract_postal_code
- resolve_seloger_lieu
- test_rollback_model.py
- ErrorBoundary
- test_scraper_extraction_fixtures.py
- load_declared_villes
- test_chat_service.py
- File Structure
- scraper_utils.py
- PruneDeadMapListingsTest
- get_map_tile
- decide_promotion
- LoadLayersConfigTest
- File Structure
- CheckUrlStatusBrowserTest
- DetailDescriptionExtractionTest
- data_versioning.py
- ReportPdfRouteTest
- docker-compose.yml
- PanelNav.jsx
- computeHomeStats
- computeQuartierOptions
- CavaliersRadiusService
- oracle_cavaliers_dag.py (per-city, ORA-153)
- VizzitCardTest
- QuartierStatsRequestSchema
- clean_price_integer
- clean_surface
- train
- resolve_quartier
- DedoublonnerTest
- BuildCavalierMarkersScriptTest
- scripts
- MemoryStorage
- Plan: non-destructive dead-listing cleanup (ORA-134 bis)
- load_existing_rows
- GetChromeDriverOptionsTest
- QuartierHistoriqueRouteTest
- BuildImmoMarkersClickScriptTest
- RuntimeConfigTest
- package.json
- AdresseDuBienTest
- api.js
- scraper_seloger.py
- format_description
- fetch_lyon_arrondissements.py
- geocodage.py
- ChatRouteTest
- HealthRouteTest
- GeocodingJitterTest
- StepExclureNonLogementTest
- ResolveLilleQuartierHintTest
- StepFeaturesTest
- StepPruneExpiredTest
- WriteMapMetadataTest
- SanitizeListingUrlTest
- LilleQuartiersGeojsonTest
- QuartierAmbigu.jsx
- archive_model_version
- fetch_lille_quartiers.py
- MatchQuartierLilleTest
- StepSyncAnnoncesStoreTest
- RunFusionSelogerLieuTest
- AddQuartiersLayerTest
- CavalierIconHtmlTest
- ComputeLayerCountsTest
- LoadGeojsonFileTest
- AnnonceDetailModal.jsx
- get_db_connection
- get_scraper_logger
- _FakeSeleniumElement
- is_context_safe
- ListingsRouteTest
- BuildLayerGroupsScriptTest
- FocusStyleConstantTest
- ScaleScriptTest
- ResolveVillePathsTest
- run_scrapers.sh
- StepTypesTest
- vite.config.js
- chat_service.py
- archive_stale_rows
- oracle_annonces_dag.py
- oracle_cavaliers_dag.py
- oracle_cleanup_dag.py
- autoprefixer
- rollback_model.py
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
- Generated Folium map for Lille (map_pings_lille_calques)
- CI/CD Render deploy hook (ORA-64)
- Data science deps (pandas, scikit-learn, numpy, scipy, joblib, shapely)
- Flask stack (Flask, flask-cors, flask-limiter, flasgger, pydantic)
- folium
- google-genai (Gemini client)
- rapidfuzz (fuzzy matching)
- sentry-sdk[flask]
- weasyprint (PDF export)
- xgboost==2.1.4 pin (ORA-152)
- Healthchecks des services
- Vite frontend HTML shell (fonts Inter/Archivo, ORA-170)
- Frontend README (Vite/React template)
- React Logo (react.svg)
- XGBoost training keeps archived listings
- Century21 detail page fixture
- Orpi detail page fixture
- Orpi results page fixture
- PAP detail page fixture (synthetic)
- ParuVendu detail page fixture
- ParuVendu h3 card layout fixture
- SeLoger detail page fixture (synthetic)
- Fixture carte Vizzit (announce-card, prix en €)
- Application Security Review (OWASP Top 10) — ORA-69
- OWASP A01: Broken Access Control — risk accepted (ORA-46)
- OWASP A02: Cryptographic Failures — OK
- OWASP A03: Injection — OK
- OWASP A04: Insecure Design — OK
- OWASP A05: Security Misconfiguration — partially corrected
- OWASP A07: Identification and Authentication Failures — risk accepted (ORA-46)
- OWASP A10: Server-Side Request Forgery — OK
- XgboostVersionGuardTest
- ChatRequestSchema
- _fetch_all_annonces
- resolve_default_cp
- PruneDeadAnnoncesTest
- fiche.spec.js
- step_prune_expired
- test_cavaliers_radius.py
- LooksLikeSoft404Test

## God Nodes (most connected - your core abstractions)
1. `ChatService` - 51 edges
2. `AnnoncesStoreTest` - 36 edges
3. `build_report_html()` - 25 edges
4. `run_fusion()` - 24 edges
5. `App()` - 23 edges
6. `_geocode()` - 21 edges
7. `CavaliersRequestSchema` - 19 edges
8. `ChatServiceTest` - 19 edges
9. `retry_with_backoff()` - 18 edges
10. `main()` - 18 edges

## Surprising Connections (you probably didn't know these)
- `Photo hotlink posture (ORA-134, supersedes ORA-94)` --semantically_similar_to--> `SET_TILE_URL message`  [INFERRED] [semantically similar]
  LEGAL_DECISIONS.md → MAP_CONTRACT.md
- `recheck_ambiguous()` --calls--> `_fetch_all_annonces()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `check_url_status_browser()` --calls--> `looks_like_soft_404()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `annonces_store.get_annonce_by_url` --shares_data_with--> `annonces.db (SQLite store, ORA-112)`  [INFERRED]
  MAP_CONTRACT.md → README.md
- `Address geocoding via third-party service (ORA-180)` --conceptually_related_to--> `clean_immo.py`  [AMBIGUOUS]
  LEGAL_DECISIONS.md → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Airflow docker-compose services** — docker_compose_airflow_db, docker_compose_airflow_init, docker_compose_airflow_webserver, docker_compose_airflow_scheduler [EXTRACTED 1.00]
- **Weekly annonces ETL flow (fusion -> clean -> train -> map)** — readme_oracle_annonces_dag, readme_data_fusion, readme_clean_immo, readme_train_model, map_contract_generate_map, readme_master_immo_final [EXTRACTED 1.00]
- **Photo display legal posture across UI surfaces** — legal_decisions_no_photo_hosting_ora_94, legal_decisions_photo_hotlink_ora_134, legal_decisions_annoncecard, legal_decisions_annoncedetailcontent, map_contract_annonce_select [EXTRACTED 1.00]
- **React <-> Folium iframe bridge** — map_contract_mapcomponent, map_contract_build_bridge_message_script, map_contract_build_immo_markers_click_script, map_contract_maplayers_config, map_contract_origin_check_ora_125 [EXTRACTED 1.00]
- **OWASP Top 10 (2021) Security Checklist** — security_review_a01_broken_access_control, security_review_a02_crypto_failures, security_review_a03_injection, security_review_a04_insecure_design, security_review_a05_security_misconfiguration, security_review_a06_vulnerable_components, security_review_a07_auth_failures, security_review_a08_integrity_failures, security_review_a09_logging_monitoring, security_review_a10_ssrf [EXTRACTED 1.00]
- **Fonds de carte overlays** — docs_mockups_vue_calques_fonds_de_carte, docs_mockups_vue_calques_metro_lines, docs_mockups_vue_calques_prix_m2_arrondissement, docs_mockups_vue_calques_dark_basemap [INFERRED 0.85]
- **Four cavalier POI layers filtered by radius and shown in legend** — docs_mockups_vue_calques_cavalier_vice, docs_mockups_vue_calques_cavalier_gentrification, docs_mockups_vue_calques_cavalier_nuisance, docs_mockups_vue_calques_cavalier_superstition, docs_mockups_vue_calques_rayon_selector, docs_mockups_vue_calques_map_legend [INFERRED 0.85]

## Communities (234 total, 89 thin omitted)

### Community 0 - "summarize_cavaliers"
Cohesion: 0.06
Nodes (31): enrich_annonce_detail(), ORA-174 (maquette 06, "Fiche annonce") : enrichit une annonce issue…, absence_phrase_for(), detail_cavaliers(), _intensity_tier(), list_poi_types(), phrase_for(), _pick_variant() (+23 more)

### Community 1 - "CalquesView.jsx"
Cohesion: 0.05
Nodes (37): CalquesView(), IMMO_KEYS, immoLayerByKey, LYON_LINE_CODES, quartiersLayer, RADIUS_OPTIONS, cavaliersDetail, facteurs (+29 more)

### Community 2 - "complete_data_extraction.py"
Cohesion: 0.06
Nodes (29): advert_id(), coordinates_from_api_response(), extract_coordinates_from_html(), fetch_api_coordinates(), get_gps_from_url(), process_row(), URL de recherche Vizzit d'une ville (scraping_config.json), sans tranche de…, Identifiant d'annonce Vizzit : dernier segment de l'URL de la fiche. (+21 more)

### Community 3 - "resolve_quartier_filter"
Cohesion: 0.10
Nodes (17): compute_price_history(), compute_price_history_from_listings(), _filter_quartier(), Calcule l'évolution du prix moyen/m² pour `quartier` à travers tous les…, Ne lit que les colonnes utiles à l'historique (prix/quartier/dates) —…, Calcule l'évolution du prix moyen/m² pour `quartier` depuis…, _read_listing_columns(), Résolution d'une recherche utilisateur (texte libre) en un sous-ensemble du… (+9 more)

### Community 4 - "monitor_drift.py"
Cohesion: 0.07
Nodes (29): CI Workflow (ci.yml), CI job: backend (pytest), CI job: dependency-scan (pip-audit, npm audit), CI job: deploy (Render deploy hooks, ORA-64), CI job: e2e (Playwright vs vite preview + Flask), CI job: frontend (lint, build, test), CI job: scrapers (pytest, excludes e2e), Model Drift Monitor Workflow (+21 more)

### Community 5 - "CavaliersRadiusServiceTest"
Cohesion: 0.17
Nodes (5): Raccourci pratique (tests) : l'entrée de `result["cavaliers_detail"]` dont…, CavaliersRadiusServiceTest, Le fichier Lille fixture a un BOM (utf-8-sig) : si le service le lisait en…, Le Bar Loin (800m) et l'École du Coin (800m) n'entrent que dans le rayon 1000m…, Cimetière du Nord (1500m) reste le plus proche même si hors de tous les rayons…

### Community 6 - "app.py"
Cohesion: 0.06
Nodes (41): after_request, chat(), get_annonce_detail(), get_annonces(), get_cavaliers(), get_chat_rate_limit(), get_cors_origins(), get_default_rate_limits() (+33 more)

### Community 7 - "pick_user_agent"
Cohesion: 0.11
Nodes (21): prune_dead_map_listings(), Nettoyage ponctuel des annonces mortes dans master_immo_final.csv + carte…, Écrit dans un fichier temporaire puis remplace `path` via os.replace (atomique)…, Vérifie chaque url de `csv_path` (HTTP puis navigateur headless pour les…, _write_csv_atomically(), check_url_status_browser(), looks_like_challenge_page(), looks_like_valid_listing() (+13 more)

### Community 8 - "App.jsx"
Cohesion: 0.08
Nodes (21): App(), renderEstimationView(), renderScanView(), renderSummaryChip(), makePanelFallback(), MOBILE_TABS, useIsDesktop(), CATEGORY_STYLES (+13 more)

### Community 9 - "clean_immo.py"
Cohesion: 0.09
Nodes (38): build_shapes_from_cavaliers(), build_titre(), clean_zipcode(), determine_type_local(), extract_seloger_quartier_slug(), get_nearest_distance_and_count(), get_point_for_zipcode(), get_point_in_circle() (+30 more)

### Community 10 - "AnnoncesStoreTest"
Cohesion: 0.05
Nodes (4): AnnoncesStoreTest, ORA-173 : "€/m² croissant" (tri par défaut de la maquette 05) — prix_m2 n'est…, `NULLIF(surface, 0)` -> NULL pour une surface manquante : SQLite trie NULL…, Le frontend envoie le slug de la ville active ("lyon"), la colonne stocke…

### Community 11 - "AnnonceCard.jsx"
Cohesion: 0.14
Nodes (19): AnnonceCard(), AnnonceIllustration(), formatPrice(), ILLUSTRATION_BY_CATEGORY, baseAnnonce, AnnoncesList(), loadAnnonces(), SORT_OPTIONS (+11 more)

### Community 12 - "scraper_orpi.py"
Cohesion: 0.09
Nodes (19): _fetch_geocodage(), geocode_adresse(), checkpoint(), load_page(), parse_quartier(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Nom de quartier seul depuis le libellé de localisation Orpi ("Lyon 8-…, checkpoint() (+11 more)

### Community 13 - "merge_cavaliers"
Cohesion: 0.09
Nodes (19): fetch_elements(), get_cavaliers_data(), merge_cavaliers(), Lit le nom de la ville active (`villes.<ville_active>.nom`) depuis…, Résout le nom d'affichage d'une ville depuis son slug, indépendamment de…, Fusionne les cavaliers déjà connus avec les cavaliers fraîchement extraits.…, Éléments Overpass de `query`, ou None si les 4 essais échouent (429/504 =…, Récupère la liste complète des lieux pour chaque catégorie et fusionne avec le… (+11 more)

### Community 14 - "generate_map.py"
Cohesion: 0.09
Nodes (33): add_quartiers_layer(), build_bridge_message_script(), build_cavalier_markers_script(), build_immo_markers_click_script(), build_immo_tooltip_html(), build_layer_groups_script(), build_metro_station_popup_html(), build_scale_script() (+25 more)

### Community 15 - "build_report_html"
Cohesion: 0.11
Nodes (15): build_report_html(), _ecart_html(), _ecart_pct(), _escape(), _format_m2(), _format_price(), _quartile_stats(), Rend le rapport d'estimation en PDF (bytes), via WeasyPrint (ORA-121). (+7 more)

### Community 16 - "RowsToVerifyTest"
Cohesion: 0.06
Nodes (11): CheckUrlStatusAsyncTest, Integration test: mix of all statuses with various verification timestamps., Test the date-arithmetic logic of _rows_to_verify (TTL/staleness detection)., Row with statut='active' and derniere_verification_http older than ttl_days →…, Row with statut='active' and derniere_verification_http within ttl_days → NOT…, Row with statut='active' and missing/empty derniere_verification_http →…, Row with statut='active' and NaT derniere_verification_http → included., Row with statut='a_verifier' regardless of derniere_verification_http → always… (+3 more)

### Community 17 - "build_feature_row"
Cohesion: 0.14
Nodes (13): build_feature_row(), compute_distance_features(), haversine_distance_m(), normalize_type_bien(), normalize_type_local(), Construit le vecteur de features attendu par le modèle à partir du payload…, Normalise un type de bien utilisateur (T1, studio, T4+...) vers une catégorie…, Normalise le type de bien brut (Appartement/Maison/Studio), 'Appartement' par… (+5 more)

### Community 18 - "test_scraper_utils.py"
Cohesion: 0.09
Nodes (13): find_first(), Date du jour (UTC) au format ISO — utilisée pour horodater la colonne…, Décide si la pagination d'un scraper doit continuer après une page où…, Essaie chaque sélecteur CSS de `selectors` dans l'ordre sur `element` et…, should_continue_pagination(), today_iso(), BlankShortDescriptionsTest, CleanDescriptionTest (+5 more)

### Community 19 - "scraper_vizzit.py"
Cohesion: 0.11
Nodes (27): apply_price_band(), build_page_url(), checkpoint(), clean_card_text(), decode_data_o_link(), est_en_euros(), find_attr(), find_text() (+19 more)

### Community 21 - "_geocode"
Cohesion: 0.16
Nodes (6): AdresseGeocodeeTest, _geocode(), _geocodeur(), OrdrePrioriteLocalisationTest, Une annonce, colonnes par défaut vides ; renvoie le df après step_geocoding., _sans_reseau()

### Community 22 - "test_playwright_selectors.py"
Cohesion: 0.08
Nodes (26): expectedFailure, retry_with_backoff, checkpoint(), lien_de_carte(), load_page(), href du premier <a> de la carte, ou None si le bloc n'a pas de lien.…, Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, assert_selector_canary() (+18 more)

### Community 23 - "localisation_texte.py"
Cohesion: 0.14
Nodes (16): _candidats(), _nom_propre(), Adresse du bien extraite d'un texte libre (ORA-180) : « 52 rue André Bollier ».…, [(adresse, avec_numero)] acceptées dans une phrase brute., _clause_propre(), _evaluer(), extraire_zone(), localiser_par_texte() (+8 more)

### Community 24 - "useCavaliersRadius.test.js"
Cohesion: 0.43
Nodes (5): defaultDetail, defaultFacteurs, renderCavaliersRadius(), useCavaliersRadius(), CAVALIERS_RADIUS_M

### Community 25 - "scraper_paruvendu.py"
Cohesion: 0.11
Nodes (20): checkpoint(), fetch_description(), fetch_page(), find_description_bs4(), find_image_bs4(), find_lien_partiel(), Lien de l'annonce : le titre s'il est un <a>, sinon le premier lien…, Équivalent BeautifulSoup de `selenium_description_fetcher` : premier texte de… (+12 more)

### Community 26 - "prepare_new_city.py"
Cohesion: 0.17
Nodes (14): build_config_skeleton(), build_report(), classify(), fetch_arrondissements(), fetch_commune(), fetch_shared_postal_codes(), _get(), main() (+6 more)

### Community 27 - "get_connection"
Cohesion: 0.11
Nodes (25): log_annonce_click(), Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le…, deactivate_hors_master(), Alimente la table SQLite `annonces` (services/annonces_store.py) à partir du…, Passe `inactive` les annonces du store absentes du master (ORA-193), sauf si le…, step_sync_annonces_store(), count_clicks(), deactivate_annonces_not_in() (+17 more)

### Community 28 - "CavaliersRequestSchema"
Cohesion: 0.15
Nodes (6): CavaliersRequestSchema, La query string GET ne transporte que des chaînes : "none" (toute casse) est la…, CavaliersRequestSchemaTest, Rayon "Aucun" (ORA-183, v3) : le sélecteur segmenté envoie la valeur "none"…, Non-régression : seul un "none" explicite retire le rayon — un appel qui omet…, field_validator

### Community 30 - "ResultCard.jsx"
Cohesion: 0.14
Nodes (18): formatM2(), formatPrice(), formatShortDate(), historyPeriod(), positionOnRange(), RANGE_LABELS, ResultCard(), baseData (+10 more)

### Community 31 - "schemas.py"
Cohesion: 0.23
Nodes (8): ComparableSchema, FacteurSchema, PdfReportRequestSchema, PredictRequestSchema, PriceHistoryPointSchema, Schémas de validation des payloads pour les routes Flask actives (/api/chat,…, PredictRequestSchemaTest, BaseModel

### Community 32 - "LoggingConfigTest"
Cohesion: 0.10
Nodes (7): configure_logging(), init_sentry(), Configuration centralisée de l'observabilité applicative du backend (ORA-63).…, Configure le logger racine du process avec un format structuré et un niveau…, Initialise sentry-sdk pour capturer automatiquement les exceptions non gérées…, LoggingConfigTest, Vérifie le logger structuré centralisé (ORA-63) : niveau par défaut, prise en…

### Community 33 - "normalize_text"
Cohesion: 0.20
Nodes (6): compact_text(), normalize_text(), searchable_text(), CompactTextTest, NormalizeTextTest, SearchableTextTest

### Community 34 - "GetTileTest"
Cohesion: 0.12
Nodes (4): BuildUpstreamUrlTest, GetTileTest, IsValidTileTest, TileRouteTest

### Community 35 - "EnrichDescriptionsTest"
Cohesion: 0.25
Nodes (3): EnrichDescriptionsTest, _Logger, ORA-161 : visite des pages détail plafonnée, sans jamais insister en cas de…

### Community 36 - "AnnoncesRoutesTest"
Cohesion: 0.11
Nodes (3): AnnoncesRoutesTest, ORA-174 : coordonnées, €/m² moyen du quartier et cavaliers viennent du dataset…, ORA-183 : les favoris sont servis ensemble, quel que soit leur rang dans la…

### Community 38 - "BuildBridgeMessageScriptTest"
Cohesion: 0.11
Nodes (7): BuildBridgeMessageScriptTest, Contrat postMessage carte (ORA-125) : la carte générée ne doit traiter un…, Remplace l'ancienne correspondance par texte de <label> (fragile, cassait dès…, ORA-105 : recentrage sur la bounding-box des résultats filtrés., L'URL du proxy de tuiles arrive au runtime (dépend du déploiement) : validée…, v3 (ORA-183) : tous les pings d'un cavalier actif restent visibles, rayon actif…, Un second SET_FOCUS (nouveau rayon) ne doit pas laisser l'ancien cercle affiché…

### Community 39 - "scope_cavaliers_to_ville"
Cohesion: 0.33
Nodes (3): Cavaliers de la ville donnée uniquement (même convention que…, scope_cavaliers_to_ville(), ScopeCavaliersToVilleTest

### Community 40 - "load_site_config"
Cohesion: 0.33
Nodes (3): load_site_config(), Charge la config de la ville active (URL de recherche, paramètre de pagination)…, LoadSiteConfigTest

### Community 41 - "test_data_fusion.py"
Cohesion: 0.18
Nodes (6): Config des fichiers 'classiques' (hors Vizzit) pour une ville donnée, à partir…, site_files_config(), PostalCodeFromUrlTest, Le fichier GPS Vizzit (complete_data_extraction.py) n'a pas de colonne `Image`…, RunFusionVizzitImageTest, SiteFilesConfigTest

### Community 42 - "run_fusion"
Cohesion: 0.18
Nodes (8): Fusionne les CSV scrapés en base_de_donnees_immo_complet.csv. Par défaut…, run_fusion(), ORA-134 : la colonne DerniereVue des scrapers doit survivre à la fusion sous le…, ORA-161 : la description libre scrapée sur la page détail (colonne…, ORA-153 : chaque DAG annonces tourne désormais indépendamment par ville.…, RunFusionDateDernierScanTest, RunFusionDescriptionDetailTest, RunFusionPerVilleTest

### Community 43 - "annonces_store.py"
Cohesion: 0.13
Nodes (15): check_url_status(), looks_like_soft_404(), Nettoyage ponctuel des annonces mortes dans annonces.db (ORA-134). Le pipeline…, True si `html_text` contient un des `SOFT_404_PATTERNS` (insensible à la casse)., Vérifie une url en direct. Renvoie True (confirmée morte : 404/410, ou soft-404…, check_url_status_async(), Vérification HTTP asynchrone des annonces à statut incertain (ORA-134 bis, tier…, Vérifie les annonces éligibles (cf. `_rows_to_verify`) et met à jour leur… (+7 more)

### Community 44 - "QuartierStatsRouteTest"
Cohesion: 0.11
Nodes (6): QuartierStatsRouteTest, ORA-110 : le endpoint utilise désormais le matching partagé (fuzzy) au lieu…, ORA-111 : message différencié aucun résultat vs quartier ambigu., ORA-111 : suggestions renvoyées quand plusieurs quartiers sont proches., ORA-167 : min/P25/médiane/P75/max calculés sur tous les biens filtrés, pas sur…, ORA-122/ORA-128/ORA-177 : échantillon de biens comparables réels, pour le…

### Community 45 - "API_CONTRACT.md (Contrat API)"
Cohesion: 0.16
Nodes (17): API_CONTRACT.md (Contrat API), Niveau de confiance (Faible/Moyenne/Élevée), Résolution floue du quartier (text_matching.py), GET /api/annonces/<id>, GET /api/cavaliers, GET /api/listings, Décision ORA-46 : aucune authentification, POST /api/chat (Immotep) (+9 more)

### Community 46 - "annonces.db (SQLite store, ORA-112)"
Cohesion: 0.13
Nodes (17): Décision ORA-86 : redirection directe sans modal, GET /api/annonces, POST /api/annonces/<id>/click, AnnonceCard.jsx, AnnonceDetailContent.jsx, Click redirects to source listing (ORA-89), Never host scraped photos (ORA-94, option B), Photo hotlink posture (ORA-134, supersedes ORA-94) (+9 more)

### Community 47 - "step_flag_expired"
Cohesion: 0.18
Nodes (5): `sur_carte` : True si l'annonce a été revue lors du dernier scrape de son…, Fusionne `df` (résultat frais de data_fusion.py) avec le…, step_flag_expired(), _vu_au_dernier_scrape(), StepFlagExpiredTest

### Community 48 - "extract_type"
Cohesion: 0.21
Nodes (3): extract_type(), Détermine le type de bien (Maison, Appartement, Studio, Coloc, Parking,…, ExtractTypeTest

### Community 49 - "devDependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, devDependencies, eslint, @eslint/js, jsdom, postcss, @testing-library/react (+9 more)

### Community 50 - "clean_immo.py"
Cohesion: 0.11
Nodes (21): Address geocoding via third-party service (ORA-180), geocodage_cache.json, IGN Geoplateforme, annonces_store.py changes (premiere_vue, derniere_vue, record_price_observation), historique_prix table (append-only price history), price_evolution.py compute_price_trend, step_flag_expired (clean_immo.py, 2-state merge), step_flag_expired (3-state preserving merge) (+13 more)

### Community 51 - "test_clean_immo_steps.py"
Cohesion: 0.12
Nodes (4): BuildShapesFromCavaliersTest, BuildTitreTest, GetPointForZipcodeZonesLimitrophesTest, StepIdsTest

### Community 52 - "test_generate_map.py"
Cohesion: 0.12
Nodes (6): BuildImmoTooltipHtmlTest, BuildMetroStationPopupHtmlTest, FilterByVilleTest, ORA-188 : la pastille DivIcon 24x24 avec la lettre de ligne est retirée…, Aucune clé, ni URL CARTO, dans la carte générée (fichier versionné)., TileLayerNeverEmbedsAKeyTest

### Community 53 - "4 cavaliers (Vice, Gentrification, Nuisance, Superstition) POI layers"
Cohesion: 0.13
Nodes (16): Mockup: Vue Calques (Calques & 4 cavaliers), Cavalier Gentrification, Cavalier Nuisance, Cavalier Superstition, Cavalier Vice (Bar, Tabac, CBD Shop, Kebab), Couleur des annonces toggle (Écart / Type), Dark CARTO / OpenStreetMap basemap (Lyon, Ainay T2 context), Fonds de carte toggles (Métro & stations, Funiculaires, €/m² par arrondissement) (+8 more)

### Community 54 - "step_archive_hors_master"
Cohesion: 0.21
Nodes (7): load_sites_actifs(), Retire les colonnes `nom.1`, `nom.2`… que pandas crée à la lecture d'un CSV…, Clés des sites actifs (`sites_actifs` de scraping_config.json, ex. {'vizzit',…, Le master ne garde que les annonces scrapées au dernier run de leur (ville,…, _sans_colonnes_dupliquees(), step_archive_hors_master(), StepArchiveHorsMasterTest

### Community 55 - "data_fusion.py"
Cohesion: 0.18
Nodes (13): dedoublonner(), _distance_m(), load_sites_actifs(), postal_code_from_url(), Clés des sites actifs (`sites_actifs` de scraping_config.json), ou None si…, Début du texte libre de l'annonce, normalisé (lettres/chiffres seuls), ou None…, Même prix/surface/type/CP (déjà vrai ici) ET une preuve d'identité : même début…, Retire les vrais doublons (même clé prix/surface/prix_m2/type/CP + preuve… (+5 more)

### Community 56 - "MainRegeneratesAWorkingLyonMapTest"
Cohesion: 0.13
Nodes (5): MainRegeneratesAWorkingLyonMapTest, Test d'intégration (données réelles versionnées, backend/data/) : exécute…, Ordre textuel : oracleCavalierMarkers doit être à l'intérieur du callback…, Un seul marker par lieu (folium.Marker/DivIcon, cf. cavalier_icon_html) — plus…, ORA-183 (v3) : une seule légende (React, MapComponent) — celle générée côté…

### Community 57 - "ModelRegressionTest"
Cohesion: 0.17
Nodes (8): ModelRegressionTest, PredictEndpointRegressionTest, _prepare_features(), ORA-154 : un modèle XGBoost distinct par ville plutôt que `ville` en feature…, Non-régression explicite du bug corrigé par ORA-30 : /api/predict renvoyait…, Reproduit exactement le prétraitement de train_model.py (ORA-154, ORA-155),…, Remplace backend/scripts/test_prediction.py (script manuel, échantillon…, VilleExcludedFromFeaturesTest

### Community 58 - "generate_map.py"
Cohesion: 0.17
Nodes (15): build_bridge_message_script, build_cavalier_markers_script, build_layer_groups_script, FLY_TO message, FLY_TO_BOUNDS message, Folium render-order pitfall (init script after </body>), generate_map.py, MapComponent.jsx (+7 more)

### Community 59 - "record_model_metadata"
Cohesion: 0.23
Nodes (7): load_active_model_metadata(), Lit les métadonnées (`metrics`, `model_version`) du modèle actuellement actif…, Écrit `<model_path>.meta.json`, référençant explicitement la version des…, record_model_metadata(), LoadActiveModelMetadataTest, PromotionGuardTriggersRollbackTest, Reproduit le flux de décision de train_model.py au niveau des fonctions qu'il…

### Community 60 - "DataLoader"
Cohesion: 0.18
Nodes (9): DataLoader, Charge le CSV en mémoire et applique un nettoyage de base., Renvoie le DataFrame brut., clean_input_data(), format_prediction_response(), guess_room_count_smart(), Nettoie les données entrantes., Devine le type de logement (T1, T2...) basé sur la surface si l'information est… (+1 more)

### Community 61 - "match_quartier"
Cohesion: 0.22
Nodes (5): match_quartier(), Fait correspondre `query` (texte libre, éventuellement fautif ou noyé dans une…, MatchQuartierTest, QuartierAliasTest, ORA-109 : tolérance aux fautes de frappe sur les quartiers connus.

### Community 62 - "PredictRouteTest"
Cohesion: 0.14
Nodes (4): PredictRouteTest, ORA-154 : la panne d'un modèle ne doit plus dégrader toutes les villes — seule…, ORA-152 : un modèle qui prédit un loyer négatif (ex. pickle XGBoost désérialisé…, Un loyer exactement nul n'est pas plus plausible qu'un loyer négatif.

### Community 64 - "SearchForm.jsx"
Cohesion: 0.30
Nodes (8): formatEuros(), SearchForm(), splitAtMatch(), quartierOptions, TYPE_FILTERS, normalizeText(), loadRecentSearches(), pushRecentSearch()

### Community 65 - "VizzitExtractionTest"
Cohesion: 0.15
Nodes (3): _FakeElement, Reproduit juste ce dont decode_data_o_link a besoin (element.get_attribute),…, VizzitExtractionTest

### Community 69 - "RateLimitBehaviorTest"
Cohesion: 0.15
Nodes (4): RateLimitBehaviorTest, RateLimitConfigTest, ORA-118 : le frontend a besoin de X-RateLimit-Remaining pour afficher un…, Sans Access-Control-Expose-Headers, fetch() côté frontend ne peut pas lire ces…

### Community 70 - "dependencies"
Cohesion: 0.15
Nodes (13): dependencies, leaflet, react, react-dom, react-leaflet, react-markdown, remark-gfm, leaflet (+5 more)

### Community 71 - "CavaliersRadiusServiceNoRadiusTest"
Cohesion: 0.22
Nodes (4): CavaliersRadiusServiceNoRadiusTest, Rayon « Aucun » (ORA-183, v3) : totaux à l'échelle de la ville, sans filtre de…, 3 lieux Vice à Lyon (Le Bar Proche 100m, Le Bar Loin 800m, Kebab King 400m) :…, Lille (fixture LILLE_ROWS) n'a que du Vice : à l'échelle d'une ville, une…

### Community 72 - "L'Oracle des Loyers"
Cohesion: 0.33
Nodes (5): API_CONTRACT.md, cavaliers_factors.py, Les 4 Cavaliers (Gentrification, Vice, Nuisance, Superstition), L'Oracle des Loyers, PRIVACY.md

### Community 73 - "bs4_first_text"
Cohesion: 0.21
Nodes (6): bs4_first_text(), bs4_select_first_matching(), OrpiExtractionTest, PapExtractionTest, Équivalent BeautifulSoup de find_first/find_text (cascade de sélecteurs CSS)., Équivalent BeautifulSoup de la cascade `for sel in CARD_SELECTORS:…

### Community 74 - "extract_postal_code"
Cohesion: 0.29
Nodes (3): extract_postal_code(), Normalise le CP (69XXX ou 59XXX). `default_cp` est le repli utilisé quand aucun…, ExtractPostalCodeTest

### Community 75 - "resolve_seloger_lieu"
Cohesion: 0.24
Nodes (5): normalize_lieu(), CP réel déduit du champ `Lieu` de SeLoger, ou du premier segment d'`Infos`…, resolve_seloger_lieu(), ORA-71 POC follow-up : le champ Lieu de SeLoger contient parfois une vraie…, ResolveSelogerLieuTest

### Community 76 - "test_rollback_model.py"
Cohesion: 0.29
Nodes (3): ORA-154 : un modèle distinct par ville — price_predictor_<ville>.pkl, pas un…, ResolveModelPathTest, RollbackModelTest

### Community 78 - "test_scraper_extraction_fixtures.py"
Cohesion: 0.15
Nodes (8): bs4_first_attr(), Century21ExtractionTest, load_fixture(), ParuVenduExtractionTest, Tests unitaires d'extraction par site (ORA-19), basés sur des fixtures HTML…, ParuVendu utilise déjà BeautifulSoup en production : on teste find_bs4…, Équivalent BeautifulSoup de find_attr (cascade de sélecteurs CSS -> attribut)., SeLogerExtractionTest

### Community 79 - "load_declared_villes"
Cohesion: 0.22
Nodes (7): load_declared_villes(), Villes déclarées dans scraping_config.json (ORA-71) : ajouter une ville au JSON…, merge_all_villes(), L'Oracle des Loyers — Fusion des cavaliers par ville Concatène les…, LoadDeclaredVillesTest, MergeAllVillesTest, ORA-153 : avant ce script, rien ne produisait cavaliers_all.csv automatiquement…

### Community 80 - "test_chat_service.py"
Cohesion: 0.20
Nodes (4): ExtractLocationsFuzzyMatchingTest, FakeClient, FakeModels, ORA-109 : la recherche de quartier tolère les fautes de frappe.

### Community 81 - "File Structure"
Cohesion: 0.18
Nodes (10): File Structure, Global Constraints, Nettoyage non-destructif des annonces mortes — Implementation Plan, Prochaines étapes après ce plan (hors scope, à netifier séparément si besoin), Self-Review, Task 1: Migration DB non-destructive + statut dans `annonces_store.py`, Task 2: Fusion préservante dans `clean_immo.py` (remplace le drop TTL), Task 3: Vérificateur HTTP asynchrone (`verify_annonces_async.py`) (+2 more)

### Community 82 - "scraper_utils.py"
Cohesion: 0.21
Nodes (6): atomic_csv_writer(), Écrit dans un fichier temporaire à côté de `output_path` et ne remplace ce…, _detect_local_chrome_major_version(), Utilitaires partagés entre les 6 scrapers (Century21, Orpi, PAP, ParuVendu,…, Détecte la version majeure du Chrome installé localement en interrogeant le…, AtomicCsvWriterTest

### Community 84 - "get_map_tile"
Cohesion: 0.24
Nodes (9): get_map_tile(), Proxy des tuiles CARTO du fond de carte : la clé API reste côté serveur…, build_upstream_url(), get_tile(), is_valid_tile(), Proxy des tuiles du fond de carte CARTO. CARTO exige une clé API sur ses…, Coordonnées de tuile plausibles : 0 <= z <= MAX_ZOOM, x et y dans [0, 2^z)., URL CARTO d'une tuile (sans la clé : elle voyage en paramètre séparé). (+1 more)

### Community 85 - "decide_promotion"
Cohesion: 0.31
Nodes (4): decide_promotion(), Décide si un modèle nouvellement entraîné doit remplacer le modèle actif.…, DecidePromotionTest, ORA-34 : un ré-entraînement automatique (DAG Airflow quotidien) ne doit jamais…

### Community 86 - "LoadLayersConfigTest"
Cohesion: 0.20
Nodes (4): LoadLayersConfigTest, ORA-130 : la liste des calques (nom Folium/TOGGLE_LAYER, visibilité par défaut,…, Non-régression ORA-130 : le refactor ne doit rien changer à l'état initial des…, Source unique (mapLayers.config.json) couleur+forme, lue à la fois par ce…

### Community 87 - "File Structure"
Cohesion: 0.20
Nodes (9): File Structure, Global Constraints, Note pour la suite (hors scope de ce plan), Self-Review, Séparation affichage carte / archive ML Implementation Plan, Task 1: `annonces_store.py` — statut 2-états, premiere_vue/derniere_vue, table `historique_prix`, Task 2: `clean_immo.py` — diff de scrape simplifié (2 états) + retrait du tier HTTP, Task 3: Filtrage affichage (carte + API) + vocabulaire XGBoost (+1 more)

### Community 88 - "CheckUrlStatusBrowserTest"
Cohesion: 0.09
Nodes (4): CheckUrlStatusBrowserTest, LooksLikeChallengePageTest, LooksLikeValidListingTest, RecheckAmbiguousTest

### Community 90 - "data_versioning.py"
Cohesion: 0.25
Nodes (5): Archive un instantané content-addressé de `csv_path` dans `snapshots_dir` et…, _sha256_of_file(), snapshot_dataset(), RecordModelMetadataTest, SnapshotDatasetTest

### Community 91 - "ReportPdfRouteTest"
Cohesion: 0.22
Nodes (3): ORA-122 : enrichissement du rapport (historique de prix, biens comparables)., ORA-177 : champs ajoutés pour aligner le rapport sur la maquette 09 (case…, ReportPdfRouteTest

### Community 92 - "docker-compose.yml"
Cohesion: 0.50
Nodes (8): Service airflow-db (postgres:14), docker-compose service: airflow-init, Service airflow-scheduler, Service airflow-webserver (:8082), docker-compose service: backend, docker-compose service: frontend (Vite dev), Réseau oracle-network, Montage ./scripts en lecture seule

### Community 93 - "PanelNav.jsx"
Cohesion: 0.33
Nodes (4): ICON_PROPS, icons, PanelNav(), PANEL_VIEWS

### Community 94 - "computeHomeStats"
Cohesion: 0.44
Nodes (7): arrondissementLabel(), computeHomeStats(), groupMedianPrixM2(), isFiniteNumber(), isLocated(), median(), listings

### Community 95 - "computeQuartierOptions"
Cohesion: 0.39
Nodes (7): arrondissementLabel(), computeQuartierOptions(), isFiniteNumber(), isLocated(), median(), mostFrequent(), listings

### Community 96 - "CavaliersRadiusService"
Cohesion: 0.21
Nodes (7): CavaliersRadiusService, _parse_categorie_cavalier(), Vice - Sex-shop" -> ("vice", "sex-shop") — même normalisation que…, Calcule en direct (haversine, sans passer par les colonnes précalculées à 500m…, Lit un CSV cavaliers_<ville>.csv en utf-8-sig (BOM déjà rencontré sur le…, Une catégorie, rayon "Aucun" : total et détail par sous-catégorie sur…, Détail (`cavaliers_detail`, même forme que cavaliers_factors.detail_cavaliers)…

### Community 97 - "oracle_cavaliers_dag.py (per-city, ORA-153)"
Cohesion: 0.18
Nodes (11): ORA-80 Legal/Ethics Epic (scraped listings display), Scraping compliance with CGU/robots.txt (ORA-67/ORA-93), Scraper anti-detection (UA/proxy rotation) and legal limits, api_overpass.py, cavaliers_all.csv, enrich_cavaliers_cp.py, ETL Pipeline (Airflow DAGs), merge_cavaliers_villes.py (+3 more)

### Community 100 - "clean_price_integer"
Cohesion: 0.39
Nodes (3): clean_price_integer(), Convertit en entier (supprime €, cc, espaces, points)., CleanPriceIntegerTest

### Community 101 - "clean_surface"
Cohesion: 0.39
Nodes (3): clean_surface(), Extrait le nombre avant 'm2'., CleanSurfaceTest

### Community 102 - "train"
Cohesion: 0.20
Nodes (17): active_training_urls(), check_xgboost_version(), compare_on_common_test(), compare_sources(), load_source_dataframe(), _metrics(), prepare_features_and_target(), Charge le jeu d'entraînement d'UNE ville depuis `source` (ORA-181) : - 'master'… (+9 more)

### Community 103 - "resolve_quartier"
Cohesion: 0.36
Nodes (4): Résout `query` vers le libellé canonique d'un quartier de `known_quartiers`, ou…, resolve_quartier(), ORA-110 : point d'entrée unique utilisé par /api/quartier-stats, /api/quartier-…, ResolveQuartierTest

### Community 105 - "BuildCavalierMarkersScriptTest"
Cohesion: 0.25
Nodes (4): BuildCavalierMarkersScriptTest, Référence JS de chaque marker de cavalier (variable Folium + lat/lng + famille)…, SET_FOCUS (build_bridge_message_script) lit `entry.color` pour dessiner le halo…, Doit rester accessible une fois englobé dans une fonction (le callback…

### Community 106 - "scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, test, test:e2e, test:watch

### Community 108 - "Plan: non-destructive dead-listing cleanup (ORA-134 bis)"
Cohesion: 0.32
Nodes (8): Plan: separate map display from ML archive (ORA-144), Two-state status active/archivee driven by scrape diff, Plan: non-destructive dead-listing cleanup (ORA-134 bis), Non-destructive cleanup principle (never delete rows), oracle_cleanup_pipeline Airflow DAG (daily), Three-state status active/a_verifier/inactive, annonces_store.update_statut, verify_annonces_async.py (aiohttp HTTP verifier)

### Community 109 - "load_existing_rows"
Cohesion: 0.39
Nodes (3): load_existing_rows(), Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble…, LoadExistingRowsTest

### Community 111 - "QuartierHistoriqueRouteTest"
Cohesion: 0.29
Nodes (3): QuartierHistoriqueRouteTest, État actuel réel du projet (2 snapshots enregistrés à ce jour, voir…, ORA-182 : source alternative aux snapshots — état actuel réel du projet…

### Community 112 - "BuildImmoMarkersClickScriptTest"
Cohesion: 0.29
Nodes (3): BuildImmoMarkersClickScriptTest, ORA-185 : le clic sur un marker d'annonce n'ouvre plus un popup avec un lien…, Le popup retiré ouvrait le site source dans un nouvel onglet (`<a…

### Community 114 - "package.json"
Cohesion: 0.29
Nodes (6): name, overrides, vite, private, type, version

### Community 115 - "AdresseDuBienTest"
Cohesion: 0.20
Nodes (5): extraire_adresse(), localiser_adresse(), (adresse | None, raison courte). Contradiction = None., Premier texte (dans l'ordre donné) qui décide ; une contradiction est…, AdresseDuBienTest

### Community 116 - "api.js"
Cohesion: 0.17
Nodes (14): ALL_TYPES, buildChatContext(), ChatOracle(), DEFAULT_MESSAGES, describeChatError(), API_URL, ApiError, apiFetchOptions() (+6 more)

### Community 117 - "scraper_seloger.py"
Cohesion: 0.22
Nodes (7): checkpoint(), parse_title_attribute(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, Parse 'Type - Lieu - Prix - Infos' format. Returns None if format unrecognized., canonical_url(), Retire la query string et le fragment d'une URL d'annonce. Régression réelle…, SeLoger scraper test fixture (HTML)

### Community 118 - "format_description"
Cohesion: 0.47
Nodes (3): format_description(), Nettoie la description pour l'affichage final., FormatDescriptionTest

### Community 119 - "fetch_lyon_arrondissements.py"
Cohesion: 0.53
Nodes (5): fetch_arrondissement_boundary(), main(), ordinal_label(), Récupère une fois les polygones des 9 arrondissements de Lyon (Nominatim/ OSM)…, Récupère le polygone GeoJSON d'un arrondissement de Lyon via Nominatim.

### Community 120 - "geocodage.py"
Cohesion: 0.47
Nodes (5): _charger_cache(), geocoder(), _interroger(), Géocodage d'une adresse de Lyon via la Géoplateforme de l'IGN (ORA-180).…, {'lat', 'lon', 'precision': 'numero'|'rue', 'cp'} ou None ('lyon' ou 'lille').…

### Community 122 - "HealthRouteTest"
Cohesion: 0.33
Nodes (3): HealthRouteTest, ORA-154 : un modèle distinct par ville — /api/health expose l'état de chacun…, ORA-171 : "entraîné sur N annonces" (maquette 03) doit venir du dernier run…

### Community 131 - "QuartierAmbigu.jsx"
Cohesion: 0.47
Nodes (4): formatEuros(), QuartierAmbigu(), ambiguous, quartierOptions

### Community 132 - "archive_model_version"
Cohesion: 0.50
Nodes (3): archive_model_version(), Conserve une copie du modèle sous un nom versionné (hash du binaire), pour…, ArchiveModelVersionTest

### Community 133 - "fetch_lille_quartiers.py"
Cohesion: 0.50
Nodes (4): fetch_boundary(), main(), Récupère une fois les contours réels des quartiers de Lille (+ Lomme,…, Renvoie une Feature GeoJSON polygonale pour `nom`, ou None si OSM n'a pas de…

### Community 141 - "AnnonceDetailModal.jsx"
Cohesion: 0.33
Nodes (6): AnnonceDetailContent(), CATEGORY_STYLES, formatM2(), formatPrice(), AnnonceDetailModal(), detail

### Community 143 - "get_db_connection"
Cohesion: 0.50
Nodes (4): get_db_connection(), init_db(), Initialise la table 'annonces' si elle n'existe pas., Crée une connexion à la base de données.

### Community 144 - "get_scraper_logger"
Cohesion: 0.36
Nodes (3): get_scraper_logger(), Logger structuré commun aux scrapers : format et niveaux cohérents entre les 6…, GetScraperLoggerTest

### Community 145 - "_FakeSeleniumElement"
Cohesion: 0.29
Nodes (3): Century21LienDeCarteTest, _FakeSeleniumElement, CARD_SELECTOR ([class*=...]) attrape aussi un sous-bloc sans lien par carte (~1…

### Community 146 - "is_context_safe"
Cohesion: 0.67
Nodes (3): extract_address_hybrid(), is_context_safe(), Vérifie si le texte précédant l'adresse contient des mots interdits (proche,…

### Community 152 - "run_scrapers.sh"
Cohesion: 0.67
Nodes (3): DISPLAY, log(), run_scrapers.sh script

### Community 155 - "chat_service.py"
Cohesion: 0.67
Nodes (3): chat_service.py, Gemini cloud + deterministic filtering, no local RAG (ORA-119), Backend observability: structured logs + Sentry (ORA-63)

### Community 156 - "archive_stale_rows"
Cohesion: 0.32
Nodes (3): archive_stale_rows(), Déplace de `rows_by_lien` vers `<output>_archive.csv` les annonces non revues…, ArchiveStaleRowsTest

### Community 161 - "rollback_model.py"
Cohesion: 0.29
Nodes (5): Revenir à une version antérieure du modèle price_predictor_<ville>.pkl sans…, price_predictor_<ville>.pkl pour le slug donné — un modèle distinct par ville…, Restaure `model_path` à la version archivée `model_version`. `versions_dir`…, resolve_model_path(), rollback_to()

### Community 227 - "_fetch_all_annonces"
Cohesion: 0.33
Nodes (6): _fetch_all_annonces(), prune_dead_annonces(), Snapshot complet (id, url, titre) pris avant toute suppression : évite le bug…, Vérifie chaque annonce de `db_path` (DEFAULT_DB_PATH si None) et supprime…, delete_annonce(), Retire une annonce (et ses clics associés) du store, par `url` ou `annonce_id`…

### Community 228 - "resolve_default_cp"
Cohesion: 0.50
Nodes (3): CP de repli pour une ville (cf. extract_postal_code). Fail-fast plutôt que de…, resolve_default_cp(), ResolveDefaultCpTest

### Community 230 - "fiche.spec.js"
Cohesion: 0.43
Nodes (4): clickAtLatLng(), clickMarkerAndAwaitFiche(), expectAnnoncePopupOpen(), expectFicheOpen()

### Community 232 - "test_cavaliers_radius.py"
Cohesion: 0.40
Nodes (3): _offset(), (lat, lng) à ~`dist_m` mètres au nord de CENTER_LAT/CENTER_LNG., _write_csv()

## Ambiguous Edges - Review These
- `clean_immo.py` → `Address geocoding via third-party service (ORA-180)`  [AMBIGUOUS]
  LEGAL_DECISIONS.md · relation: conceptually_related_to

## Knowledge Gaps
- **174 isolated node(s):** `Backend observability: structured logs + Sentry (ORA-63)`, `CI/CD Render deploy hook (ORA-64)`, `Dependency vulnerability scan (ORA-65)`, `Healthchecks des services`, `sanitizeListingUrl` (+169 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **89 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `clean_immo.py` and `Address geocoding via third-party service (ORA-180)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `ChatService` connect `ChatService` to `test_chat_service.py`, `normalize_text`, `ChatServiceTest`, `app.py`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `CavaliersRadiusService` connect `CavaliersRadiusService` to `CavaliersRadiusServiceTest`, `app.py`, `CavaliersRadiusServiceNoRadiusTest`, `test_cavaliers_radius.py`, `build_feature_row`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Why does `SyncDeactivatesHorsMasterTest` connect `SyncDeactivatesHorsMasterTest` to `test_clean_immo_steps.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ChatService` (e.g. with `ChatServiceTest` and `ExtractLocationsFuzzyMatchingTest`) actually correct?**
  _`ChatService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `run_fusion()` (e.g. with `clean_price_integer()` and `clean_surface()`) actually correct?**
  _`run_fusion()` has 13 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Backend observability: structured logs + Sentry (ORA-63)`, `CI/CD Render deploy hook (ORA-64)`, `Dependency vulnerability scan (ORA-65)` to the rest of the system?**
  _174 weakly-connected nodes found - possible documentation gaps or missing edges._