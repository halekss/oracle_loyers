import { useState } from 'react';
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import MapComponent from './components/MapComponent';
import ChatOracle from './components/ChatOracle';
import { api } from './services/api';

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [geoContext, setGeoContext] = useState(null);
  const [roomFilter, setRoomFilter] = useState("all");

  const getSurfaceFromFilter = (filter) => {
    switch(filter) {
      case 't1': return 25;
      case 't2': return 45;
      case 't3': return 65;
      case 't4+': return 95;
      default: return 35;
    }
  };

  const fetchPrediction = async (lat, lon, filter) => {
    setLoading(true);
    try {
      const surface = getSurfaceFromFilter(filter);
      const prediction = await api.getPrediction({
        latitude: lat,
        longitude: lon,
        surface: surface,
        room_filter: filter
      });
      setResult(prediction);
    } catch (err) {
      console.error(err);
      alert("Erreur Oracle : Impossible de récupérer l'estimation.");
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (userInput) => {
    setLoading(true);
    try {
      const query = userInput.trim() + ", Lyon, France";
      const geoRes = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`);
      const geoData = await geoRes.json();
      if (!geoData.length) throw new Error("Introuvable");

      const lat = parseFloat(geoData[0].lat);
      const lon = parseFloat(geoData[0].lon);

      setGeoContext({ lat, lon });
      await fetchPrediction(lat, lon, roomFilter);
    } catch (err) {
      alert(err.message);
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilter) => {
    setRoomFilter(newFilter);
    if (geoContext) fetchPrediction(geoContext.lat, geoContext.lon, newFilter);
  };

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-200 font-sans flex items-center justify-center overflow-hidden">
      
      <div className="w-[95%] h-[94%] flex flex-col relative">

        {/* HEADER */}
        <header className="flex-none mb-3 px-2 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-500 to-pink-500 drop-shadow-[0_0_10px_rgba(168,85,247,0.5)]">
              ORACLE IMMOBILIER
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1 bg-slate-900 rounded-full border border-slate-800">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Système Actif</span>
            </div>
          </div>
        </header>

        {/* MAIN CONTENT */}
        <main className="flex-1 w-full bg-slate-900 rounded-3xl border border-slate-800 shadow-2xl overflow-hidden flex relative ring-1 ring-white/5">
          
          {/* COLONNE GAUCHE (Carte - 60%) */}
          <div className="w-[60%] h-full relative border-r border-slate-800">
            <MapComponent 
              center={geoContext ? [geoContext.lat, geoContext.lon] : null} 
            />
          </div>

          {/* COLONNE DROITE (Dashboard - 40%) */}
          <div className="w-[40%] h-full flex flex-col bg-slate-900/95 backdrop-blur-md relative z-10">
            
            {/* SEARCH */}
            <div className="p-5 border-b border-slate-800 bg-slate-950/50 z-20">
              <SearchForm 
                onSearch={handleSearch} 
                isLoading={loading}
                currentFilter={roomFilter}
                onFilterChange={handleFilterChange} 
              />
            </div>

            {/* RESULTAT */}
            <div className="shrink-0 p-5 border-b border-slate-800 bg-slate-900/30">
              <ResultCard data={result} loading={loading} />
            </div>

            {/* CHAT - 👇 ON PASSE L'ANALYSE AU CHATBOT */}
            <div className="flex-1 min-h-0 relative">
              <ChatOracle analysis={result?.analysis} />
            </div>

          </div>
        </main>
      
      </div>
    </div>
  );
}

export default App;