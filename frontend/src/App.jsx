import { useState } from "react";

// --- IMPORT DES COMPOSANTS ---
import SearchForm from "./components/SearchForm";
import ResultCard from "./components/ResultCard";
import MapComponent from "./components/MapComponent";
import CynicalLoader from "./components/CynicalLoader";
import ChatOracle from "./components/ChatOracle";

function App() {
  // --- ÉTATS (STATES) ---
  const [result, setResult] = useState(null); // Données reçues du Backend
  const [loading, setLoading] = useState(false); // État de chargement
  const [error, setError] = useState(null); // Gestion des erreurs
  const [mapCoords, setMapCoords] = useState(null); // Coordonnées pour centrer la carte

  // --- LOGIQUE PRINCIPALE ---
  const handleSearch = async (userInput) => {
    // Réinitialisation avant nouvelle recherche
    setLoading(true);
    setError(null);
    setResult(null);
    setMapCoords(null);

    try {
      if (!userInput.trim()) throw new Error("L'Oracle ne répond pas au vide.");

      // 1. PRÉPARATION DE LA REQUÊTE
      // On aide l'API en ajoutant "Lyon" si l'utilisateur ne l'a pas précisé
      let query = userInput.trim();
      if (
        !query.toLowerCase().includes("lyon") &&
        !query.toLowerCase().includes("villeurbanne")
      ) {
        query += ", Lyon";
      }

      console.log("🌍 Recherche via OpenStreetMap (Nominatim) :", query);

      // 2. APPEL API NOMINATIM (OpenStreetMap)
      // Beaucoup plus intelligente que Gouv.fr pour les lieux-dits et quartiers
      const geoResponse = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1&addressdetails=1`,
        {
          headers: {
            // Nominatim demande poliment d'identifier l'application
            "User-Agent": "OracleLoyersApp/1.0",
          },
        },
      );

      if (!geoResponse.ok)
        throw new Error("Erreur de connexion au service de cartographie.");

      const geoData = await geoResponse.json();

      if (!geoData || geoData.length === 0) {
        throw new Error(
          "Lieu introuvable. Soyez plus précis (ex: 'Place Bellecour').",
        );
      }

      const place = geoData[0];

      // Extraction et conversion des coordonnées (Nominatim renvoie des Strings)
      const lat = parseFloat(place.lat);
      const lon = parseFloat(place.lon);

      // Sécurité : Vérification du Code Postal
      const postcode = place.address.postcode;

      // 3. LE VIDEUR (FILTRE GÉOGRAPHIQUE)
      // On vérifie si on est bien dans le département 69 (Rhône)
      // Note: On accepte si pas de postcode (certains lieux-dits) mais on trust la lat/lon
      if (postcode && !postcode.startsWith("69")) {
        throw new Error(
          `Hors Juridiction. L'Oracle ne juge que le Grand Lyon (Trouvé : ${place.display_name}).`,
        );
      }

      // -> Mise à jour immédiate de la carte (Feedback visuel)
      setMapCoords({ lat, lon });

      // 4. APPEL BACKEND (DOCKER)
      console.log("📡 Appel de l'Oracle Backend sur localhost:8000...");

      const apiResponse = await fetch(
        "http://localhost:8000/api/analyze/vice",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            address: place.display_name, // On envoie le nom complet trouvé par OSM
            lat: lat,
            lon: lon,
          }),
        },
      );

      if (!apiResponse.ok) {
        // Gestion fine des erreurs HTTP
        if (apiResponse.status === 503)
          throw new Error(
            "La base de données est vide. Lancez le script de fusion !",
          );
        throw new Error(
          `Le Backend a refusé de répondre (Erreur ${apiResponse.status}).`,
        );
      }

      const analysisData = await apiResponse.json();
      console.log("📦 Données reçues du Backend :", analysisData);

      // -> Affichage du résultat final
      setResult(analysisData);
    } catch (err) {
      console.error("❌ ERREUR :", err);
      // Message d'erreur plus sympa pour l'utilisateur
      setError(err.message || "Erreur inconnue dans la matrice.");
    } finally {
      setLoading(false);
    }
  };

  // --- RENDU VISUEL (JSX) ---
  return (
    <div className="min-h-screen flex flex-col items-center py-10 px-4 relative overflow-x-hidden font-sans text-slate-200 bg-slate-950">
      {/* FOND D'AMBIANCE (GLOW) */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-purple-600/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      {/* EN-TÊTE & RECHERCHE */}
      <div className="w-full max-w-7xl flex flex-col items-center mb-8 relative z-10">
        <header className="text-center mb-8 space-y-2">
          <h1 className="text-4xl md:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-500 to-red-500 drop-shadow-xl">
            ORACLE<span className="text-blue-500">.DATA</span>
          </h1>
          <p className="text-slate-400 text-sm md:text-base font-light">
            Analyse de marché temps réel & prédictions locatives.
          </p>
        </header>

        <div className="w-full max-w-2xl z-20">
          <SearchForm onSearch={handleSearch} isLoading={loading} />
        </div>

        {/* ZONE DE FEEDBACK (Loader & Erreurs) */}
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

      {/* COCKPIT PRINCIPAL (GRILLE) */}
      <div className="w-full max-w-[1600px] grid grid-cols-1 lg:grid-cols-3 gap-6 px-0 md:px-4 mb-10 items-start">
        {/* COLONNE GAUCHE : CARTE INTERACTIVE */}
        <div className="lg:col-span-2 w-full h-[500px] lg:h-[700px] rounded-3xl overflow-hidden shadow-2xl shadow-purple-900/20 border border-slate-800 relative bg-slate-900/50">
          {mapCoords ? (
            /* Si on a des coordonnées, on affiche la carte centrée */
            <MapComponent lat={mapCoords.lat} lon={mapCoords.lon} />
          ) : (
            /* Sinon, on affiche l'écran d'attente stylisé */
            <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 space-y-4 relative overflow-hidden">
              <div className="absolute inset-0 opacity-5 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-white to-transparent"></div>

              {error ? (
                <div className="text-center px-6 relative z-10">
                  <div className="text-6xl mb-4 grayscale opacity-50">🦁</div>
                  <p className="text-red-400 font-mono uppercase tracking-widest text-sm font-bold">
                    Cible Perdue
                  </p>
                  <p className="text-slate-500 text-xs mt-2">
                    Réessayez avec une adresse précise.
                  </p>
                </div>
              ) : (
                <div className="relative z-10 flex flex-col items-center">
                  <div className="w-20 h-20 border-4 border-slate-700 border-dashed rounded-full animate-spin-slow mb-4"></div>
                  <p className="uppercase tracking-widest text-xs font-bold text-purple-400/60">
                    En attente de coordonnées...
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* COLONNE DROITE : RÉSULTATS & CHAT */}
        <div className="flex flex-col gap-4 h-auto lg:h-[700px]">
          {/* Bloc A : La Carte de Résultat (Data Réelle) */}
          {/* Ne s'affiche que si on a un résultat valide */}
          {result && (
            <div className="animate-fade-in-up shrink-0">
              <ResultCard data={result} />
            </div>
          )}

          {/* Bloc B : Le Chatbot (L'Assistant IA) */}
          <div className="flex-1 w-full min-h-[300px] rounded-3xl overflow-hidden shadow-xl border border-purple-500/20 bg-slate-900/80 backdrop-blur-md relative animate-fade-in-up delay-100">
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
