import { useState, useEffect, useMemo } from 'react';
import ResultCard from './components/ResultCard';
import PriceHistory from './components/PriceHistory';
import MapComponent from './components/MapComponent';
import CalquesView from './components/CalquesView';
import ChatOracle from './components/ChatOracle';
import AnnoncesList from './components/AnnoncesList';
import ErrorBoundary from './components/ErrorBoundary';
import Topbar from './components/Topbar';
import HomeOverview from './components/HomeOverview';
import CavaliersDetail from './components/CavaliersDetail';
import QuartierAmbigu from './components/QuartierAmbigu';
import PanelNav from './components/PanelNav';
import PanelSheet from './components/PanelSheet';
import SearchForm from './components/SearchForm';
import AnnonceDetailContent from './components/AnnonceDetailContent';
import { useAnnonceDetail } from './hooks/useAnnonceDetail';
import { api, describeApiError } from './services/api';
import { computeBoundsForQuartiers } from './services/mapBounds';
import { computeHomeStats } from './services/homeStats';
import { computeQuartierOptions } from './services/quartierStats';
import { computeLatestDataDate } from './services/latestDataDate';
import { useLayerVisibility } from './hooks/useLayerVisibility';
import { useCavaliersRadius } from './hooks/useCavaliersRadius';
import { useLayerCounts } from './hooks/useLayerCounts';
import { CAVALIERS_RADIUS_M } from './services/cavaliersDisplay';
import { loadCavaliersRadiusM, saveCavaliersRadiusM } from './services/cavaliersRadiusStorage';

// ORA-123 : fallback compact par panneau, pour ne pas faire planter tout
// l'écran (comportement par défaut d'ErrorBoundary) quand une seule zone
// (carte, oracle, chat) rencontre une erreur de rendu. Renvoie la fonction
// (reset) => élément attendue par ErrorBoundary#fallback.
function makePanelFallback(label) {
  return (reset) => (
    <div className="w-full h-full flex flex-col items-center justify-center gap-3 p-6 text-center bg-ink-900/50">
      <p className="text-xs text-ink-muted max-w-xs">
        {label} a rencontré une erreur d'affichage.
      </p>
      <button
        type="button"
        onClick={reset}
        className="px-3 py-1.5 bg-ink-800 hover:bg-ink-700 rounded-lg text-ink text-[10px] uppercase tracking-widest font-bold transition-colors"
      >
        Réessayer
      </button>
    </div>
  );
}

// Correspond au breakpoint `md` de Tailwind : au-delà, les deux panneaux
// (carte + oracle) restent visibles simultanément, donc la carte doit
// toujours être montée. En dessous, elle ne doit se monter que si son
// onglet mobile est actif, pour éviter de charger l'iframe (4 Mo) inutilement.
const DESKTOP_MEDIA_QUERY = '(min-width: 768px)';
const MOBILE_TABS = ['carte', 'oracle', 'annonces'];
const PANEL_SHEET_ID = 'panel-sheet';

