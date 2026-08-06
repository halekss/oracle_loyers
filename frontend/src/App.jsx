import { useState, useEffect } from 'react';
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import PriceHistory from './components/PriceHistory';
import MapComponent from './components/MapComponent';
import ChatOracle from './components/ChatOracle';
import AnnoncesList from './components/AnnoncesList';
import { api, describeApiError } from './services/api';
import { computeBoundsForQuartiers } from './services/mapBounds';

// Correspond au breakpoint `md` de Tailwind : au-delà, les deux panneaux
// (carte + oracle) restent visibles simultanément, donc la carte doit
// toujours être montée. En dessous, elle ne doit se monter que si son
// onglet mobile est actif, pour éviter de charger l'iframe (4 Mo) inutilement.
const DESKTOP_MEDIA_QUERY = '(min-width: 768px)';
const MOBILE_TABS = ['carte', 'oracle', 'annonces'];

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
  const [chatContext, setChatContext] = useState(null);
  const [mapCenter, setMapCenter] = useState(null);
  // ORA-105 : bounding-box des annonces actuellement affichées dans
  // AnnoncesList (colonne Oracle desktop). undefined = pas encore calculée
  // (la carte ne réagit pas) ; null = calculée mais sans coordonnée
  // exploitable (repli explicite sur le centre-ville dans MapComponent).
  const [mapBounds, setMapBounds] = useState(undefined);
  const [listings, setListings] = useState([]);
  const [activeTab, setActiveTab] = useState('oracle');
  // Chat en bulle flottante superposée à l'écran (pas de fenêtre/page à
  // part) : fermé par défaut pour laisser "Détails du quartier" toute la
  // hauteur de la colonne Oracle.
  const [isChatOpen, setIsChatOpen] = useState(false);
  const isDesktop = useIsDesktop();
  const shouldMountMap = isDesktop || activeTab === 'carte';
  const facteurs = result?.facteurs || [];

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

  const handleAnnoncesItemsChange = (items) => {
    const quartiers = [...new Set(items.map((item) => item.quartier).filter(Boolean))];
    setMapBounds(computeBoundsForQuartiers(listings, quartiers));
  };

  const handleScan = async (quartier, typeLocal, surfaceInput) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPriceHistory(null);

    try {
      const data = await api.getQuartierStats(quartier, typeLocal);

      if (!data.found) {
        setError(data.message || "Aucun résultat trouvé.");
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
      });
      setChatContext(`Quartier: ${data.quartier_detecte}, Type: ${data.type_filtre}, Prix Moyen: ${data.prix_moyen}€, Prix m²: ${data.prix_m2_moyen}€`);
      if (data.center?.lat && data.center?.lng) {
        setMapCenter([data.center.lat, data.center.lng, 15]);
      }

      // Non bloquant : un échec ici ne doit pas gâcher un scan par ailleurs réussi.
      try {
        const historyData = await api.getQuartierHistorique(data.quartier_detecte, typeLocal);
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

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-200 overflow-hidden font-sans selection:bg-purple-500/30">

      {/* Zone de contenu principale */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* COLONNE GAUCHE — Carte (60% desktop, plein écran mobile) */}
        <div
          id="panel-carte"
          role="tabpanel"
          aria-labelledby="tab-carte"
          className={`${activeTab === 'carte' ? 'flex' : 'hidden'} md:flex w-full md:w-[60%] h-full relative border-r border-slate-800`}
        >
          {shouldMountMap && <MapComponent center={mapCenter} bounds={mapBounds} chatOpen={isChatOpen} />}
        </div>

        {/* COLONNE DROITE — Oracle (40% desktop, plein écran mobile) */}
        <div
          id="panel-oracle"
          role="tabpanel"
          aria-labelledby="tab-oracle"
          className={`${activeTab === 'oracle' ? 'flex' : 'hidden'} md:flex flex-col w-full md:w-[40%] h-full bg-slate-900/95 backdrop-blur-md relative z-10`}
        >

          {/* En-tête / Recherche */}
          <div className="shrink-0 p-4 md:p-5 border-b border-slate-800 bg-slate-950/50 z-20">
            <h1 className="text-xl font-black tracking-tighter text-white mb-4">
              ORACLE <span className="text-purple-500">DES LOYERS</span>
            </h1>

            <SearchForm onScan={handleScan} isLoading={loading} />

            {error && (
              <div className="mt-3 text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
                {error}
              </div>
            )}
          </div>

          {/* Résultat + détails (cavaliers/historique/annonces) — bloc
              scrollable indépendant occupant toute la hauteur restante de la
              colonne (le chat n'y prend plus de place, cf. bulle flottante
              plus bas). */}
          <div
            id="oracle-info-panel"
            className="flex-1 min-h-0 overflow-y-auto custom-scrollbar"
          >
            {/* Résultat */}
            <div className="p-4 md:p-5 border-b border-slate-800 bg-slate-900/30">
              <ResultCard data={result} loading={loading} />
              {result && (
                <div className="mt-2 text-center text-[10px] text-slate-500 uppercase tracking-widest">
                  Données réelles ({result.count} biens)
                </div>
              )}
            </div>

            {/* Détails du quartier — Les 4 Cavaliers, historique des prix et
                annonces récentes, regroupés dans un seul dropdown (desktop
                uniquement, l'onglet mobile "Annonces" joue ce rôle en plein
                écran sur mobile pour les annonces). */}
            <details className="hidden md:block border-b border-slate-800 group" open>
              <summary className="px-4 md:px-5 py-2.5 bg-slate-900/20 text-[9px] uppercase text-slate-500 font-bold tracking-widest cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden flex items-center justify-between hover:text-slate-300 transition-colors">
                <span>Détails du quartier</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-open:rotate-180">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </summary>

              <div className="p-4 md:p-5 pt-3 space-y-4">
                {/* Les 4 Cavaliers */}
                {facteurs.length > 0 && (
                  <div>
                    <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-1.5">
                      Les 4 Cavaliers
                    </p>
                    <div className="space-y-1.5">
                      {facteurs.map((f) => (
                        <div key={f.categorie} className="text-[11px] text-slate-400 bg-slate-900/50 rounded-lg px-2 py-1.5 border border-slate-800">
                          <span className="text-purple-400 font-bold">{f.categorie} — </span>
                          {f.phrase}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Historique du prix moyen/m² (ORA-72) */}
                <PriceHistory
                  status={priceHistory?.status}
                  message={priceHistory?.message}
                  historique={priceHistory?.historique}
                />

                {/* Annonces récentes (ORA-87/88) */}
                <div>
                  <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">
                    Annonces récentes
                  </p>
                  <AnnoncesList compact onItemsChange={handleAnnoncesItemsChange} />
                </div>
              </div>
            </details>
          </div>

        </div>

        {/* COLONNE ANNONCES — onglet plein écran mobile uniquement (desktop :
            un aperçu compact est déjà intégré dans la colonne Oracle ci-dessus) */}
        <div
          id="panel-annonces"
          role="tabpanel"
          aria-labelledby="tab-annonces"
          className={`${activeTab === 'annonces' ? 'flex' : 'hidden'} md:hidden flex-col w-full h-full bg-slate-900/95 overflow-y-auto p-4`}
        >
          <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-3">
            Annonces récentes
          </p>
          <AnnoncesList />
        </div>
      </div>

      {/* Chat Immotep — bulle flottante + overlay, superposés à l'écran
          principal quel que soit l'onglet actif (pas de fenêtre ni de page
          séparée). ChatOracle reste monté en permanence, seule sa visibilité
          bascule, pour ne jamais perdre l'historique de conversation entre
          deux ouvertures. */}
      <div
        id="chat-overlay"
        className={`fixed z-[60] bottom-36 md:bottom-24 right-4 md:right-6 w-[calc(100vw-2rem)] max-w-sm h-[70vh] max-h-[560px] flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl shadow-black/50 overflow-hidden ${isChatOpen ? 'flex' : 'hidden'}`}
      >
        <div className="shrink-0 flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800">
          <span className="text-xs font-black uppercase tracking-widest text-white">
            Immotep <span className="text-purple-400">— Oracle</span>
          </span>
          <button
            type="button"
            onClick={() => setIsChatOpen(false)}
            aria-label="Fermer le chat"
            className="text-slate-500 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div className="flex-1 min-h-0">
          <ChatOracle
            analysis={result?.analysis}
            context={chatContext}
            onInsight={(insight) => {
              if (insight?.map_focus?.lat && insight?.map_focus?.lng) {
                setMapCenter([insight.map_focus.lat, insight.map_focus.lng, insight.map_focus.zoom || 15]);
              }
            }}
          />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setIsChatOpen((v) => !v)}
        aria-expanded={isChatOpen}
        aria-controls="chat-overlay"
        aria-label={isChatOpen ? 'Fermer le chat Immotep' : 'Ouvrir le chat Immotep'}
        className="fixed z-[60] bottom-20 md:bottom-6 right-4 md:right-6 w-14 h-14 rounded-full bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white shadow-lg shadow-indigo-900/40 flex items-center justify-center transition-all transform active:scale-95"
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
        className="md:hidden flex-none h-14 bg-slate-950 border-t border-slate-800 flex items-stretch z-50"
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
            activeTab === 'carte' ? 'text-purple-400' : 'text-slate-500'
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
            activeTab === 'oracle' ? 'text-purple-400' : 'text-slate-500'
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
            activeTab === 'annonces' ? 'text-purple-400' : 'text-slate-500'
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
