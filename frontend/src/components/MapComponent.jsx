import { useState, useEffect, useRef } from 'react';

// --- CONFIGURATION : TRADUCTION REACT -> CARTE ---
// Clé = Ton nom de bouton | Valeur = Le nom exact du calque dans Folium (Python)
const LAYER_MAPPING = {
  'Immo': 'Offres Immobilières',
  'Metro': 'Réseau Métro (API)',
  'Vice': 'Vice (Sexe/Bar)',
  'Nuisance': 'Nuisance (Bruit/Jeux)',
  'Gentrification': 'Gentrification (Bio)',
  'Superstition': 'Superstition (Mort/Culte)'
};

// --- LE COMPOSANT SLIDER ---
const ToggleItem = ({ label, color, isActive, onToggle, disabled }) => (
  <div 
    className={`flex items-center justify-between mb-2 group select-none transition-opacity duration-300 ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`} 
    onClick={!disabled ? onToggle : undefined}
  >
    <div className="flex items-center gap-2">
      <div 
        className={`w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] transition-all duration-300 ${isActive ? 'opacity-100' : 'opacity-30 grayscale'}`}
        style={{ backgroundColor: color, boxShadow: isActive && !disabled ? `0 0 10px ${color}` : 'none' }}
      ></div>
      <span className={`text-xs font-medium transition-colors ${isActive ? 'text-slate-200' : 'text-slate-500'}`}>
        {label}
      </span>
    </div>
    <div className={`w-9 h-5 flex items-center bg-slate-800 rounded-full p-1 duration-300 ease-in-out ${isActive ? 'bg-slate-700' : 'bg-slate-900 border border-slate-800'}`}>
      <div 
        className={`bg-white w-3 h-3 rounded-full shadow-md transform duration-300 ease-in-out ${isActive ? 'translate-x-4 bg-purple-400' : ''}`}
      ></div>
    </div>
  </div>
);

export default function MapComponent() {
  const [mapUrl, setMapUrl] = useState('');
  const iframeRef = useRef(null);

  // État des calques (True = Activé par défaut)
  const [layers, setLayers] = useState({
    'Immo': true,
    'Metro': true,
    'Vice': true,
    'Nuisance': false,
    'Gentrification': false,
    'Superstition': false
  });

  useEffect(() => {
    // IMPORTANT : On pointe vers le dossier static de FastAPI
    setMapUrl(`http://localhost:5000/static/map_lyon.html?t=${Date.now()}`);
  }, []);

  // Fonction magique pour parler à l'Iframe
  const sendLayerCommand = (layerKey, show) => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      const realLayerName = LAYER_MAPPING[layerKey]; // Traduction ici !
      
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_LAYER',
        name: realLayerName,
        show: show
      }, '*');
    }
  };

  // Gestion du clic
  const toggleLayer = (layerKey) => {
    const newState = !layers[layerKey];
    setLayers(prev => ({ ...prev, [layerKey]: newState }));
    sendLayerCommand(layerKey, newState);
  };

  // Synchronisation initiale quand l'iframe a fini de charger
  const handleIframeLoad = () => {
    // On force l'état actuel pour être sûr que la carte est synchro avec les boutons
    Object.keys(layers).forEach(key => {
      sendLayerCommand(key, layers[key]);
    });
  };

  return (
    <div className="w-full h-full relative z-0 bg-slate-900 overflow-hidden rounded-2xl border border-slate-800 shadow-2xl">
      
      {mapUrl && (
        <iframe 
          ref={iframeRef}
          src={mapUrl}
          title="Carte Oracle"
          className="w-full h-full border-none"
          onLoad={handleIframeLoad} // Synchro au chargement
          style={{ filter: "contrast(1.1) saturate(1.1)" }}
        />
      )}

      {/* Overlay Ombre */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(2,6,23,0.9)] z-[400]"></div>
      
      {/* Badge Live */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2 bg-slate-950/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-purple-500/30 shadow-lg">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        <span className="text-[10px] font-mono text-purple-200 uppercase tracking-widest font-bold">Oracle Live</span>
      </div>

      {/* Panneau de Contrôle */}
      <div className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-4 rounded-xl border border-slate-700/50 shadow-2xl w-64">
        <h3 className="text-[10px] uppercase tracking-widest text-slate-400 mb-3 font-bold border-b border-slate-700 pb-2">
          Contrôle des Calques
        </h3>
        
        {/* INFRASTRUCTURE */}
        <ToggleItem 
          label="Réseau Métro" 
          color="#ef4444" 
          isActive={layers['Metro']} 
          onToggle={() => toggleLayer('Metro')} 
        />
        
        <ToggleItem label="Réseau Métro" color="#ef4444" isActive={layers['Metro']} onToggle={() => toggleLayer('Metro')} />
        <div className="h-px bg-slate-800 my-2"></div>

        {/* ORACLE (Vices) */}
        <ToggleItem 
          label="Vice (Bars/Sexe)" 
          color="#e74c3c" 
          isActive={layers['Vice']} 
          onToggle={() => toggleLayer('Vice')} 
        />

        <ToggleItem 
          label="Gentrification (Bio)" 
          color="#3b82f6" 
          isActive={layers['Gentrification']} 
          onToggle={() => toggleLayer('Gentrification')} 
        />

        <ToggleItem 
          label="Nuisance (Écoles)" 
          color="#f39c12" 
          isActive={layers['Nuisance']} 
          onToggle={() => toggleLayer('Nuisance')} 
        />

        <ToggleItem 
          label="Superstition" 
          color="#9b59b6" 
          isActive={layers['Superstition']} 
          onToggle={() => toggleLayer('Superstition')} 
          disabled={false} // J'ai réactivé superstition au cas où
        />

        <div className="h-px bg-slate-800 my-2"></div>

        {/* IMMOBILIER */}
        <ToggleItem 
          label="Offres Immobilières" 
          color="#22c55e" 
          isActive={layers['Immo']} 
          onToggle={() => toggleLayer('Immo')} 
        />

      </div>
    </div>
  );
}