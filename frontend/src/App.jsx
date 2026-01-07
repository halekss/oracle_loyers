import { useState } from 'react';
import SearchForm from './components/SearchForm';
import ResultCard from './components/ResultCard';
import MapComponent from './components/MapComponent';

function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // On stocke les coordonnées GPS séparément pour afficher la carte 
  // même si le backend est lent ou plante
  const [mapCoords, setMapCoords] = useState(null);

  const handleSearch = async (address) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setMapCoords(null);

    try {
      // --- ÉTAPE 1 : GEOCODING (Front -> API Gouv) ---
      // On transforme le texte "Rue Victor Hugo" en GPS [lat, lon]
      const geoResponse = await fetch(`https://api-adresse.data.gouv.fr/search/?q=${encodeURIComponent(address)}&limit=1`);
      const geoData = await geoResponse.json();

      if (!geoData.features || geoData.features.length === 0) {
        throw new Error("Adresse introuvable. Soyez plus précis (Ville, Code Postal).");
      }

      // Attention : GeoJSON renvoie [Longitude, Latitude], Leaflet veut [Lat, Lon]
      const [lon, lat] = geoData.features[0].geometry.coordinates;
      
      console.log("📍 GPS trouvé :", lat, lon);
      setMapCoords({ lat, lon }); // On met à jour la carte immédiatement

      // --- ÉTAPE 2 : ANALYSE (Front -> Ton Backend Python) ---
      // On envoie le GPS au cerveau pour compter les kebabs
      const apiResponse = await fetch('http://127.0.0.1:8000/api/analyze/vice', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ lat, lon, address }),
      });

      if (!apiResponse.ok) {
        throw new Error("L'Oracle est silencieux (Vérifie que le terminal Backend tourne sur le port 8000).");
      }

      const analysisData = await apiResponse.json();
      setResult(analysisData);

    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center py-12 px-4 font-sans text-slate-200">
      
      {/* HEADER */}
      <header className="text-center mb-10 space-y-2">
        <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 drop-shadow-lg">
          ORACLE DES LOYERS
        </h1>
        <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto font-light">
          Découvrez ce que votre agent immobilier ne vous dira <span className="italic text-purple-400">jamais</span>.
        </p>
      </header>

      {/* FORMULAIRE */}
      <SearchForm onSearch={handleSearch} isLoading={loading} />

      {/* GESTION D'ERREUR */}
      {error && (
        <div className="mt-6 p-4 bg-red-900/30 border border-red-800 text-red-200 rounded-lg max-w-md w-full text-center animate-pulse">
          ⚠️ {error}
        </div>
      )}

      {/* RESULTATS */}
      <div className="w-full max-w-md mt-6 space-y-6">
        
        {/* La carte s'affiche dès qu'on a les coordonnées */}
        {mapCoords && (
          <div className="animate-fade-in-up">
             <MapComponent lat={mapCoords.lat} lon={mapCoords.lon} />
          </div>
        )}

        {/* Le verdict s'affiche quand le backend a répondu */}
        {result && (
          <div className="animate-fade-in-up delay-100">
            <ResultCard data={result} />
          </div>
        )}
      </div>

    </div>
  );
}

export default App;