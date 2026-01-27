import { useState, useEffect, useRef } from 'react';
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import MapComponent from './components/MapComponent';
import CynicalLoader from './components/CynicalLoader';
import ChatOracle from './components/ChatOracle';
import { api } from './services/api';

function App() {
  // --- ÉTATS ---
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [listings, setListings] = useState([]); 
  
  // On stocke la position trouvée (Lat/Lon) pour pouvoir rejouer la requête si on change de filtre
  const [geoContext, setGeoContext] = useState(null); 
  const [roomFilter, setRoomFilter] = useState("all"); 

  // --- 1. CHARGEMENT DES LISTINGS (Carte) ---
  useEffect(() => {
    const loadListings = async () => {
      const data = await api.getListings();
      setListings(data);
    };
    loadListings();
  }, []);

  // --- 2. LOGIQUE DE SURFACE AUTOMATIQUE ---
  const getSurfaceFromFilter = (filter) => {
    switch(filter) {
      case 't1': return 25;
      case 't2': return 45;
      case 't3': return 65;
      case 't4+': return 95;
      default: return 35; 
    }
  };

  // --- 3. FONCTION CENTRALE DE REQUÊTE ---
  // Cette fonction fait l'appel API, qu'il vienne du bouton "Scanner" ou du changement de filtre
  const fetchPrediction = async (lat, lon, filter) => {
    setLoading(true);
    try {
      const surface = getSurfaceFromFilter(filter);
      
      const prediction = await api.getPrediction({
        latitude: lat,
        longitude: lon,
        surface: surface,
        room_filter: filter // <--- ON ENVOIE LE FILTRE AU BACKEND ICI
      });

      setResult(prediction);
    } catch (err) {
      console.error(err);
      alert("L'Oracle a eu un hoquet (Erreur API)");
    } finally {
      setLoading(false);
    }
  };

  // --- 4. GESTION DES ÉVÉNEMENTS ---

  // A. L'utilisateur lance une recherche texte (ex: "Part Dieu")
  const handleSearch = async (userInput) => {
    setLoading(true);
    setResult(null);

    try {
      const query = userInput.trim() + ", Lyon, France"; 
      const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
      const geoData = await geoRes.json();

      if (!geoData.length) throw new Error("Quartier introuvable.");

      const lat = parseFloat(geoData[0].lat);
      const lon = parseFloat(geoData[0].lon);

      // On sauvegarde le contexte géographique
      setGeoContext({ lat, lon });

      // On lance la prédiction avec le filtre actuel
      await fetchPrediction(lat, lon, roomFilter);

    } catch (err) {
      alert("Erreur : " + err.message);
      setLoading(false);
    }
  };

  // B. L'utilisateur change de filtre (T1 -> T2)
  const handleFilterChange = (newFilter) => {
    setRoomFilter(newFilter);
    
    // Si on a déjà une localisation, on relance la prédiction automatiquement !
    if (geoContext) {
      fetchPrediction(geoContext.lat, geoContext.lon, newFilter);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-purple-500/30">
      <div className="max-w-7xl mx-auto p-4 md:p-8">
        
        {/* HEADER */}
        <header className="mb-12 text-center animate-fade-in">
          <h1 className="text-5xl md:text-7xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 mb-4 drop-shadow-[0_0_15px_rgba(168,85,247,0.5)]">
            ORACLE DES LOYERS
          </h1>
          <p className="text-slate-400 text-lg md:text-xl font-light tracking-wide">
            L'IA qui juge tes choix de vie (et ton budget)
          </p>
        </header>

        {/* BARRE DE RECHERCHE */}
        <div className="max-w-2xl mx-auto mb-16 relative z-50">
          <SearchForm 
            onSearch={handleSearch} 
            isLoading={loading}
            currentFilter={roomFilter}
            onFilterChange={handleFilterChange} // On utilise notre nouvelle fonction
          />
        </div>

        {/* GRILLE PRINCIPALE */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 px-0 md:px-4 mb-10 items-start">
          
          {/* GAUCHE : CARTE */}
          <div className="lg:col-span-2 w-full h-[500px] lg:h-[700px] rounded-3xl overflow-hidden shadow-2xl shadow-purple-900/20 border border-slate-800 relative bg-slate-900/50">
            <MapComponent 
              listings={listings} 
              center={geoContext ? [geoContext.lat, geoContext.lon] : [45.75, 4.85]} 
            />
          </div>

          {/* DROITE : RESULTATS & CHAT */}
          <div className="flex flex-col gap-4 h-auto lg:h-[700px]">
            {loading && <CynicalLoader />}

            {result && !loading && (
              <div className="animate-fade-in-up shrink-0">
                <ResultCard data={result} />
              </div>
            )}

            <div className="flex-1 w-full min-h-[300px] rounded-3xl overflow-hidden shadow-xl border border-purple-500/20 bg-slate-900/80 backdrop-blur-sm relative flex flex-col">
               <ChatOracle analysis={result?.analysis} />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default App;