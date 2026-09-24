import { useState, useEffect, useMemo, useRef } from 'react';
import ResultCard from './components/ResultCard';
import PriceHistory from './components/PriceHistory';
import MapComponent, { ToggleItem } from './components/MapComponent';
import ChatOracle from './components/ChatOracle';
import AnnoncesList from './components/AnnoncesList';
import ErrorBoundary from './components/ErrorBoundary';
import Topbar from './components/Topbar';
import HomeOverview from './components/HomeOverview';
import CavaliersDetail from './components/CavaliersDetail';
import QuartierAmbigu from './components/QuartierAmbigu';
import PanelNav from './components/PanelNav';
import PanelSheet from './components/PanelSheet';
import AnnonceDetailContent from './components/AnnonceDetailContent';
import { useAnnonceDetail } from './hooks/useAnnonceDetail';
import { api, describeApiError } from './services/api';
import { computeBoundsForQuartiers } from './services/mapBounds';
import { computeHomeStats } from './services/homeStats';
import { computeQuartierOptions } from './services/quartierStats';
import { computeLatestDataDate } from './services/latestDataDate';
import { layersByGroup } from './services/mapLayers';
import { loadRecentSearches } from './services/recentSearchesStorage';

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
  // ORA-178 : miroir de l'état interne de MapComponent (calques + compteurs),
  // pour que la vue "Calques" du rail affiche exactement ce qu'il sait déjà
  // — jamais recalculé ici, seulement reflété (cf. MapComponent#onLayersChange).
  const [mapLayersState, setMapLayersState] = useState({ layers: {}, layerCounts: {} });
  const mapRef = useRef(null);
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
  // ORA-178 : "Estimation personnalisée" (maquette 03) — vraie prédiction
  // modèle disponible, cf. ResultCard.jsx (même condition).
  const hasModelEstimate = Boolean(result?.surface) && Boolean(result?.confiance);
  // ORA-178 : fiche annonce (vue "Fiche") — fetch/actions partagés avec la
  // modale (AnnonceDetailModal), jamais recalculés en double. Ne dépend pas
  // de `activeView` : la fiche reste en cache tant qu'une autre annonce n'a
  // pas été sélectionnée, même après avoir changé de vue.
  const ficheDetail = useAnnonceDetail(selectedAnnonceId);

  // ORA-105 : chargé une fois, sert à résoudre les coordonnées des quartiers
  // des annonces affichées (AnnoncesList n'a pas de latitude/longitude).
  useEffect(() => {
    let cancelled = false;

    api.getListings()
      .then((data) => {
        if (!cancelled) setListings(data || []);
      })
      .catch((err) => console.error("Listings indisponibles pour le recentrage carte :", err));

    return () => {
      cancelled = true;
    };
  }, []);

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

  const handleScan = async (quartier, typeLocal, surfaceInput) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPriceHistory(null);
    setAmbiguousQuartier(null);
    // ORA-178 : lancer un scan bascule toujours sur la vue "Scan" du rail
    // (desktop) — sans effet sur mobile, qui garde ses propres onglets.
    setActiveView('scan');

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
          }
        } catch (predictErr) {
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
        facteurs: data.facteurs || [],
        // ORA-172 : détail complet (tous les sous-types, pas juste le plus
        // présent) pour le panneau "Les 4 Cavaliers", en plus des phrases résumées ci-dessus (PDF).
        cavaliersDetail: data.cavaliers_detail || [],
        comparables: data.comparables || [],
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

  // ORA-178 : contenu de la vue "Scan" du rail — reprend tel quel l'ancien
  // contenu principal de la colonne Oracle desktop (ResultCard + détails du
  // quartier), désormais sa propre vue dédiée plutôt qu'un unique panneau.
  function renderScanView() {
    if (ambiguousQuartier && !loading) {
      return (
        <QuartierAmbigu
          ambiguous={ambiguousQuartier}
          quartierOptions={quartierOptions}
          onSelect={(name) => handleScan(name, ambiguousQuartier.typeLocal, ambiguousQuartier.surfaceInput)}
        />
      );
    }

    if (!result && !loading) {
      return (
        <p className="p-4 md:p-5 text-xs text-ink-dim">
          Lancez un scan depuis la barre de recherche pour voir l'estimation d'un quartier.
        </p>
      );
    }

    return (
      <>
        <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
          <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} onAddSurface={() => document.getElementById('topbar-surface')?.focus()} ville={ville} health={health} dataAsOf={latestDataDate} />
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
              <AnnoncesList compact onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} onSelectAnnonce={handleSelectAnnonce} />
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
      return (
        <p className="p-4 md:p-5 text-xs text-ink-dim">
          Saisissez une surface dans la barre de recherche pour obtenir l'estimation personnalisée du modèle.
        </p>
      );
    }
    return (
      <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
        <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} ville={ville} health={health} dataAsOf={latestDataDate} />
      </div>
    );
  }

  // ORA-178 : vue "Calques" — mêmes lignes que le panneau flottant de
  // MapComponent (mobile), pilotées à distance via `mapRef.current.toggleLayer`
  // pour ne jamais dupliquer la logique d'envoi des commandes à l'iframe.
  function renderCalquesView() {
    const { layers, layerCounts } = mapLayersState;
    const toggle = (key) => mapRef.current?.toggleLayer(key);
    return (
      <div className="p-4 md:p-5 space-y-4">
        <div>
          <h3 className="text-[10px] uppercase tracking-widest text-ink-dim mb-2 font-bold">Transports</h3>
          {layersByGroup('transports').map((layer) => (
            <ToggleItem key={layer.key} label={layer.label} color={layer.uiColor} isActive={layers[layer.key]} onToggle={() => toggle(layer.key)} />
          ))}
        </div>
        <div>
          <h3 className="text-[10px] uppercase tracking-widest text-ink-dim mb-2 font-bold">Les 4 Cavaliers</h3>
          {layersByGroup('contexte').map((layer) => (
            <ToggleItem key={layer.key} label={layer.label} color={layer.uiColor} isActive={layers[layer.key]} onToggle={() => toggle(layer.key)} count={layerCounts[layer.key]} />
          ))}
        </div>
        <div>
          <h3 className="text-[10px] uppercase tracking-widest text-ink-dim mb-2 font-bold">Offres Immobilières</h3>
          {layersByGroup('immobilier').map((layer) => (
            <ToggleItem key={layer.key} label={layer.label} color={layer.uiColor} isActive={layers[layer.key]} onToggle={() => toggle(layer.key)} count={layerCounts[layer.key]} />
          ))}
        </div>
      </div>
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

  // ORA-178 : vue "Recherche" — ville + recherches récentes déjà persistées
  // (ORA-176, `recentSearchesStorage.js`) ; le champ de recherche avec
  // suggestions/ambiguïté reste celui de la Topbar (pas de duplication de sa
  // logique de palette ici, juste un raccourci pour lui donner le focus).
  function renderRechercheView() {
    const recent = loadRecentSearches();
    return (
      <div className="p-4 md:p-5 space-y-4">
        <div>
          <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest mb-2">Ville</p>
          <div className="flex gap-2">
            {['lyon', 'lille'].map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setVille(v)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-colors ${
                  ville === v ? 'bg-accent text-white' : 'bg-ink-900 border border-ink-700 text-ink-muted hover:text-ink'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={() => document.getElementById('topbar-quartier-input')?.focus()}
          className="w-full text-left bg-ink-900 border border-ink-700 hover:border-accent rounded-xl px-3 py-2.5 text-[11px] text-ink-muted transition-colors"
        >
          Rechercher un quartier <span className="text-accent-light">→ utiliser la barre de recherche en haut</span>
        </button>

        <div>
          <p className="text-[9px] uppercase text-ink-dim font-bold tracking-widest mb-2">Recherches récentes</p>
          {recent.length === 0 ? (
            <p className="text-[11px] text-ink-dim">Aucune recherche récente.</p>
          ) : (
            <ul className="space-y-1.5">
              {recent.map((entry, i) => (
                <li key={i}>
                  <button
                    type="button"
                    onClick={() => handleScan(entry.quartier, entry.typeLocal || 'Tout', entry.surface || '')}
                    className="w-full flex items-center justify-between gap-2 bg-ink-900 border border-ink-700 hover:border-accent rounded-lg px-3 py-2 text-left transition-colors"
                  >
                    <span className="text-xs text-ink truncate">
                      {entry.quartier}{entry.typeLocal ? ` · ${entry.typeLocal}` : ''}{entry.surface ? ` · ${entry.surface} m²` : ''}
                    </span>
                    <span className="text-[9px] uppercase text-accent-light font-bold shrink-0">Scanner</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
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
      case 'calques':
        return { title: 'Calques & 4 cavaliers' };
      case 'annonces':
        return { title: 'Annonces' };
      case 'fiche': {
        const annonce = ficheDetail.annonce;
        return {
          overline: annonce?.type_local && annonce?.quartier ? `${annonce.type_local} · ${annonce.quartier}`.toUpperCase() : undefined,
          title: 'Fiche annonce',
        };
      }
      case 'recherche':
        return { title: 'Recherche' };
      default:
        return {};
    }
  }

  const { overline: sheetOverline, title: sheetTitle } = panelSheetHeader();

  return (
    <div className="flex flex-col h-screen w-screen bg-ink-950 text-ink overflow-hidden font-sans selection:bg-accent/30">

      {/* Topbar (ORA-170) : logo, ville, recherche quartier, filtres type,
          surface et bouton SCAN — pleine largeur, persistante au-dessus de
          la carte ET du panneau latéral, quel que soit l'onglet mobile actif. */}
      <Topbar ville={ville} onVilleChange={setVille} onScan={handleScan} isLoading={loading} dataAsOf={latestDataDate} quartierOptions={quartierOptions} />

      {error && (
        <div className="shrink-0 mx-3 md:mx-4 mt-2 text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
          {error}
        </div>
      )}

      {/* Zone de contenu principale */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* COLONNE GAUCHE — Carte (60% desktop, plein écran mobile). Ne se
            démonte/remonte jamais au changement de vue du rail (ORA-178) :
            seuls `center`/`bounds` changent, la vue "Calques" pilote ses
            calques à distance via `mapRef`. */}
        <div
          id="panel-carte"
          role="tabpanel"
          aria-labelledby="tab-carte"
          className={`${activeTab === 'carte' ? 'flex' : 'hidden'} md:flex w-full md:w-[60%] h-full relative border-r border-ink-800`}
        >
          {shouldMountMap && (
            <ErrorBoundary fallback={makePanelFallback('La carte')}>
              <MapComponent
                ref={mapRef}
                center={mapCenter}
                bounds={mapBounds}
                chatOpen={isChatOpen}
                ville={ville}
                hidePanel={isDesktop}
                onLayersChange={(layers, layerCounts) => setMapLayersState({ layers, layerCounts })}
                onAnnonceClick={handleSelectAnnonce}
              />
            </ErrorBoundary>
          )}
        </div>

        {/* COLONNE DROITE DESKTOP — rail "classeur" + feuille de contenu
            (ORA-178, maquette nav-b3-classeur). Mobile garde sa propre
            colonne ci-dessous, inchangée. */}
        <div className="hidden md:flex w-[40%] h-full relative z-10">
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
                  <HomeOverview
                    stats={homeStats}
                    ville={ville}
                    onOpenChat={() => setActiveView('immotep')}
                    onSelectQuartier={(quartier) => handleScan(quartier, 'Tout', '')}
                  />
                )}
                {activeView === 'scan' && renderScanView()}
                {activeView === 'estimation' && renderEstimationView()}
                {activeView === 'calques' && renderCalquesView()}
                {activeView === 'annonces' && (
                  <div className="p-4 md:p-5">
                    <AnnoncesList onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} onSelectAnnonce={handleSelectAnnonce} />
                  </div>
                )}
                {activeView === 'fiche' && renderFicheView()}
                {activeView === 'recherche' && renderRechercheView()}
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
            {ambiguousQuartier && !loading && (
              <QuartierAmbigu
                ambiguous={ambiguousQuartier}
                quartierOptions={quartierOptions}
                onSelect={(name) => handleScan(name, ambiguousQuartier.typeLocal, ambiguousQuartier.surfaceInput)}
              />
            )}

            {!result && !loading && !ambiguousQuartier && (
              <HomeOverview
                stats={homeStats}
                ville={ville}
                onOpenChat={() => setIsChatOpen(true)}
                onSelectQuartier={(quartier) => handleScan(quartier, 'Tout', '')}
              />
            )}

            {(result || loading) && (
            <div className="p-4 md:p-5 border-b border-ink-800 bg-ink-900/30">
              <ResultCard data={result} loading={loading} priceHistory={priceHistory} onViewAnnonces={handleViewAnnonces} ville={ville} health={health} dataAsOf={latestDataDate} />
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
                  <AnnoncesList compact onItemsChange={handleAnnoncesItemsChange} focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} />
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
          <AnnoncesList focusedQuartier={focusedQuartier} referencePrixM2={result?.quartierPrixM2} referenceType={result?.type} />
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