function useIsDesktop() {
  const [isDesktop, setIsDesktop] = useState(
    () => window.matchMedia(DESKTOP_MEDIA_QUERY).matches
  );

  useEffect(() => {
    const mql = window.matchMedia(DESKTOP_MEDIA_QUERY);
    const handleChange = (e) => setIsDesktop(e.matches);
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, []);

  return isDesktop;
}

function App() {
  const [result, setResult] = useState(null);
  const [priceHistory, setPriceHistory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // ORA-176 : { query, suggestions, typeLocal, surfaceInput } quand le scan
  // a échoué sur une ambiguïté (plusieurs quartiers assez proches) — jamais
  // en même temps que `result`/`error` (handleScan les remet à zéro à chaque
  // nouvelle tentative).
  const [ambiguousQuartier, setAmbiguousQuartier] = useState(null);
  const [chatContext, setChatContext] = useState(null);
  const [mapCenter, setMapCenter] = useState(null);
  // ORA-105 : bounding-box des annonces actuellement affichées dans
  // AnnoncesList (colonne Oracle desktop). undefined = pas encore calculée
  // (la carte ne réagit pas) ; null = calculée mais sans coordonnée
  // exploitable (repli explicite sur le centre-ville dans MapComponent).
  const [mapBounds, setMapBounds] = useState(undefined);
  const [listings, setListings] = useState([]);
  // ORA-179 : état d'erreur du fetch /api/listings + jeton incrémenté par le
  // bouton "Réessayer" de l'Accueil pour relancer la requête (cf. useEffect
  // de chargement des listings plus bas).
  const [listingsError, setListingsError] = useState(null);
  const [listingsRetryToken, setListingsRetryToken] = useState(0);
  const [activeTab, setActiveTab] = useState('oracle');
  // ORA-127 : lien direct depuis un quartier scanné vers ses annonces —
  // `token` change à chaque clic (même quartier compris) pour que
  // AnnoncesList redéclenche le saut à chaque fois, cf. son prop `focusedQuartier`.
  const [focusedQuartier, setFocusedQuartier] = useState(null);
  // Chat en bulle flottante superposée à l'écran, MOBILE UNIQUEMENT (ORA-178 :
  // sur desktop, Immotep vit désormais dans la vue "Immotep" du rail — voir
  // `activeView` ci-dessous). Fermé par défaut pour laisser "Détails du
  // quartier" toute la hauteur de la colonne Oracle mobile.
  const [isChatOpen, setIsChatOpen] = useState(false);
  // ORA-178 : vue active du rail "classeur" du panneau droit (desktop
  // uniquement — mobile garde ses 3 onglets historiques ci-dessus, `activeTab`).
  const [activeView, setActiveView] = useState('accueil');
  // ORA-178 : annonce sélectionnée (clic "Détails" dans la liste, ou clic sur
  // un marker de la carte via ANNONCE_CLICK) — alimente la vue "Fiche".
  const [selectedAnnonceId, setSelectedAnnonceId] = useState(null);
  // ORA-167/179 : "+ Surface" (ResultCard, `onAddSurface`) — bascule sur la
  // vue Recherche et demande à SearchForm de focus directement le champ
  // Surface plutôt que Quartier (déjà rempli). Remis à `false` dès qu'on
  // quitte la vue Recherche, pour qu'une visite ultérieure (rail direct)
  // n'hérite pas de ce focus ciblé.
  const [focusSurfaceNext, setFocusSurfaceNext] = useState(false);
  // ORA-178 : visibilité des calques — remontée depuis MapComponent (qui
  // devient un composant contrôlé) pour qu'App en soit l'unique source de
  // vérité, partagée par la vue "Calques" du rail ET le panneau flottant
  // mobile (hook dédié, testable indépendamment : useLayerVisibility.test.js).
  const { layers: layerVisibility, toggleLayer, resetLayers, setLayersVisible } = useLayerVisibility();
  // Vue "Calques", sélecteur de rayon (Aucun/300 m/500 m/1 km) : remis à
  // 500 m à chaque nouveau scan (cf. handleScan) pour repartir du rayon par
  // défaut plutôt que d'hériter du dernier rayon consulté sur un autre
  // quartier. Le choix (y compris "Aucun", `null`) est mémorisé en
  // localStorage — seule la valeur initiale au montage en dépend, un nouveau
  // scan garde la remise à 500 m ci-dessus inchangée.
  const [cavaliersRadiusM, setCavaliersRadiusM] = useState(() => loadCavaliersRadiusM(CAVALIERS_RADIUS_M));
  useEffect(() => {
    saveCavaliersRadiusM(cavaliersRadiusM);
  }, [cavaliersRadiusM]);
  // Sélecteur de ville (ORA-71 POC) : ne change que la carte affichée et le
  // bornage des recherches quartier/historique — les CSV/codes postaux
  // Lyon/Lille restant jamais ambigus entre les deux villes.
  const [ville, setVille] = useState('lyon');
  // ORA-171 : mae/dataset_size par ville (backend/models/training_metrics_*),
  // pour ne jamais coder en dur "± 175 €" / "entraîné sur 890 annonces".
  const [health, setHealth] = useState(null);
  const isDesktop = useIsDesktop();
  const shouldMountMap = isDesktop || activeTab === 'carte';
  // ORA-170 : agrégats "Le marché en un coup d'œil", affichés tant qu'aucun
  // quartier n'a été scanné (état par défaut de la colonne Oracle).
  const homeStats = useMemo(() => computeHomeStats(listings, ville), [listings, ville]);
  // ORA-176 : liste des quartiers pour la palette de recherche de la topbar.
  const quartierOptions = useMemo(() => computeQuartierOptions(listings, ville), [listings, ville]);
  // ORA-171 : badge "Données au" de la topbar, repris sur toutes les vues.
  const latestDataDate = useMemo(() => computeLatestDataDate(listings, ville), [listings, ville]);
  // ORA-183 (v3) : compteurs par calque (bloc "Annonces" de la vue Calques),
  // même hook que le panneau flottant mobile (MapComponent) — un seul fetch
  // par composant qui en a besoin, jamais recalculé depuis `listings`.
  const layerCounts = useLayerCounts(ville);
  // ORA-178 : "Estimation personnalisée" (maquette 03) — vraie prédiction
  // modèle disponible, cf. ResultCard.jsx (même condition).
  const hasModelEstimate = Boolean(result?.surface) && Boolean(result?.confiance);
  // ORA-178 : fiche annonce (vue "Fiche") — fetch/actions partagés avec la
  // modale (AnnonceDetailModal), jamais recalculés en double. Ne dépend pas
  // de `activeView` : la fiche reste en cache tant qu'une autre annonce n'a
  // pas été sélectionnée, même après avoir changé de vue.
  const ficheDetail = useAnnonceDetail(selectedAnnonceId);
  // Vue "Calques" : détail des 4 cavaliers pour `cavaliersRadiusM` — reprend
  // result.cavaliersDetail/facteurs (500 m, déjà fournis par le scan) sans
  // appel réseau, sauf si un autre rayon a été choisi (GET /api/cavaliers,
  // mis en cache par (quartier, rayon) — hooks/useCavaliersRadius.js).
  const cavaliersRadius = useCavaliersRadius({
    quartier: result?.quartier,
    center: result?.center,
    ville,
    radiusM: cavaliersRadiusM,
    defaultDetail: result?.cavaliersDetail,
    defaultFacteurs: result?.facteurs,
  });

  // ORA-105 : chargé une fois, sert à résoudre les coordonnées des quartiers
  // des annonces affichées (AnnoncesList n'a pas de latitude/longitude), et
  // à calculer les agrégats "Le marché en un coup d'œil" (Accueil). Un échec
  // silencieux ici (ex : quota /api/listings dépassé au chargement) laissait
  // auparavant l'Accueil afficher "0 ARRONDISSEMENTS"/"—" indéfiniment, sans
  // recours ni explication — `listingsError` + `listingsRetryToken`
  // permettent d'afficher un message clair et de relancer la requête.
  useEffect(() => {
    let cancelled = false;
    setListingsError(null);

    api.getListings()
      .then((data) => {
        if (!cancelled) setListings(data || []);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Listings indisponibles pour le recentrage carte :", err);
        setListingsError(describeApiError(err));
      });

    return () => {
      cancelled = true;
    };
  }, [listingsRetryToken]);

  // ORA-171 : chargé une fois, indépendant du quartier scanné (les métriques
  // du modèle ne changent qu'à un ré-entraînement, pas à chaque scan).
  useEffect(() => {
    let cancelled = false;

    api.getHealth()
      .then((data) => {
        if (!cancelled) setHealth(data);
      })
      .catch((err) => console.error("Métriques modèle indisponibles :", err));

    return () => {
      cancelled = true;
    };
  }, []);

  // ORA-179 : raccourci "/" — ouvre la vue Recherche et focus le champ
  // Quartier (SearchForm s'autofocus au montage), sauf si l'utilisateur est
  // déjà en train de saisir du texte ailleurs (jamais d'interception d'une
  // frappe "/" légitime dans un champ). Desktop uniquement (rail) : sans
  // effet utile sur mobile (pas de vue "Recherche" séparée, formulaire déjà
  // visible en permanence dans la colonne Oracle).
  useEffect(() => {
    if (!isDesktop) return;

    const handleKeyDown = (e) => {
      if (e.key !== '/') return;
      const target = e.target;
      const isTextInput = target instanceof HTMLElement && (
        target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable
      );
      if (isTextInput) return;
      e.preventDefault();
      setActiveView('recherche');
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isDesktop]);

  const handleAnnoncesItemsChange = (items) => {
    const quartiers = [...new Set(items.map((item) => item.quartier).filter(Boolean))];
    setMapBounds(computeBoundsForQuartiers(listings, quartiers));
  };

  // ORA-127 : "Voir les annonces de ce quartier" (ResultCard) — présélectionne
  // le filtre quartier d'AnnoncesList et bascule sur l'onglet Annonces en
  // mobile, et sur la vue "Annonces" du rail en desktop (ORA-178).
  const handleViewAnnonces = (quartier) => {
    setFocusedQuartier({ quartier, token: Date.now() });
    setActiveTab('annonces');
    setActiveView('annonces');
  };

  // ORA-178 : sélection d'une annonce (bouton "Détails" de la liste, ou clic
  // sur un marker de la carte via le contrat postMessage ANNONCE_CLICK) —
  // bascule sur la vue "Fiche" du rail, qui affiche son détail complet.
  const handleSelectAnnonce = (id) => {
    setSelectedAnnonceId(id);
    setActiveView('fiche');
  };

  // ORA-167/179 : "+ Surface" (ResultCard) — sur mobile, SearchForm est déjà
  // monté en permanence dans la colonne Oracle : on se contente de lui
  // donner le focus. Sur desktop, la vue Recherche n'est montée que si
  // active : on y bascule et on lui indique (via `focusSurfaceNext`) de
  // focus directement le champ Surface au montage plutôt que Quartier
  // (déjà rempli depuis le dernier `result`).
  const handleAddSurface = () => {
    // ORA-179 : la colonne Oracle mobile garde SearchForm monté en
    // permanence (masqué en CSS sur desktop via `md:hidden`, pas démonté) —
    // `getElementById` seul le retrouverait même sur desktop où il est
    // invisible. `offsetParent` (null si l'élément ou un ancêtre est
    // `display:none`) distingue une instance réellement affichée (mobile)
    // d'une instance simplement présente dans le DOM (desktop, masquée).
    const existingSurfaceInput = document.getElementById('searchform-surface');
    if (existingSurfaceInput && existingSurfaceInput.offsetParent !== null) {
      existingSurfaceInput.focus();
      return;
    }
    setFocusSurfaceNext(true);
    setActiveView('recherche');
  };

  // Consomme `focusSurfaceNext` dès qu'on quitte la vue Recherche, pour
  // qu'une visite ultérieure (rail direct, sans passer par "+ Surface")
  // n'hérite pas de ce focus ciblé.
  useEffect(() => {
    if (activeView !== 'recherche' && focusSurfaceNext) {
      setFocusSurfaceNext(false);
    }
  }, [activeView, focusSurfaceNext]);

  const handleScan = async (quartier, typeLocal, surfaceInput) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPriceHistory(null);
    setAmbiguousQuartier(null);
    // Nouveau scan : repart du rayon par défaut plutôt que d'hériter du
    // dernier rayon consulté sur un autre quartier (vue "Calques").
    setCavaliersRadiusM(CAVALIERS_RADIUS_M);
    // ORA-179 : lancer un scan bascule immédiatement sur la vue "Scan" du
    // rail (desktop), ou "Estimation" si une surface a été saisie — connu
    // synchroniquement, pas besoin d'attendre la réponse du serveur. Sans
    // effet sur mobile, qui garde ses propres onglets.
    const initialSurfaceValue = parseFloat(surfaceInput);
    setActiveView(Number.isFinite(initialSurfaceValue) && initialSurfaceValue > 0 ? 'estimation' : 'scan');

    try {
      const data = await api.getQuartierStats(quartier, typeLocal, ville);

      if (!data.found) {
        // ORA-176 (ORA-111 côté backend) : plusieurs quartiers assez proches
        // de la saisie — l'Oracle demande explicitement plutôt que deviner.
        // `typeLocal`/`surfaceInput` mémorisés pour rejouer le scan choisi
        // avec le même contexte (Topbar ne les expose pas à ce niveau).
        if (data.ambiguous && data.suggestions?.length) {
          setAmbiguousQuartier({ query: quartier, suggestions: data.suggestions, typeLocal, surfaceInput });
        } else {
          setError(data.message || "Aucun résultat trouvé.");
        }
        return;
      }

      // Par défaut, l'estimation affichée est la moyenne réelle du secteur
      // (/api/quartier-stats). Si une surface est renseignée et qu'un type de
      // bien précis est sélectionné, on tente en plus la vraie prédiction ML
      // (/api/predict) et on l'utilise comme estimation principale — avec
      // repli silencieux sur la moyenne réelle si l'IA échoue.
      let estimatedPrice = data.prix_moyen;
      let priceM2 = data.prix_m2_moyen;
      let confiance = null;
      // ORA-179 : distingue "aucune prédiction tentée" (surface/type non
      // fournis, vue Estimation vide et invite normalement) de "prédiction
      // tentée mais indisponible" (le modèle actif n'a pas assez de données
      // pour ce couple quartier/type précis, ex: T3 à Ainay) — l'ancien
      // message d'invite blâmait l'utilisateur même quand il avait tout
      // rempli correctement.
      let predictionUnavailable = false;

      const surfaceValue = parseFloat(surfaceInput);
      const hasValidSurface = Number.isFinite(surfaceValue) && surfaceValue > 0;

      if (hasValidSurface && typeLocal !== 'Tout') {
        try {
          const prediction = await api.predict({
            surface: surfaceValue,
            quartier: data.quartier_detecte,
            type_local: typeLocal,
          });
          if (typeof prediction.estimated_price === 'number') {
            estimatedPrice = prediction.estimated_price;
            priceM2 = prediction.price_m2;
            confiance = prediction.confiance;
          } else {
            predictionUnavailable = true;
          }
        } catch (predictErr) {
          predictionUnavailable = true;
          console.error("Estimation IA indisponible, repli sur la moyenne réelle du secteur :", predictErr);
        }
      }

      setResult({
        estimated_price: estimatedPrice,
        stats: { prix_m2: priceM2 },
        quartier: data.quartier_detecte,
        count: data.count,
        type: data.type_filtre,
        confiance,
        predictionUnavailable,
        facteurs: data.facteurs || [],
        // ORA-172 : détail complet (tous les sous-types, pas juste le plus
        // présent) pour le panneau "Les 4 Cavaliers", en plus des phrases résumées ci-dessus (PDF).
        cavaliersDetail: data.cavaliers_detail || [],
        comparables: data.comparables || [],
        // ORA-178 : centre du quartier scanné — vue "Calques", cercle de
        // rayon des cavaliers tracé sur la carte (MapComponent#radiusCircle).
        center: data.center,
        // ORA-171 : "Estimation personnalisée" (maquette 03) ne s'affiche que
        // lorsqu'une vraie prédiction modèle a eu lieu (confiance non nulle) ;
        // `surface` sert d'entrée aux scénarios "et si la surface change ?" et
        // `quartierPrixM2` (moyenne réelle du secteur, avant écrasement par le
        // modèle ci-dessus) à la comparaison "vs moyenne T{type} du quartier".
        surface: hasValidSurface ? surfaceValue : undefined,
        quartierPrixM2: data.prix_m2_moyen,
        // ORA-167 : barre de fourchette min · P25 · médiane · P75 · max
        prixStats: data.prix_stats,
      });
      setChatContext(`Quartier: ${data.quartier_detecte}, Type: ${data.type_filtre}, Prix Moyen: ${data.prix_moyen}€, Prix m²: ${data.prix_m2_moyen}€`);
      if (data.center?.lat && data.center?.lng) {
        setMapCenter([data.center.lat, data.center.lng, 15]);
      }

      // Non bloquant : un échec ici ne doit pas gâcher un scan par ailleurs réussi.
      try {
        const historyData = await api.getQuartierHistorique(data.quartier_detecte, typeLocal, ville);
        setPriceHistory(historyData);
      } catch (historyErr) {
        console.error("Historique des prix indisponible :", historyErr);
      }
    } catch (err) {
      console.error(err);
      setError(describeApiError(err));
    } finally {
      setLoading(false);
    }
  };

  // ORA-179 : puce récapitulative du dernier scan ("Ainay · T2 · 45 m²"),
  // en tête des vues Scan/Estimation — "Modifier" ramène à la vue Recherche,
  // qui se pré-remplit automatiquement depuis `result` (cf. SearchForm plus
  // bas, `initialQuartier`/`initialTypeLocal`/`initialSurface`).
  function renderSummaryChip() {
    if (!result?.quartier) return null;
    const parts = [
      result.quartier,
      result.type && result.type !== 'Tout' ? result.type : null,
      result.surface ? `${result.surface} m²` : null,
    ].filter(Boolean);
    return (
      <div className="flex items-center justify-between gap-2 px-4 md:px-5 py-2 bg-ink-900/60 border-b border-ink-800">
        <span className="text-[11px] font-bold text-slate-300 truncate">{parts.join(' · ')}</span>
        <button
          type="button"
          onClick={() => setActiveView('recherche')}
          className="shrink-0 text-[10px] uppercase tracking-widest font-bold text-violet-400 hover:text-violet-300"
        >
          Modifier
        </button>
      </div>
    );
  }

  // ORA-178 : contenu de la vue "Scan" du rail — reprend tel quel l'ancien
  // contenu principal de la colonne Oracle desktop (ResultCard + détails du
  // quartier), désormais sa propre vue dédiée plutôt qu'un unique panneau.
  function renderScanView() {
    if (ambiguousQuartier && !loading) {
      return (
        <>
          {renderSummaryChip()}
          <QuartierAmbigu
            ambiguous={ambiguousQuartier}
            quartierOptions={quartierOptions}
            onSelect={(name) => handleScan(name, ambiguousQuartier.typeLocal, ambiguousQuartier.surfaceInput)}
          />
        </>
      );
    }

    if (!result && !loading) {
      return (
        <>
          {renderSummaryChip()}
          <p className="p-4 md:p-5 text-xs text-ink-dim">
            Lancez un scan depuis la vue Recherche pour voir l'estimation d'un quartier.
          </p>
        </>
      );
    }

    return (
      <>
        {renderSummaryChip()}
        <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
          <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} onAddSurface={handleAddSurface} ville={ville} health={health} dataAsOf={latestDataDate} />
          {result && !(result.surface && result.confiance) && (
            <div className="mt-2 text-center text-[10px] text-ink-dim uppercase tracking-widest">
              Données réelles ({result.count} biens)
            </div>
          )}
        </div>

        {(result || loading) && (
          <div className="p-4 md:p-5 space-y-4">
            <CavaliersDetail detail={result?.cavaliersDetail} quartier={result?.quartier} />
            <PriceHistory
              status={priceHistory?.status}
              message={priceHistory?.message}
              historique={priceHistory?.historique}
            />
            <div>
              <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest mb-2">
                Annonces récentes
              </p>
              <AnnoncesList ville={ville} compact onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} onSelectAnnonce={handleSelectAnnonce} />
            </div>
          </div>
        )}
      </>
    );
  }

  // ORA-178 : vue "Estimation" — dédiée à la prédiction modèle par surface
  // (maquette 03), vide et explicite tant qu'aucune surface n'a été saisie.
  function renderEstimationView() {
    if (!hasModelEstimate) {
      // ORA-179 : une surface/type ont bien été fournis mais le modèle actif
      // n'a pas assez de données pour cette combinaison précise (ex: peu
      // d'annonces T3 à Ainay) — message honnête plutôt que de laisser
      // penser que l'utilisateur a oublié de remplir un champ.
      const message = result?.predictionUnavailable
        ? `Estimation indisponible pour ${result.quartier} en ${result.type} : données insuffisantes pour cette combinaison quartier/type dans le modèle actif. Le loyer moyen réel du secteur reste visible dans Scan.`
        : "Saisissez une surface et un type de bien précis (T1-T4+) dans Recherche pour obtenir l'estimation personnalisée du modèle.";
      return (
        <>
          {renderSummaryChip()}
          <p className="p-4 md:p-5 text-xs text-ink-dim">{message}</p>
        </>
      );
    }
    return (
      <>
        {renderSummaryChip()}
        <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
          <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} ville={ville} health={health} dataAsOf={latestDataDate} />
        </div>
      </>
    );
  }

  // ORA-178 : vue "Calques" (maquette vue-calques.png) — Fonds de carte +
  // lecture détaillée des 4 cavaliers autour du quartier scanné. Au rayon
  // 500 m, réutilise les mêmes données que le bloc "Les 4 Cavaliers" de la
  // vue Scan (`result.cavaliersDetail`/`result.facteurs`) ; pour 300 m/1 km,
  // useCavaliersRadius appelle GET /api/cavaliers (cf. plus haut).
  function renderCalquesView() {
    return (
      <CalquesView
        layers={layerVisibility}
        onToggleLayer={toggleLayer}
        onSetLayersVisible={setLayersVisible}
        layerCounts={layerCounts}
        cavaliersDetail={cavaliersRadius.cavaliersDetail}
        facteurs={cavaliersRadius.facteurs}
        isLoadingCavaliers={cavaliersRadius.isLoading}
        radiusM={cavaliersRadiusM}
        onChangeRadiusM={setCavaliersRadiusM}
        quartier={result?.quartier}
        zonesCount={homeStats.districts.length}
        ville={ville}
        onGoToRecherche={() => setActiveView('recherche')}
      />
    );
  }

  // ORA-178 : vue "Fiche" — même contenu que la modale (AnnonceDetailContent),
  // sans le chrome dialog/portail, puisqu'elle vit désormais dans une vue du
  // rail plutôt que dans un overlay superposé.
  function renderFicheView() {
    if (selectedAnnonceId == null) {
      return (
        <p className="p-4 md:p-5 text-xs text-ink-dim">
          Sélectionnez une annonce (liste ou carte) pour voir sa fiche.
        </p>
      );
    }
    return (
      <AnnonceDetailContent
        {...ficheDetail}
        onToggleFavorite={ficheDetail.toggleFavorite}
        onVoirAnnonce={ficheDetail.handleVoirAnnonce}
        onExportPdf={ficheDetail.handleExportPdf}
      />
    );
  }

  // ORA-179 : vue "Recherche" — SearchForm (ville, quartier + suggestions,
  // type, surface, scan, recherches récentes), pré-rempli depuis le dernier
  // `result` (lien "Modifier" des vues Scan/Estimation, ou simplement rouvrir
  // Recherche après un scan). Aucune logique dupliquée : mêmes props/
  // `handleScan` que la mobile (rendu plus bas dans la colonne Oracle mobile).
  function renderSearchForm() {
    return (
      <SearchForm
        ville={ville}
        onVilleChange={setVille}
        onScan={handleScan}
        isLoading={loading}
        quartierOptions={quartierOptions}
        initialQuartier={result?.quartier || ''}
        initialTypeLocal={result?.type || 'Tout'}
        initialSurface={result?.surface || ''}
        autoFocusSurface={focusSurfaceNext}
      />
    );
  }

  // ORA-178 : en-tête (sur-titre + titre) de la feuille de contenu, par vue —
  // omis pour Accueil/Immotep dont le contenu porte déjà son propre titre.
  function panelSheetHeader() {
    const breadcrumb = result?.quartier
      ? `${result.quartier} · ${result.type || 'Tout'} · ${ville === 'lille' ? 'LILLE' : 'LYON'}`.toUpperCase()
      : undefined;

    switch (activeView) {
      case 'scan':
        return { overline: breadcrumb, title: 'Scan du quartier' };
      case 'estimation':
        return { overline: breadcrumb, title: 'Estimation personnalisée' };
      case 'calques': {
        // ORA-178 : sur-titre "QUARTIER · TYPE · ARRONDISSEMENT" (maquette
        // vue-calques.png) — l'arrondissement vient de `quartierOptions`
        // (déjà calculé, palette de recherche), jamais recalculé ici.
        const arrondissement = quartierOptions.find((o) => o.quartier === result?.quartier)?.arrondissement;
        const calquesBreadcrumb = result?.quartier
          ? [result.quartier, result.type && result.type !== 'Tout' ? result.type : null, arrondissement]
              .filter(Boolean).join(' · ').toUpperCase()
          : undefined;
        return {
          overline: calquesBreadcrumb,
          title: 'Calques & 4 cavaliers',
          actions: (
            <button
              type="button"
              onClick={resetLayers}
              className="shrink-0 min-h-[44px] px-2 flex items-center text-[10px] uppercase tracking-widest font-bold text-violet-400 hover:text-violet-300"
            >
              Réinitialiser
            </button>
          ),
        };
      }
      case 'annonces':
        return { title: 'Annonces' };
      case 'fiche': {
        const annonce = ficheDetail.annonce;
        return {
          overline: annonce?.type_local && annonce?.quartier ? `${annonce.type_local} · ${annonce.quartier}`.toUpperCase() : undefined,
          title: 'Fiche annonce',
        };
      }
      // ORA-179 : SearchForm porte déjà son propre en-tête ("Nouvelle
      // recherche" / "Que cherches-tu ?"), comme Accueil/Immotep.
      case 'recherche':
        return {};
      default:
        return {};
    }
  }

  const { overline: sheetOverline, title: sheetTitle, actions: sheetActions } = panelSheetHeader();

  return (
    <div className="flex flex-col h-screen w-screen bg-ink-950 text-ink overflow-hidden font-sans selection:bg-accent/30">

      {/* Topbar (ORA-179) : logo + badge "Données au" uniquement — la
          recherche vit désormais dans SearchForm (vue "Recherche" du rail
          desktop, colonne Oracle mobile). */}
      <Topbar dataAsOf={latestDataDate} />

      {error && (
        <div className="shrink-0 mx-3 md:mx-4 mt-2 text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
          {error}
        </div>
      )}

      {/* Zone de contenu principale */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* COLONNE GAUCHE — Carte (60% desktop, plein écran mobile). Ne se
            démonte/remonte jamais au changement de vue du rail (ORA-178) :
            seuls `center`/`bounds` changent, la vue "Calques" pilote
            `layerVisibility`, qu'App transmet directement en prop (composant
            contrôlé). */}
        <div
          id="panel-carte"
          role="tabpanel"
          aria-labelledby="tab-carte"
          className={`${activeTab === 'carte' ? 'flex' : 'hidden'} md:flex w-full md:w-[60%] md:min-w-0 h-full relative border-r border-ink-800`}
        >
          {shouldMountMap && (
            <ErrorBoundary fallback={makePanelFallback('La carte')}>
              <MapComponent
                center={mapCenter}
                bounds={mapBounds}
                chatOpen={isChatOpen}
                ville={ville}
                hidePanel={isDesktop}
                layers={layerVisibility}
                onToggleLayer={toggleLayer}
                onAnnonceClick={handleSelectAnnonce}
                focus={
                  // Rayon "Aucun" (ORA-183, v3) : `cavaliersRadiusM` vaut
                  // `null` — CLEAR_FOCUS (pas de cercle, pings au style
                  // normal), jamais SET_FOCUS avec un radius_m manquant.
                  activeView === 'calques' && result?.center && cavaliersRadiusM != null
                    ? { lat: result.center.lat, lng: result.center.lng, radiusM: cavaliersRadiusM }
                    : null
                }
              />
            </ErrorBoundary>
          )}
        </div>

        {/* COLONNE DROITE DESKTOP — rail "classeur" + feuille de contenu
            (ORA-178, maquette nav-b3-classeur). Mobile garde sa propre
            colonne ci-dessous, inchangée. */}
        <div className="hidden md:flex w-[40%] min-w-0 h-full relative z-10">
          <PanelNav
            activeView={activeView}
            onChange={setActiveView}
            annonceCount={result?.count}
            ficheDisabled={selectedAnnonceId == null}
            sheetId={PANEL_SHEET_ID}
          />

          <ErrorBoundary fallback={makePanelFallback("Le panneau d'estimation")}>
            <PanelSheet
              id={PANEL_SHEET_ID}
              overline={activeView === 'immotep' ? undefined : sheetOverline}
              title={activeView === 'immotep' ? undefined : sheetTitle}
              actions={activeView === 'immotep' ? undefined : sheetActions}
            >
              {/* ORA-175/178 : Immotep reste monté en permanence (juste
                  masqué) pour ne jamais perdre l'historique de conversation
                  en changeant de vue — seule vue dont le contenu persiste
                  hors de son onglet actif, comme la carte. */}
              <div className={activeView === 'immotep' ? 'h-full flex flex-col' : 'hidden'}>
                <ChatOracle
                  analysis={result?.analysis}
                  context={chatContext}
                  quartier={result?.quartier}
                  onListAnnonces={(quartier) => handleViewAnnonces(quartier)}
                  onInsight={(insight) => {
                    if (insight?.map_focus?.lat && insight?.map_focus?.lng) {
                      setMapCenter([insight.map_focus.lat, insight.map_focus.lng, insight.map_focus.zoom || 15]);
                    }
                  }}
                />
              </div>

              <div className={activeView === 'immotep' ? 'hidden' : 'h-full'}>
                {activeView === 'accueil' && (
                  <>
                    {listingsError && listings.length === 0 && (
                      <div className="mx-4 md:mx-5 mt-4 flex items-center justify-between gap-2 bg-red-900/20 border border-red-900/50 rounded-lg px-3 py-2">
                        <p className="text-[11px] text-red-400 font-bold">
                          Impossible de charger les données du marché : {listingsError}
                        </p>
                        <button
                          type="button"
                          onClick={() => setListingsRetryToken((t) => t + 1)}
                          className="shrink-0 text-[10px] uppercase tracking-widest font-bold text-red-300 hover:text-red-200 underline underline-offset-2"
                        >
                          Réessayer
                        </button>
                      </div>
                    )}
                    <HomeOverview
                      stats={homeStats}
                      ville={ville}
                      onOpenChat={() => setActiveView('immotep')}
                      onSelectQuartier={(quartier) => handleScan(quartier, 'Tout', '')}
                    />
                    <div className="px-4 md:px-5 pb-4 md:pb-5">
                      <button
                        type="button"
                        onClick={() => setActiveView('recherche')}
                        className="w-full min-h-[44px] rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-bold uppercase text-xs tracking-widest transition-colors"
                      >
                        Lancer une recherche
                      </button>
                    </div>
                  </>
                )}
                {activeView === 'recherche' && renderSearchForm()}
                {activeView === 'scan' && renderScanView()}
                {activeView === 'estimation' && renderEstimationView()}
                {activeView === 'calques' && renderCalquesView()}
                {activeView === 'annonces' && (
                  <div className="p-4 md:p-5">
                    <AnnoncesList ville={ville} onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} onSelectAnnonce={handleSelectAnnonce} />
                  </div>
                )}
                {activeView === 'fiche' && renderFicheView()}
              </div>
            </PanelSheet>
          </ErrorBoundary>
        </div>

        {/* COLONNE DROITE MOBILE — Oracle (plein écran, onglet mobile
            "oracle") : structure historique inchangée (ORA-178 : "garde les
            onglets mobiles actuels et masque le rail"), y compris la bulle de
            chat flottante ci-dessous. */}
        <div
          id="panel-oracle"
          role="tabpanel"
          aria-labelledby="tab-oracle"
          className={`${activeTab === 'oracle' ? 'flex' : 'hidden'} md:hidden flex-col w-full h-full bg-ink-900/95 backdrop-blur-md relative z-10`}
        >
          <div id="chat-panel" className={isChatOpen ? 'flex-1 min-h-0' : 'hidden'}>
            <ErrorBoundary fallback={makePanelFallback('Le chat Immotep')}>
              <ChatOracle
                analysis={result?.analysis}
                context={chatContext}
                quartier={result?.quartier}
                onListAnnonces={(quartier) => {
                  handleViewAnnonces(quartier);
                  setIsChatOpen(false);
                }}
                onInsight={(insight) => {
                  if (insight?.map_focus?.lat && insight?.map_focus?.lng) {
                    setMapCenter([insight.map_focus.lat, insight.map_focus.lng, insight.map_focus.zoom || 15]);
                  }
                }}
              />
            </ErrorBoundary>
          </div>

          <div
            id="oracle-info-panel"
            className={isChatOpen ? 'hidden' : 'flex-1 min-h-0 overflow-y-auto custom-scrollbar'}
          >
          <ErrorBoundary fallback={makePanelFallback("Le panneau d'estimation")}>
            {/* ORA-179 : la Topbar ne porte plus la recherche — mobile
                (pas de rail) garde donc un accès permanent à SearchForm ici,
                le seul composant de recherche restant (aucune logique
                dupliquée avec la vue "Recherche" desktop ci-dessus). */}
            <details className="border-b border-slate-800 group" open>
              <summary className="px-4 md:px-5 py-2.5 bg-slate-900/20 text-[9px] uppercase text-slate-500 font-bold tracking-widest cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden flex items-center justify-between hover:text-slate-300 transition-colors">
                <span>Recherche</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-open:rotate-180">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </summary>
              <SearchForm
                ville={ville}
                onVilleChange={setVille}
                onScan={handleScan}
                isLoading={loading}
                quartierOptions={quartierOptions}
                initialQuartier={result?.quartier || ''}
                initialTypeLocal={result?.type || 'Tout'}
                initialSurface={result?.surface || ''}
                autoFocus={false}
              />
            </details>

            {ambiguousQuartier && !loading && (
              <QuartierAmbigu
                ambiguous={ambiguousQuartier}
                quartierOptions={quartierOptions}
                onSelect={(name) => handleScan(name, ambiguousQuartier.typeLocal, ambiguousQuartier.surfaceInput)}
              />
            )}

            {!result && !loading && !ambiguousQuartier && (
              <>
                {listingsError && listings.length === 0 && (
                  <div className="mx-4 md:mx-5 mt-4 flex items-center justify-between gap-2 bg-red-900/20 border border-red-900/50 rounded-lg px-3 py-2">
                    <p className="text-[11px] text-red-400 font-bold">
                      Impossible de charger les données du marché : {listingsError}
                    </p>
                    <button
                      type="button"
                      onClick={() => setListingsRetryToken((t) => t + 1)}
                      className="shrink-0 text-[10px] uppercase tracking-widest font-bold text-red-300 hover:text-red-200 underline underline-offset-2"
                    >
                      Réessayer
                    </button>
                  </div>
                )}
                <HomeOverview
                  stats={homeStats}
                  ville={ville}
                  onOpenChat={() => setIsChatOpen(true)}
                  onSelectQuartier={(quartier) => handleScan(quartier, 'Tout', '')}
                />
              </>
            )}

            {(result || loading) && (
            <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
              <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} onAddSurface={handleAddSurface} ville={ville} health={health} dataAsOf={latestDataDate} />
              {result && !(result.surface && result.confiance) && (
                <div className="mt-2 text-center text-[10px] text-ink-dim uppercase tracking-widest">
                  Données réelles ({result.count} biens)
                </div>
              )}
            </div>
            )}

            {(result || loading) && (
            <details className="hidden md:block border-b border-ink-800 group" open>
              <summary className="px-4 md:px-5 py-2.5 bg-ink-900/20 text-[9px] uppercase text-ink-dim font-bold tracking-widest cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden flex items-center justify-between hover:text-ink transition-colors">
                <span>Détails du quartier</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-open:rotate-180">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </summary>

              <div className="p-4 md:p-5 pt-3 space-y-4">
                <CavaliersDetail detail={result?.cavaliersDetail} quartier={result?.quartier} />

                <PriceHistory
                  status={priceHistory?.status}
                  message={priceHistory?.message}
                  historique={priceHistory?.historique}
                />

                <div>
                  <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest mb-2">
                    Annonces récentes
                  </p>
                  <AnnoncesList ville={ville} compact onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} />
                </div>
              </div>
            </details>
            )}
          </ErrorBoundary>
          </div>

        </div>

        {/* COLONNE ANNONCES — onglet plein écran mobile uniquement (desktop :
            un aperçu compact est déjà intégré dans la colonne Oracle ci-dessus) */}
        <div
          id="panel-annonces"
          role="tabpanel"
          aria-labelledby="tab-annonces"
          className={`${activeTab === 'annonces' ? 'flex' : 'hidden'} md:hidden flex-col w-full h-full bg-ink-900/95 overflow-y-auto p-4`}
        >
          <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest mb-3">
            Annonces récentes
          </p>
          <AnnoncesList ville={ville} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} />
        </div>
      </div>

      {/* ORA-175/178 : bouton bascule du chat Immotep — MOBILE UNIQUEMENT
          désormais (desktop pilote Immotep via la vue dédiée du rail). */}
      <button
        type="button"
        onClick={() => {
          setIsChatOpen((v) => !v);
          setActiveTab('oracle');
        }}
        aria-expanded={isChatOpen}
        aria-controls="chat-panel"
        aria-label={isChatOpen ? 'Fermer le chat Immotep' : 'Ouvrir le chat Immotep'}
        className="md:hidden fixed z-[60] bottom-20 right-4 w-14 h-14 rounded-full bg-accent hover:bg-accent-light active:bg-accent text-white shadow-lg shadow-accent/40 flex items-center justify-center transition-all transform active:scale-95"
      >
        {isChatOpen ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
      </button>

      {/* Barre d'onglets — mobile uniquement */}
      <nav
        role="tablist"
        aria-label="Navigation principale"
        className="md:hidden flex-none h-14 bg-ink-950 border-t border-ink-800 flex items-stretch z-50"
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            setActiveTab((prev) => {
              const currentIndex = MOBILE_TABS.indexOf(prev);
              const delta = e.key === 'ArrowRight' ? 1 : -1;
              const nextIndex = (currentIndex + delta + MOBILE_TABS.length) % MOBILE_TABS.length;
              return MOBILE_TABS[nextIndex];
            });
          }
        }}
      >
        <button
          role="tab"
          id="tab-carte"
          aria-selected={activeTab === 'carte'}
          aria-controls="panel-carte"
          tabIndex={activeTab === 'carte' ? 0 : -1}
          onClick={() => setActiveTab('carte')}
          className={`flex-1 flex flex-col items-center justify-center gap-1 transition-colors ${
            activeTab === 'carte' ? 'text-accent-light' : 'text-ink-dim'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"></polygon>
            <line x1="9" y1="3" x2="9" y2="18"></line>
            <line x1="15" y1="6" x2="15" y2="21"></line>
          </svg>
          <span className="text-[9px] uppercase tracking-widest font-bold">Carte</span>
        </button>

        <button
          role="tab"
          id="tab-oracle"
          aria-selected={activeTab === 'oracle'}
          aria-controls="panel-oracle"
          tabIndex={activeTab === 'oracle' ? 0 : -1}
          onClick={() => setActiveTab('oracle')}
          className={`flex-1 flex flex-col items-center justify-center gap-1 transition-colors ${
            activeTab === 'oracle' ? 'text-accent-light' : 'text-ink-dim'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span className="text-[9px] uppercase tracking-widest font-bold">Oracle</span>
        </button>

        <button
          role="tab"
          id="tab-annonces"
          aria-selected={activeTab === 'annonces'}
          aria-controls="panel-annonces"
          tabIndex={activeTab === 'annonces' ? 0 : -1}
          onClick={() => setActiveTab('annonces')}
          className={`flex-1 flex flex-col items-center justify-center gap-1 transition-colors ${
            activeTab === 'annonces' ? 'text-accent-light' : 'text-ink-dim'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
          </svg>
          <span className="text-[9px] uppercase tracking-widest font-bold">Annonces</span>
        </button>
      </nav>
    </div>
  );
}

export default App;
