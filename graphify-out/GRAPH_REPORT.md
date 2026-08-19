# Graph Report - oracle_loyers  (2026-08-18)

## Corpus Check
- Large corpus: 165 files · ~561,543 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1435 nodes · 2242 edges · 140 communities (89 shown, 51 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 144 edges (avg confidence: 0.76)
- Token cost: 221,480 input · 0 output

## Community Hubs (Navigation)
- API & Data Cleaning Pipeline
- Scraper Test Fixtures
- CI/CD Workflows
- Coordinate Extraction & Enrichment
- Flask App Routes
- Dead Listing Pruning
- Dead Listing Pruning Browser Tests
- Scraper Compliance & Geocoding
- Price Prediction Feature Building
- Quartier Price History
- Model Drift Monitoring
- Annonces Store Tests
- Playwright Selector Canary Tests
- React App Shell & Error Boundary
- Map Generation (Folium)
- Chat Service Core
- Overpass Cavaliers API
- PDF Report Generation
- Atomic CSV Writing & Checkpointing
- Logging & Observability Config
- Chat Query Text Matching
- Annonces SQLite Store
- Annonce Card UI Components
- Cavaliers Factors Summary
- Frontend Lint/Dev Dependencies
- Quartier Stats Route Tests
- Chat Service Tests
- Dead Listing Detection Utilities
- Model Regression Tests
- Multi-City DAG & Model Rollback
- Request/Response Schemas
- Model Version Archiving
- Model Promotion Metadata
- Data Loader Utilities
- Predict Route Tests
- Quartier Resolution (clean_immo steps)
- Vizzit Scraper Utilities
- SeLoger Lieu Resolution
- Vite/Frontend Build Dependencies
- Rate Limiting Tests
- Frontend Map & UI Dependencies
- Chat UI Components
- SeLoger Scraper
- Scraper Date/Selector Utilities
- Cavaliers Multi-City Merge
- Postal Code Extraction
- CSV Fusion Pipeline
- Model Rollback
- Favorites & Annonces List UI
- ParuVendu Scraper & Site Config
- Chat Request Schema
- Quartier Fuzzy Matching
- Chat Service Fuzzy Matching Tests
- Dead Map Listings Pruning Tests
- Model Promotion Decision
- Zip Code Zone Tests
- Property Type Extraction
- Map Popup Click Tracking Tests
- Result Card & Blob Download UI
- API Client Error Handling
- Quartier Stats Schema
- Price Cleaning Tests
- Surface Cleaning Tests
- Quartier Resolution Core
- Map Ville Path Resolution Tests
- Map Layers Config Tests
- Dead Annonce URL Check Tests
- Frontend NPM Scripts
- Scraper Row Loading Tests
- Chrome Driver Options Tests
- Site Files Config
- PDF Report Route Tests
- Map Bridge Message Tests
- Dead Annonces Pruning Tests
- Runtime Config Tests
- Package Metadata
- Map Component UI
- Click Logging
- Price Prediction Route
- Description Formatting Tests
- Lyon Arrondissement Fetching
- Lille Quartier Hint Tests
- Cavaliers Feature Matching Tests
- Expired Annonce Pruning Tests
- Map Staleness Metadata Tests
- Listing URL Sanitization Tests
- Default Postal Code Fallback
- Chat Route Tests
- Quartier Historique Route Tests
- Geocoding Jitter Tests
- Cavaliers Shape Building Tests
- Lille Quartier Matching Tests
- SeLoger Lieu Fusion Tests
- Map Tooltip Tests
- GeoJSON Layer Loading Tests
- Soft-404 Detection Tests
- SQLite Database Init
- Annonces Store Sync
- Address Extraction Test
- Health Route Tests
- Titre Building Tests
- Annonces Store Sync Tests
- API Contract & Privacy Docs
- Vite Config
- Autoprefixer Dependency
- Vite Logo Asset
- ESLint React Hooks Plugin
- ESLint React Refresh Plugin
- Frontend Entry Point & README
- Globals Dependency
- Playwright Test Dependency
- Tailwind CSS Dependency
- Testing Library Jest DOM
- Testing Library User Event
- React Type Definitions
- React DOM Type Definitions
- Annonce Detail API Route
- Quartier Historique API Route
- React Logo Asset
- Map FlyToBounds Contract
- OWASP Security Review
- OWASP Crypto Review
- OWASP SSRF Review

## God Nodes (most connected - your core abstractions)
1. `ChatService` - 48 edges
2. `AnnoncesStoreTest` - 26 edges
3. `retry_with_backoff()` - 20 edges
4. `pick_user_agent()` - 18 edges
5. `run_fusion()` - 17 edges
6. `ChatServiceTest` - 17 edges
7. `build_report_html()` - 16 edges
8. `match_quartier()` - 16 edges
9. `pick_proxy()` - 16 edges
10. `build_feature_row()` - 15 edges

## Surprising Connections (you probably didn't know these)
- `OWASP A01: Broken Access Control — risk accepted (ORA-46)` --semantically_similar_to--> `ORA-67/93: robots.txt & photo-column compliance review`  [INFERRED] [semantically similar]
  SECURITY_REVIEW.md → LEGAL_DECISIONS.md
- `recheck_ambiguous()` --calls--> `_fetch_all_annonces()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `Cavaliers Enrichment Report` --conceptually_related_to--> `ORA-71/153/154: multi-city genericity, per-city models`  [AMBIGUOUS]
  backend/data/cavaliers_enrichment_report.txt → README.md
- `check_url_status_browser()` --calls--> `looks_like_soft_404()`  [INFERRED]
  scripts/recheck_dead_annonces.py → backend/scripts/prune_dead_annonces.py
- `OWASP A06: Vulnerable and Outdated Components — to fix (minor)` --rationale_for--> `CI job: dependency-scan (pip-audit, npm audit)`  [INFERRED]
  SECURITY_REVIEW.md → .github/workflows/ci.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **OWASP Top 10 (2021) Security Checklist** — security_review_a01_broken_access_control, security_review_a02_crypto_failures, security_review_a03_injection, security_review_a04_insecure_design, security_review_a05_security_misconfiguration, security_review_a06_vulnerable_components, security_review_a07_auth_failures, security_review_a08_integrity_failures, security_review_a09_logging_monitoring, security_review_a10_ssrf [EXTRACTED 1.00]
- **Oracle des Loyers ETL Pipeline (cavaliers + annonces DAGs)** — backend_scripts_api_overpass, backend_scripts_enrich_cavaliers_cp, backend_scripts_merge_cavaliers_villes, backend_scripts_data_fusion, backend_scripts_clean_immo, backend_scripts_train_model, backend_scripts_generate_map [EXTRACTED 1.00]
- **Scraper selector regression-testing pattern (ORA-19 fixtures)** — scripts_tests_test_scraper_extraction_fixtures, scripts_tests_fixtures_century21, scripts_tests_fixtures_orpi, scripts_tests_fixtures_pap, scripts_tests_fixtures_paruvendu, scripts_tests_fixtures_seloger, scripts_tests_fixtures_vizzit [EXTRACTED 1.00]

## Communities (140 total, 51 thin omitted)

### Community 0 - "API & Data Cleaning Pipeline"
Cohesion: 0.07
Nodes (44): GET /api/annonces, GET /api/listings, ORA-86: direct redirect vs confirmation modal, POST /api/annonces/<id>/click, build_shapes_from_cavaliers(), build_titre(), clean_zipcode(), determine_type_local() (+36 more)

### Community 1 - "Scraper Test Fixtures"
Cohesion: 0.07
Nodes (23): Century21 scraper test fixture (HTML), Orpi scraper test fixture (HTML), PAP scraper test fixture (HTML), ParuVendu scraper test fixture (HTML), SeLoger scraper test fixture (HTML), Vizzit scraper test fixture (HTML), bs4_first_attr(), bs4_first_text() (+15 more)

### Community 2 - "CI/CD Workflows"
Cohesion: 0.05
Nodes (43): CI Workflow (ci.yml), CI job: backend (pytest), CI job: dependency-scan (pip-audit, npm audit), CI job: deploy (Render deploy hooks, ORA-64), CI job: e2e (Playwright vs vite preview + Flask), CI job: frontend (lint, build, test), CI job: scrapers (pytest, excludes e2e), Model Drift Monitor Workflow (+35 more)

### Community 3 - "Coordinate Extraction & Enrichment"
Cohesion: 0.08
Nodes (19): extract_coordinates_from_html(), get_gps_from_url(), process_row(), Chemins d'entrée/sortie pour une ville donnée (slug scraping_config.json, ex:…, Coordonnées GPS (lat, lon) trouvées dans le HTML d'une fiche annonce, ou (None,…, Télécharge la page et en extrait les coordonnées GPS réelles., Fonction exécutée par chaque thread, resolve_paths() (+11 more)

### Community 4 - "Flask App Routes"
Cohesion: 0.08
Nodes (31): after_request, chat(), get_annonce_detail(), get_annonces(), get_chat_rate_limit(), get_cors_origins(), get_default_rate_limits(), get_listings() (+23 more)

### Community 5 - "Dead Listing Pruning"
Cohesion: 0.09
Nodes (22): check_url_status(), _fetch_all_annonces(), looks_like_soft_404(), prune_dead_annonces(), Nettoyage ponctuel des annonces mortes dans annonces.db (ORA-134). Le pipeline…, Snapshot complet (id, url, titre) pris avant toute suppression : évite le bug…, Vérifie chaque annonce de `db_path` (DEFAULT_DB_PATH si None) et supprime…, True si `html_text` contient un des `SOFT_404_PATTERNS` (insensible à la casse). (+14 more)

### Community 6 - "Dead Listing Pruning Browser Tests"
Cohesion: 0.09
Nodes (4): CheckUrlStatusBrowserTest, LooksLikeChallengePageTest, LooksLikeValidListingTest, RecheckAmbiguousTest

### Community 7 - "Scraper Compliance & Geocoding"
Cohesion: 0.11
Nodes (17): ORA-46: no authentication on public routes, ORA-67/93: robots.txt & photo-column compliance review, _fetch_geocodage(), geocode_adresse(), load_page(), load_page(), load_page(), _detect_local_chrome_major_version() (+9 more)

### Community 8 - "Price Prediction Feature Building"
Cohesion: 0.11
Nodes (16): build_feature_row(), compute_distance_features(), haversine_distance_m(), normalize_type_bien(), normalize_type_local(), Construit le vecteur de features attendu par le modèle à partir du payload…, Normalise un type de bien utilisateur (T1, studio, T4+...) vers une catégorie…, Normalise le type de bien brut (Appartement/Maison/Studio), 'Appartement' par… (+8 more)

### Community 9 - "Quartier Price History"
Cohesion: 0.15
Nodes (11): compute_price_history(), _filter_quartier(), Calcule l'évolution du prix moyen/m² pour `quartier` à travers tous les…, Résolution d'une recherche utilisateur (texte libre) en un sous-ensemble du…, Sous-ensemble de `df` correspondant à la recherche `quartier_input`, et les…, resolve_quartier_filter(), ComputePriceHistoryTest, ORA-110 : même matching partagé (fuzzy) que /api/quartier-stats, au lieu d'un… (+3 more)

### Community 10 - "Model Drift Monitoring"
Cohesion: 0.12
Nodes (14): build_drift_report(), compute_drift(), _ks_result(), _numeric_feature_columns(), Point d'entrée : compare `data_path` (données actuelles) au snapshot de…, Compare chaque feature numérique du modèle (et la cible `prix`, en proxy de…, Choisit la ligne du manifest à utiliser comme référence : celle d'il y a…, run() (+6 more)

### Community 12 - "Playwright Selector Canary Tests"
Cohesion: 0.12
Nodes (19): expectedFailure, assert_selector_canary(), Century21SelectorCanaryTest, find_cards(), find_first_locator_text(), new_page(), OrpiSelectorCanaryTest, PapSelectorCanaryTest (+11 more)

### Community 13 - "React App Shell & Error Boundary"
Cohesion: 0.12
Nodes (8): App(), makePanelFallback(), MOBILE_TABS, useIsDesktop(), ErrorBoundary, PriceHistory(), SearchForm(), computeBoundsForQuartiers()

### Community 14 - "Map Generation (Folium)"
Cohesion: 0.11
Nodes (24): build_bridge_message_script(), build_immo_popup_html(), build_immo_tooltip_html(), filter_by_ville(), load_geojson_file(), load_layers_config(), main(), Ne garde que les URL http(s) valides issues des données scrapées externes. (+16 more)

### Community 16 - "Overpass Cavaliers API"
Cohesion: 0.13
Nodes (14): get_cavaliers_data(), merge_cavaliers(), Lit le nom de la ville active (`villes.<ville_active>.nom`) depuis…, Résout le nom d'affichage d'une ville depuis son slug, indépendamment de…, Fusionne les cavaliers déjà connus avec les cavaliers fraîchement extraits.…, Récupère la liste complète des lieux pour chaque catégorie et fusionne avec le…, resolve_active_city_name(), resolve_city_name() (+6 more)

### Community 17 - "PDF Report Generation"
Cohesion: 0.16
Nodes (10): build_report_html(), _escape(), _format_date(), _format_price(), Rend le rapport d'estimation en PDF (bytes), via WeasyPrint (ORA-121)., Construit le HTML source du rapport PDF (fonction pure, testable indépendamment…, render_estimation_pdf(), BuildReportHtmlTest (+2 more)

### Community 18 - "Atomic CSV Writing & Checkpointing"
Cohesion: 0.12
Nodes (14): atomic_csv_writer(), Écrit dans un fichier temporaire à côté de `output_path` et ne remplace ce…, checkpoint(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, checkpoint(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un…, checkpoint(), Persiste l'état courant de `rows_by_lien` (écriture atomique complète, pas un… (+6 more)

### Community 19 - "Logging & Observability Config"
Cohesion: 0.10
Nodes (7): configure_logging(), init_sentry(), Configuration centralisée de l'observabilité applicative du backend (ORA-63).…, Configure le logger racine du process avec un format structuré et un niveau…, Initialise sentry-sdk pour capturer automatiquement les exceptions non gérées…, LoggingConfigTest, Vérifie le logger structuré centralisé (ORA-63) : niveau par défaut, prise en…

### Community 20 - "Chat Query Text Matching"
Cohesion: 0.20
Nodes (6): compact_text(), normalize_text(), searchable_text(), CompactTextTest, NormalizeTextTest, SearchableTextTest

### Community 21 - "Annonces SQLite Store"
Cohesion: 0.17
Nodes (14): delete_annonce(), get_annonce_by_id(), get_annonce_by_url(), get_connection(), list_annonces(), Store SQLite pour la table `annonces` (ORA-81/82/83). Persiste les annonces…, Insère une nouvelle annonce, ou met à jour l'annonce existante de même `url`…, Liste paginée des annonces, filtrable par ville et/ou quartier (ORA-84). `sort`… (+6 more)

### Community 22 - "Annonce Card UI Components"
Cohesion: 0.20
Nodes (13): AnnonceCard(), AnnonceIllustration(), formatPrice(), getTypeCategory(), ILLUSTRATION_BY_CATEGORY, KNOWN_CATEGORIES, baseAnnonce, AnnonceDetailModal() (+5 more)

### Community 23 - "Cavaliers Factors Summary"
Cohesion: 0.24
Nodes (8): list_poi_types(), _phrase_for(), Introspecte les colonnes `dist_<catégorie>_<poi>` réellement présentes dans…, Résume les 4 "Cavaliers" (Vice, Gentrification, Nuisance, Superstition) pour un…, summarize_cavaliers(), ListPoiTypesTest, _row(), SummarizeCavaliersTest

### Community 24 - "Frontend Lint/Dev Dependencies"
Cohesion: 0.12
Nodes (17): eslint, @eslint/js, devDependencies, eslint, @eslint/js, jsdom, postcss, @testing-library/react (+9 more)

### Community 25 - "Quartier Stats Route Tests"
Cohesion: 0.12
Nodes (5): QuartierStatsRouteTest, ORA-111 : suggestions renvoyées quand plusieurs quartiers sont proches., ORA-122/ORA-128 : quelques biens comparables réels (échantillon), pour le…, ORA-110 : le endpoint utilise désormais le matching partagé (fuzzy) au lieu…, ORA-111 : message différencié aucun résultat vs quartier ambigu.

### Community 27 - "Dead Listing Detection Utilities"
Cohesion: 0.21
Nodes (9): prune_dead_map_listings(), Vérifie chaque url de `csv_path` (HTTP puis navigateur headless pour les…, Re-teste chaque annonce de `db_path` en HTTP, puis escalade au navigateur…, recheck_ambiguous(), pick_proxy(), pick_user_agent(), Choisit un User-Agent réaliste au hasard dans le pool configuré (rotation,…, Choisit un proxy au hasard dans le pool configuré (ORA-18), désactivé par… (+1 more)

### Community 28 - "Model Regression Tests"
Cohesion: 0.17
Nodes (8): ModelRegressionTest, PredictEndpointRegressionTest, _prepare_features(), ORA-154 : un modèle XGBoost distinct par ville plutôt que `ville` en feature…, Non-régression explicite du bug corrigé par ORA-30 : /api/predict renvoyait…, Reproduit exactement le prétraitement de train_model.py (ORA-154, ORA-155),…, Remplace backend/scripts/test_prediction.py (script manuel, échantillon…, VilleExcludedFromFeaturesTest

### Community 29 - "Multi-City DAG & Model Rollback"
Cohesion: 0.21
Nodes (11): L'Oracle des Loyers — DAG Annonces (scraping + modèle) Fusionne les annonces…, GET /api/health, Cavaliers Enrichment Report, load_declared_villes(), Villes déclarées dans scraping_config.json (ORA-71) : ajouter une ville au JSON…, Restaure `model_path` à la version archivée `model_version`. `versions_dir`…, rollback_to(), Entraîne, évalue et (si le garde-fou de régression le permet) promeut un modèle… (+3 more)

### Community 30 - "Request/Response Schemas"
Cohesion: 0.25
Nodes (8): ComparableSchema, FacteurSchema, PdfReportRequestSchema, PredictRequestSchema, PriceHistoryPointSchema, Schémas de validation des payloads pour les routes Flask actives (/api/chat,…, PredictRequestSchemaTest, BaseModel

### Community 31 - "Model Version Archiving"
Cohesion: 0.21
Nodes (7): archive_model_version(), Conserve une copie du modèle sous un nom versionné (hash du binaire), pour…, Archive un instantané content-addressé de `csv_path` dans `snapshots_dir` et…, _sha256_of_file(), snapshot_dataset(), ArchiveModelVersionTest, SnapshotDatasetTest

### Community 32 - "Model Promotion Metadata"
Cohesion: 0.20
Nodes (8): load_active_model_metadata(), Lit les métadonnées (`metrics`, `model_version`) du modèle actuellement actif…, Écrit `<model_path>.meta.json`, référençant explicitement la version des…, record_model_metadata(), RecordModelMetadataTest, LoadActiveModelMetadataTest, PromotionGuardTriggersRollbackTest, Reproduit le flux de décision de train_model.py au niveau des fonctions qu'il…

### Community 33 - "Data Loader Utilities"
Cohesion: 0.18
Nodes (9): DataLoader, Charge le CSV en mémoire et applique un nettoyage de base., Renvoie le DataFrame brut., clean_input_data(), format_prediction_response(), guess_room_count_smart(), Nettoie les données entrantes., Devine le type de logement (T1, T2...) basé sur la surface si l'information est… (+1 more)

### Community 34 - "Predict Route Tests"
Cohesion: 0.14
Nodes (4): PredictRouteTest, ORA-154 : la panne d'un modèle ne doit plus dégrader toutes les villes — seule…, ORA-152 : un modèle qui prédit un loyer négatif (ex. pickle XGBoost désérialisé…, Un loyer exactement nul n'est pas plus plausible qu'un loyer négatif.

### Community 36 - "Vizzit Scraper Utilities"
Cohesion: 0.21
Nodes (13): find_first_image_url(), Cherche la première balise <img> correspondant à l'un des `selectors` dans…, apply_price_band(), build_page_url(), decode_data_o_link(), find_attr(), find_text(), load_page() (+5 more)

### Community 37 - "SeLoger Lieu Resolution"
Cohesion: 0.24
Nodes (5): normalize_lieu(), CP réel déduit du champ `Lieu` de SeLoger, ou du premier segment d'`Infos`…, resolve_seloger_lieu(), ORA-71 POC follow-up : le champ Lieu de SeLoger contient parfois une vraie…, ResolveSelogerLieuTest

### Community 39 - "Rate Limiting Tests"
Cohesion: 0.15
Nodes (4): RateLimitBehaviorTest, RateLimitConfigTest, ORA-118 : le frontend a besoin de X-RateLimit-Remaining pour afficher un…, Sans Access-Control-Expose-Headers, fetch() côté frontend ne peut pas lire ces…

### Community 40 - "Frontend Map & UI Dependencies"
Cohesion: 0.15
Nodes (13): dependencies, leaflet, react, react-dom, react-leaflet, react-markdown, remark-gfm, leaflet (+5 more)

### Community 41 - "Chat UI Components"
Cohesion: 0.28
Nodes (7): buildChatContext(), ChatOracle(), DEFAULT_MESSAGES, describeChatError(), ApiError, loadChatHistory(), saveChatHistory()

### Community 42 - "SeLoger Scraper"
Cohesion: 0.18
Nodes (8): load_page(), parse_title_attribute(), Parse 'Type - Lieu - Prix - Infos' format. Returns None if format unrecognized., canonical_url(), Retire la query string et le fragment d'une URL d'annonce. Régression réelle…, Décide si la pagination d'un scraper doit continuer après une page où…, should_continue_pagination(), ShouldContinuePaginationTest

### Community 43 - "Scraper Date/Selector Utilities"
Cohesion: 0.21
Nodes (7): find_first(), Date du jour (UTC) au format ISO — utilisée pour horodater la colonne…, Essaie chaque sélecteur CSS de `selectors` dans l'ordre sur `element` et…, today_iso(), FakeElement, FindFirstTest, TodayIsoTest

### Community 44 - "Cavaliers Multi-City Merge"
Cohesion: 0.26
Nodes (5): L'Oracle des Loyers — DAGs Cavaliers (POI), un par ville Scrape les points…, merge_all_villes(), L'Oracle des Loyers — Fusion des cavaliers par ville Concatène les…, MergeAllVillesTest, ORA-153 : avant ce script, rien ne produisait cavaliers_all.csv automatiquement…

### Community 45 - "Postal Code Extraction"
Cohesion: 0.29
Nodes (3): extract_postal_code(), Normalise le CP (69XXX ou 59XXX). `default_cp` est le repli utilisé quand aucun…, ExtractPostalCodeTest

### Community 46 - "CSV Fusion Pipeline"
Cohesion: 0.24
Nodes (6): Fusionne les CSV scrapés en base_de_donnees_immo_complet.csv. Par défaut…, run_fusion(), ORA-134 : la colonne DerniereVue des scrapers doit survivre à la fusion sous le…, ORA-153 : chaque DAG annonces tourne désormais indépendamment par ville.…, RunFusionDateDernierScanTest, RunFusionPerVilleTest

### Community 47 - "Model Rollback"
Cohesion: 0.17
Nodes (6): Revenir à une version antérieure du modèle price_predictor_<ville>.pkl sans…, price_predictor_<ville>.pkl pour le slug donné — un modèle distinct par ville…, resolve_model_path(), ORA-154 : un modèle distinct par ville — price_predictor_<ville>.pkl, pas un…, ResolveModelPathTest, RollbackModelTest

### Community 48 - "Favorites & Annonces List UI"
Cohesion: 0.32
Nodes (5): AnnoncesList(), SORT_OPTIONS, useFavorites(), loadFavoriteIds(), saveFavoriteIds()

### Community 49 - "ParuVendu Scraper & Site Config"
Cohesion: 0.20
Nodes (6): fetch_page(), find_image_bs4(), Équivalent BeautifulSoup de `scraper_utils.find_first_image_url` (pas de…, load_site_config(), Charge la config de la ville active (URL de recherche, paramètre de pagination)…, LoadSiteConfigTest

### Community 50 - "Chat Request Schema"
Cohesion: 0.27
Nodes (3): ChatRequestSchema, ChatRequestSchemaTest, field_validator

### Community 51 - "Quartier Fuzzy Matching"
Cohesion: 0.29
Nodes (4): match_quartier(), Fait correspondre `query` (texte libre, éventuellement fautif ou noyé dans une…, MatchQuartierTest, ORA-109 : tolérance aux fautes de frappe sur les quartiers connus.

### Community 52 - "Chat Service Fuzzy Matching Tests"
Cohesion: 0.20
Nodes (4): ExtractLocationsFuzzyMatchingTest, FakeClient, FakeModels, ORA-109 : la recherche de quartier tolère les fautes de frappe.

### Community 54 - "Model Promotion Decision"
Cohesion: 0.31
Nodes (4): decide_promotion(), Décide si un modèle nouvellement entraîné doit remplacer le modèle actif.…, DecidePromotionTest, ORA-34 : un ré-entraînement automatique (DAG Airflow quotidien) ne doit jamais…

### Community 55 - "Zip Code Zone Tests"
Cohesion: 0.20
Nodes (3): GetPointForZipcodeZonesLimitrophesTest, StepIdsTest, StepTypesTest

### Community 56 - "Property Type Extraction"
Cohesion: 0.36
Nodes (3): extract_type(), Détermine le type de bien (Maison, Appartement, Studio, Coloc)., ExtractTypeTest

### Community 58 - "Result Card & Blob Download UI"
Cohesion: 0.36
Nodes (5): loadAnnonces(), ResultCard(), baseData, describeApiError(), downloadBlob()

### Community 59 - "API Client Error Handling"
Cohesion: 0.33
Nodes (7): API_URL, apiFetchOptions(), classifyResponseError(), fetchWithClassification(), getApiBaseUrl(), LOCAL_HOSTS, parseRateLimitHeaders()

### Community 61 - "Price Cleaning Tests"
Cohesion: 0.39
Nodes (3): clean_price_integer(), Convertit en entier (supprime €, cc, espaces, points)., CleanPriceIntegerTest

### Community 62 - "Surface Cleaning Tests"
Cohesion: 0.39
Nodes (3): clean_surface(), Extrait le nombre avant 'm2'., CleanSurfaceTest

### Community 63 - "Quartier Resolution Core"
Cohesion: 0.36
Nodes (4): Résout `query` vers le libellé canonique d'un quartier de `known_quartiers`, ou…, resolve_quartier(), ORA-110 : point d'entrée unique utilisé par /api/quartier-stats, /api/quartier-…, ResolveQuartierTest

### Community 65 - "Map Layers Config Tests"
Cohesion: 0.25
Nodes (3): LoadLayersConfigTest, ORA-130 : la liste des calques (nom Folium/TOGGLE_LAYER, visibilité par défaut,…, Non-régression ORA-130 : le refactor ne doit rien changer à l'état initial des…

### Community 67 - "Frontend NPM Scripts"
Cohesion: 0.25
Nodes (8): scripts, build, dev, lint, preview, test, test:e2e, test:watch

### Community 68 - "Scraper Row Loading Tests"
Cohesion: 0.39
Nodes (3): load_existing_rows(), Charge les lignes déjà connues (écrites lors d'un run précédent) et l'ensemble…, LoadExistingRowsTest

### Community 70 - "Site Files Config"
Cohesion: 0.29
Nodes (4): Config des fichiers 'classiques' (hors Vizzit) pour une ville donnée, à partir…, site_files_config(), LoadDeclaredVillesTest, SiteFilesConfigTest

### Community 72 - "Map Bridge Message Tests"
Cohesion: 0.29
Nodes (3): BuildBridgeMessageScriptTest, Contrat postMessage carte (ORA-125) : la carte générée ne doit traiter un…, ORA-105 : recentrage sur la bounding-box des résultats filtrés.

### Community 75 - "Package Metadata"
Cohesion: 0.29
Nodes (6): name, overrides, vite, private, type, version

### Community 76 - "Map Component UI"
Cohesion: 0.38
Nodes (4): LAYER_MAPPING, layersByGroup(), MapComponent(), VILLE_CENTERS

### Community 77 - "Click Logging"
Cohesion: 0.33
Nodes (6): log_annonce_click(), Journalise un clic sortant vers l'annonce source (ORA-91), et renvoie le…, count_clicks(), log_click(), Journalise un clic sortant vers l'annonce `annonce_id` (ORA-91). Utilisé pour…, Nombre de clics enregistrés pour `annonce_id` (ORA-92).

### Community 78 - "Price Prediction Route"
Cohesion: 0.33
Nodes (6): predict(), Prédiction de prix via le modèle Machine Learning (XGBoost) chargé en mémoire.…, estimate_confidence(), is_physically_implausible_price(), True si `estimated_price` ne peut pas être un loyer réel (<= 0 €)., Niveau de confiance basé sur le nombre de comparables réels (quartier + type)…

### Community 79 - "Description Formatting Tests"
Cohesion: 0.47
Nodes (3): format_description(), Nettoie la description pour l'affichage final., FormatDescriptionTest

### Community 80 - "Lyon Arrondissement Fetching"
Cohesion: 0.53
Nodes (5): fetch_arrondissement_boundary(), main(), ordinal_label(), Récupère une fois les polygones des 9 arrondissements de Lyon (Nominatim/ OSM)…, Récupère le polygone GeoJSON d'un arrondissement de Lyon via Nominatim.

### Community 86 - "Default Postal Code Fallback"
Cohesion: 0.50
Nodes (3): CP de repli pour une ville (cf. extract_postal_code). Fail-fast plutôt que de…, resolve_default_cp(), ResolveDefaultCpTest

### Community 96 - "SQLite Database Init"
Cohesion: 0.50
Nodes (4): get_db_connection(), init_db(), Initialise la table 'annonces' si elle n'existe pas., Crée une connexion à la base de données.

### Community 97 - "Annonces Store Sync"
Cohesion: 0.50
Nodes (4): Alimente la table SQLite `annonces` (services/annonces_store.py) à partir du…, step_sync_annonces_store(), init_db(), Crée les tables `annonces` et `clics` si elles n'existent pas encore (ORA-81,…

### Community 98 - "Address Extraction Test"
Cohesion: 0.67
Nodes (3): extract_address_hybrid(), is_context_safe(), Vérifie si le texte précédant l'adresse contient des mots interdits (proche,…

### Community 102 - "API Contract & Privacy Docs"
Cohesion: 0.67
Nodes (3): API Contract (Oracle des Loyers), Data Retention Policy (Oracle des Loyers), IP address retention for rate limiting (in-memory only)

## Ambiguous Edges - Review These
- `ORA-71/153/154: multi-city genericity, per-city models` → `Cavaliers Enrichment Report`  [AMBIGUOUS]
  backend/data/cavaliers_enrichment_report.txt · relation: conceptually_related_to

## Knowledge Gaps
- **73 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+68 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **51 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `ORA-71/153/154: multi-city genericity, per-city models` and `Cavaliers Enrichment Report`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `ORA-33: model/data drift monitoring` connect `CI/CD Workflows` to `Multi-City DAG & Model Rollback`, `Model Version Archiving`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `ChatService` connect `Chat Service Core` to `Chat Service Tests`, `Flask App Routes`, `Chat Query Text Matching`, `Chat Service Fuzzy Matching Tests`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `CI job: drift-monitor (weekly cron, GitHub issue alert)` connect `CI/CD Workflows` to `Model Drift Monitoring`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `ChatService` (e.g. with `ChatServiceTest` and `ExtractLocationsFuzzyMatchingTest`) actually correct?**
  _`ChatService` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _73 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `API & Data Cleaning Pipeline` be split into smaller, more focused modules?**
  _Cohesion score 0.06767676767676768 - nodes in this community are weakly interconnected._