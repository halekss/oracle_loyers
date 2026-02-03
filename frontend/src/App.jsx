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

  // Fonction déclenchée par le bouton SCAN ou les filtres T1/T2
  const handleScan = async (quartier, typeLocal) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Appel au nouveau endpoint Backend
      const data = await api.getQuartierStats(quartier, typeLocal);
      
      if (data.found) {
        // On formate les données pour ResultCard.jsx
        // ResultCard attend { estimated_price: ..., stats: { prix_m2: ... } }
        setResult({
          estimated_price: data.prix_moyen,
          stats: { prix_m2: data.prix_m2_moyen },
          quartier: data.quartier_detecte,
          count: data.count,
          type: data.type_filtre,
          // Message d'analyse simple
          analysis: `Analyse basée sur ${data.count} annonces réelles à ${data.quartier_detecte}.`
        });

        // Mise à jour du contexte pour le Chatbot
        setChatContext(`Quartier: ${data.quartier_detecte}, Type: ${data.type_filtre}, Prix Moyen: ${data.prix_moyen}€, Prix m²: ${data.prix_m2_moyen}€`);

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
    <div className="flex h-screen w-screen bg-slate-950 text-slate-200 overflow-hidden font-sans selection:bg-purple-500/30">
      
      {/* COLONNE GAUCHE (Carte - 60%) */}
      <div className="w-[60%] h-full relative border-r border-slate-800">
        <MapComponent />
      </div>

      {/* COLONNE DROITE (Interface - 40%) */}
      <div className="w-[40%] h-full flex flex-col bg-slate-900/95 backdrop-blur-md relative z-10">
        
        {/* En-tête / Recherche */}
        <div className="p-5 border-b border-slate-800 bg-slate-950/50 z-20">
          <h1 className="text-xl font-black tracking-tighter text-white mb-4">
            ORACLE <span className="text-purple-500">DES LOYERS</span>
          </h1>
          
          <SearchForm 
            onScan={handleScan} 
            isLoading={loading} 
          />
          
          {error && (
            <div className="mt-3 text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
              {error}
            </div>
          )}
        </div>

        {/* Résultat */}
        <div className="shrink-0 p-5 border-b border-slate-800 bg-slate-900/30">
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
          />
        </div>
      </div>
    </div>
  );
}

export default App;