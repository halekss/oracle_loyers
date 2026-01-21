import { useState, useEffect, useRef } from 'react';

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
  
  // On stocke les infos géographiques pour pouvoir les réutiliser quand on change de filtre
  const [geoContext, setGeoContext] = useState(null); // { lat, lon, address }
  
  const [roomFilter, setRoomFilter] = useState("all"); 

  // Pour éviter que le useEffect ne se lance au tout premier chargement de la page
  const isFirstRender = useRef(true);

  // --- 1. RECHERCHE INITIALE (Celle qui trouve le GPS) ---
  const handleSearch = async (userInput) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      if (!userInput.trim()) throw new Error("L'Oracle ne répond pas au vide.");

      let query = userInput.trim();
      if (!query.toLowerCase().includes('lyon') && !query.toLowerCase().includes('villeurbanne')) {
        query += ', Lyon';
      }

      console.log("🌍 Cartographie :", query);
      const geoResponse = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&addressdetails=1`, {
        headers: { 'User-Agent': 'OracleLoyersApp/1.0' }
      });

      if (!geoResponse.ok) throw new Error("Erreur Carto.");
      const geoData = await geoResponse.json();
      if (!geoData || geoData.length === 0) throw new Error("Adresse introuvable.");

      const place = geoData[0];
      const lat = parseFloat(place.lat);
      const lon = parseFloat(place.lon);
      const postcode = place.address.postcode;

      if (postcode && !postcode.startsWith('69')) {
         throw new Error(`Hors Zone (Trouvé : ${place.display_name}).`);
      }

      // ✅ ON SAUVEGARDE LE CONTEXTE GÉOGRAPHIQUE
      // Cela va déclencher le useEffect ci-dessous automatiquement !
      setGeoContext({ lat, lon, address: place.display_name });

    } catch (err) {
      console.error("❌", err);
      setError(err.message || "Erreur inconnue.");
      setLoading(false); // On arrête le loading seulement si erreur ici
    }
  };

  // --- 2. EFFET AUTOMATIQUE (Dès que GPS ou FILTRE change) ---
  useEffect(() => {
    // Si pas de coordonnées, on ne fait rien
    if (!geoContext) return;

    const fetchBackendAnalysis = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log(`📡 Appel Backend (Filtre: ${roomFilter}) pour ${geoContext.address}...`);
        
        const apiResponse = await fetch('http://localhost:8000/api/analyze/vice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              address: geoContext.address,
              lat: geoContext.lat,
              lon: geoContext.lon,
              filter_type: roomFilter // 🔥 Le filtre est passé ici
          }),
        });

        if (!apiResponse.ok) {
           if (apiResponse.status === 503) throw new Error("Base de données vide.");
           throw new Error(`Erreur Backend (${apiResponse.status}).`);
        }

        const analysisData = await apiResponse.json();
        setResult(analysisData);

      } catch (err) {
        console.error("❌ Erreur Backend:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    // On lance l'analyse
    fetchBackendAnalysis();

  }, [geoContext, roomFilter]); // 🔥 Ce tableau dit : "Relance si geoContext OU roomFilter change"


  // --- RENDU ---
  return (
    <div className="min-h-screen flex flex-col items-center py-10 px-4 relative overflow-x-hidden font-sans text-slate-200 bg-slate-950">
      
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      <div className="w-full max-w-7xl flex flex-col items-center mb-8 relative z-10">
        <header className="text-center mb-8 space-y-2">
          <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 drop-shadow-xl">
            ORACLE<span className="text-blue-500">.DATA</span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base font-light">
            Analysez les loyers par type de bien en temps réel.
          </p>
        </header>

        <div className="w-full max-w-2xl z-20">
          <SearchForm 
            onSearch={handleSearch} 
            isLoading={loading} 
            currentFilter={roomFilter}
            onFilterChange={setRoomFilter} // Le clic change le state -> déclenche le useEffect
          />
        </div>

        <div className="w-full min-h-[50px] flex justify-center mt-4">
          {loading && <CynicalLoader />}
          {error && (
            <div className="px-6 py-3 bg-red-950/80 border border-red-500/50 text-red-100 rounded-xl backdrop-blur-md animate-pulse">
              <span>🚫 {error}</span>
            </div>
          )}
        </div>
      </div>

      <div className="w-full max-w-[1600px] grid grid-cols-1 lg:grid-cols-3 gap-6 px-0 md:px-4 mb-10 items-start">
        
        {/* CARTE */}
        <div className="lg:col-span-2 w-full h-[500px] lg:h-[700px] rounded-3xl overflow-hidden shadow-2xl shadow-purple-900/20 border border-slate-800 relative bg-slate-900/50">
          {geoContext ? (
            <MapComponent lat={geoContext.lat} lon={geoContext.lon} />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 relative overflow-hidden">
               <div className="absolute inset-0 opacity-5 bg-white"></div>
               <p className="uppercase tracking-widest text-xs font-bold text-purple-400/60">En attente de coordonnées...</p>
            </div>
          )}
        </div>

        {/* RÉSULTATS */}
        <div className="flex flex-col gap-4 h-auto lg:h-[700px]">
          {result && (
            <div className="animate-fade-in-up shrink-0">
              <ResultCard data={result} />
            </div>
          )}
          <div className="flex-1 w-full min-h-[300px] rounded-3xl overflow-hidden shadow-xl border border-purple-500/20 bg-slate-900/80 backdrop-blur-md relative animate-fade-in-up delay-100">
             <ChatOracle /> 
          </div>
        </div>

      </div>

      <footer className="mt-auto text-slate-600 text-[10px] uppercase tracking-widest pb-4">
        Oracle Data System • V4.0 Reactive
      </footer>
    </div>
  );
}

export default App;