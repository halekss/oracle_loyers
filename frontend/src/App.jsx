import { useState } from 'react';
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import MapComponent from './components/MapComponent';
import ChatOracle from './components/ChatOracle';
import { api } from './services/api';

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatContext, setChatContext] = useState(null);
  const [mapCenter, setMapCenter] = useState(null);
  const [activeTab, setActiveTab] = useState('oracle');

  const handleScan = async (quartier, typeLocal) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await api.getQuartierStats(quartier, typeLocal);

      if (data.found) {
        setResult({
          estimated_price: data.prix_moyen,
          stats: { prix_m2: data.prix_m2_moyen },
          quartier: data.quartier_detecte,
          count: data.count,
          type: data.type_filtre,
        });
        setChatContext(`Quartier: ${data.quartier_detecte}, Type: ${data.type_filtre}, Prix Moyen: ${data.prix_moyen}€, Prix m²: ${data.prix_m2_moyen}€`);
        if (data.center?.lat && data.center?.lng) {
          setMapCenter([data.center.lat, data.center.lng, 15]);
        }
      } else {
        setError(data.message || "Aucun résultat trouvé.");
      }
    } catch (err) {
      console.error(err);
      setError("Erreur lors de l'analyse du secteur.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-slate-950 text-slate-200 overflow-hidden font-sans selection:bg-purple-500/30">

      {/* Zone de contenu principale */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">

        {/* COLONNE GAUCHE — Carte (60% desktop, plein écran mobile) */}
        <div className={`${activeTab === 'carte' ? 'flex' : 'hidden'} md:flex w-full md:w-[60%] h-full relative border-r border-slate-800`}>
          <MapComponent center={mapCenter} />
        </div>

        {/* COLONNE DROITE — Oracle (40% desktop, plein écran mobile) */}
        <div className={`${activeTab === 'oracle' ? 'flex' : 'hidden'} md:flex flex-col w-full md:w-[40%] h-full bg-slate-900/95 backdrop-blur-md relative z-10`}>

          {/* En-tête / Recherche */}
          <div className="p-4 md:p-5 border-b border-slate-800 bg-slate-950/50 z-20">
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

          {/* Résultat */}
          <div className="shrink-0 p-4 md:p-5 border-b border-slate-800 bg-slate-900/30">
            <ResultCard data={result} loading={loading} />
            {result && (
              <div className="mt-2 text-center text-[10px] text-slate-500 uppercase tracking-widest">
                Données réelles ({result.count} biens)
              </div>
            )}
          </div>

          {/* Chat */}
          <div className="flex-1 min-h-0 relative">
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
      </div>

      {/* Barre d'onglets — mobile uniquement */}
      <nav className="md:hidden flex-none h-14 bg-slate-950 border-t border-slate-800 flex items-stretch z-50">
        <button
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
      </nav>
    </div>
  );
}

export default App;
