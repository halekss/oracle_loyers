import { useState } from 'react';

// Import des composants
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import MapComponent from './components/MapComponent';
import CynicalLoader from './components/CynicalLoader';
import ChatOracle from './components/ChatOracle';

function App() {
  // --- ÉTATS ---
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [mapCoords, setMapCoords] = useState(null);

  // --- LOGIQUE ---
  const handleSearch = async (userInput) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setMapCoords(null);

    try {
      // 1. PRÉPARATION INTELLIGENTE
      let queryAddress = userInput.trim();
      if (!queryAddress.toLowerCase().includes('lyon')) {
        queryAddress += ' Lyon';
      }

      // 2. GEOCODING (API Gouv - ÇA C'EST RÉEL)
      const geoResponse = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(queryAddress)}&limit=1&lat=45.7578&lon=4.8320`);
      const geoData = await geoResponse.json();

      if (!geoData.features || geoData.features.length === 0) {
        throw new Error("Adresse introuvable. Vérifiez l'orthographe.");
      }

      const feature = geoData.features[0];
      const props = feature.properties;
      const [lon, lat] = feature.geometry.coordinates;

      // 3. LE VIDEUR (FILTRE LYON)
      const postcode = props.postcode;
      if (!postcode || !postcode.startsWith('690')) {
        throw new Error(`Hors Juridiction. L'Oracle ne juge que Lyon intra-muros (${props.city} refusé).`);
      }

      // On affiche la carte (C'est la partie "Cible trouvée")
      setMapCoords({ lat, lon });

      // 4. BACKEND (ICI ON ACTIVE LE MODE SIMULATION)
      // Au lieu d'appeler le backend qui plante, on fait semblant d'attendre 1s puis on donne un résultat.
      
      setTimeout(() => {
        // --- DÉBUT FAUSSES DONNÉES ---
        const fakeResult = {
          score: Math.floor(Math.random() * (95 - 40) + 40), // Score aléatoire entre 40 et 95
          message: "L'air est chargé de particules fines et de désespoir bourgeois. Un excellent choix pour souffrir.",
          details: {
            kebabs: Math.floor(Math.random() * 10),
            bars: Math.floor(Math.random() * 20),
            adult_shops: Math.floor(Math.random() * 3),
            nightclubs: Math.floor(Math.random() * 2)
          }
        };
        // --- FIN FAUSSES DONNÉES ---
        
        setResult(fakeResult);
        setLoading(false);
      }, 1500); // On attend 1.5s pour voir le loader cynique

      /* // CODE DU BACKEND RÉEL (COMMENTÉ POUR L'INSTANT)
      const apiResponse = await fetch('http://127.0.0.1:8000/api/analyze/vice', { ... });
      if (!apiResponse.ok) throw new Error("L'Oracle est silencieux (Check Backend).");
      const analysisData = await apiResponse.json();
      setResult(analysisData);
      setLoading(false); 
      */

    } catch (err) {
      console.error(err);
      setError(err.message);
      setLoading(false);
    }
  };

  // --- RENDU ---
  return (
    <div className="min-h-screen flex flex-col items-center py-10 px-4 relative overflow-x-hidden font-sans text-slate-200">
      
      {/* FOND LUMINEUX */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      {/* HEADER & SEARCH */}
      <div className="w-full max-w-7xl flex flex-col items-center mb-8 relative z-10">
        <header className="text-center mb-8 space-y-2">
          <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 drop-shadow-xl">
            ORACLE DES LOYERS
          </h1>
          <p className="text-slate-400 text-sm md:text-base font-light">
            Analyse urbaine cynique & prédictions immobilières (Lyon Only).
          </p>
        </header>

        <div className="w-full max-w-2xl">
          <SearchForm onSearch={handleSearch} isLoading={loading} />
        </div>

        {/* Loader & Erreurs */}
        <div className="w-full min-h-[50px] flex justify-center mt-4">
          {loading && <CynicalLoader />}
          {error && (
            <div className="px-6 py-3 bg-red-950/80 border border-red-500/50 text-red-100 rounded-xl backdrop-blur-md shadow-[0_0_15px_rgba(220,38,38,0.4)] flex items-center gap-3 text-sm md:text-base font-medium animate-pulse">
              <span className="text-2xl">🚫</span> 
              <span>{error}</span>
            </div>
          )}
        </div>
      </div>

      {/* COCKPIT */}
      <div className="w-full max-w-[1600px] grid grid-cols-1 lg:grid-cols-3 gap-6 px-0 md:px-4 mb-10 items-start">
        
        {/* CARTE (Gauche) */}
        <div className="lg:col-span-2 w-full h-[500px] lg:h-[700px] rounded-3xl overflow-hidden shadow-2xl shadow-purple-900/20 border border-slate-800 relative bg-slate-900/50">
          {mapCoords ? (
            <MapComponent lat={mapCoords.lat} lon={mapCoords.lon} />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 space-y-4 relative overflow-hidden">
               <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5"></div>
               
               {error ? (
                 <div className="text-center px-6">
                    <div className="text-6xl mb-4 grayscale opacity-50">🦁</div>
                    <p className="text-red-400 font-mono uppercase tracking-widest text-sm font-bold">Zone Non Couverte</p>
                    <p className="text-slate-500 text-xs mt-2">Veuillez entrer une adresse dans Lyon (1er-9e).</p>
                 </div>
               ) : (
                 <>
                    <div className="w-20 h-20 border-4 border-slate-700 border-dashed rounded-full animate-spin-slow"></div>
                    <p className="uppercase tracking-widest text-xs font-bold text-purple-400/60">En attente de cible...</p>
                 </>
               )}
            </div>
          )}
        </div>

        {/* INTELLIGENCE (Droite) */}
        <div className="flex flex-col gap-4 h-[500px] lg:h-[700px]">
          
          {/* Bloc A : Le Verdict (S'affiche si résultat) */}
          {result && (
            <div className="animate-fade-in-up shrink-0">
              <ResultCard data={result} />
            </div>
          )}

          {/* Bloc B : Le Chatbot */}
          <div className="flex-1 w-full min-h-0 rounded-3xl overflow-hidden shadow-xl border border-purple-500/20 bg-slate-900/80 backdrop-blur-md relative animate-fade-in-up delay-100">
             <ChatOracle /> 
          </div>
        
        </div>

      </div>

      <footer className="mt-auto text-slate-600 text-[10px] uppercase tracking-widest">
        System Ready • v1.0.7 • Mode Simulation
      </footer>

    </div>
  );
}

export default App;