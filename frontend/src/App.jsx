import { useState } from 'react';

// Import des composants (Je suppose qu'ils existent déjà dans ton projet)
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
      // On ajoute Lyon si l'utilisateur a oublié, pour aider l'API Gouv
      if (!queryAddress.toLowerCase().includes('lyon')) {
        queryAddress += ' Lyon';
      }

      // 2. GEOCODING (API Gouv) - Pour placer la carte AVANT d'analyser
      console.log("📍 Géocodage Gouv.fr pour :", queryAddress);
      const geoResponse = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(queryAddress)}&limit=1`);
      const geoData = await geoResponse.json();

      if (!geoData.features || geoData.features.length === 0) {
        throw new Error("Adresse introuvable. Vérifiez l'orthographe.");
      }

      const feature = geoData.features[0];
      const props = feature.properties;
      const [lon, lat] = feature.geometry.coordinates;

      // 3. LE VIDEUR (FILTRE LYON)
      // On vérifie que c'est bien à Lyon (69XXX)
      const postcode = props.postcode;
      if (!postcode || !postcode.startsWith('69')) {
        throw new Error(`Hors Juridiction. L'Oracle ne juge que le Grand Lyon (${props.city} refusé).`);
      }

      // Mise à jour de la carte immédiate (Feedback visuel)
      setMapCoords({ lat, lon });

      // 4. APPEL BACKEND (LE VRAI CERVEAU 🧠)
      console.log("📡 Appel de l'Oracle Backend...");
      
      const apiResponse = await fetch('http://127.0.0.1:8000/api/analyze/vice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            address: props.label, // On envoie l'adresse propre trouvée par Gouv.fr
            lat: lat,
            lon: lon
        }),
      });

      if (!apiResponse.ok) {
        throw new Error("Le Backend ne répond pas. Vérifiez le terminal Python.");
      }

      const analysisData = await apiResponse.json();
      console.log("📦 Données reçues du Backend :", analysisData);
      
      setResult(analysisData);

    } catch (err) {
      console.error("❌ ERREUR :", err);
      setError(err.message || "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  // --- RENDU (Ton Design Intact) ---
  return (
    <div className="min-h-screen flex flex-col items-center py-10 px-4 relative overflow-x-hidden font-sans text-slate-200 bg-slate-950">
      
      {/* FOND LUMINEUX */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      {/* HEADER & SEARCH */}
      <div className="w-full max-w-7xl flex flex-col items-center mb-8 relative z-10">
        <header className="text-center mb-8 space-y-2">
          <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 drop-shadow-xl">
            ORACLE<span className="text-blue-500">.DATA</span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base font-light">
            Analyse de marché temps réel & prédictions locatives.
          </p>
        </header>

        <div className="w-full max-w-2xl">
          {/* On passe la fonction handleSearch au formulaire */}
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
        
        {/* COLONNE GAUCHE : CARTE */}
        <div className="lg:col-span-2 w-full h-[500px] lg:h-[700px] rounded-3xl overflow-hidden shadow-2xl shadow-purple-900/20 border border-slate-800 relative bg-slate-900/50">
          {mapCoords ? (
            <MapComponent lat={mapCoords.lat} lon={mapCoords.lon} />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 space-y-4 relative overflow-hidden">
               {/* Pattern de fond subtil */}
               <div className="absolute inset-0 opacity-5 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white to-transparent"></div>
               
               {error ? (
                 <div className="text-center px-6 relative z-10">
                    <div className="text-6xl mb-4 grayscale opacity-50">🦁</div>
                    <p className="text-red-400 font-mono uppercase tracking-widest text-sm font-bold">Cible Perdue</p>
                    <p className="text-slate-500 text-xs mt-2">Réessayez avec une adresse précise.</p>
                 </div>
               ) : (
                 <div className="relative z-10 flex flex-col items-center">
                    <div className="w-20 h-20 border-4 border-slate-700 border-dashed rounded-full animate-spin-slow mb-4"></div>
                    <p className="uppercase tracking-widest text-xs font-bold text-purple-400/60">En attente de coordonnées...</p>
                 </div>
               )}
            </div>
          )}
        </div>

        {/* COLONNE DROITE : RESULTATS & CHAT */}
        <div className="flex flex-col gap-4 h-[500px] lg:h-[700px]">
          
          {/* Bloc A : La Carte de Résultat (Data Réelle) */}
          {result && (
            <div className="animate-fade-in-up shrink-0">
              <ResultCard data={result} />
            </div>
          )}

          {/* Bloc B : Le Chatbot (Décoratif pour l'instant ou fonctionnel selon ton code) */}
          <div className="flex-1 w-full min-h-0 rounded-3xl overflow-hidden shadow-xl border border-purple-500/20 bg-slate-900/80 backdrop-blur-md relative animate-fade-in-up delay-100">
             <ChatOracle /> 
          </div>
        
        </div>

      </div>

      <footer className="mt-auto text-slate-600 text-[10px] uppercase tracking-widest pb-4">
        Oracle Data System • Connected to Localhost:8000
      </footer>

    </div>
  );
}

export default App;