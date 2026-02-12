import { useState, useEffect, useRef } from 'react';

// --- CONFIGURATION DES CALQUES ---
const LAYER_MAPPING = {
  'Studio': 'Immo Studio/T1',
  'T2': 'Immo T2',
  'T3': 'Immo T3',
  'T4': 'Immo Grand (T4+)',
  
  'Metro': 'Metro', // Groupe unifié
  'Vice': 'Vice',
  'Nuisance': 'Nuisance',
  'Gentrification': 'Gentrification',
  'Superstition': 'Superstition'
};

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

export default function MapComponent({ center }) {
  const [mapUrl, setMapUrl] = useState('');
  const iframeRef = useRef(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  
  // --- ETATS ---
  const [layers, setLayers] = useState({
    'Studio': true,
    'T2': true,
    'T3': true,
    'T4': true,
    
    'Metro': true, // Etat unique pour tout le métro
    'Vice': true,
    'Nuisance': false,
    'Gentrification': false,
    'Superstition': false
  });

  useEffect(() => {
    setMapUrl(`/data/map_pings_lyon_calques.html?t=${Date.now()}`);
  }, []);

  useEffect(() => {
    if (center && iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage({
        type: 'FLY_TO',
        lat: center[0], lng: center[1], zoom: 16
      }, '*');
    }
  }, [center]);

  const sendLayerCommand = (layerKey, show) => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      const realName = LAYER_MAPPING[layerKey];
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_LAYER',
        name: realName,
        show: show
      }, '*');
    }
  };

  const toggleLayer = (layerKey) => {
    const newState = !layers[layerKey];
    setLayers(prev => ({ ...prev, [layerKey]: newState }));
    sendLayerCommand(layerKey, newState);
  };

  const handleIframeLoad = () => {
    console.log("🗺️ Carte chargée...");
    Object.keys(layers).forEach(key => sendLayerCommand(key, layers[key]));
  };

  return (
    <div className="w-full h-full relative z-0 bg-slate-900 overflow-hidden rounded-2xl border border-slate-800 shadow-2xl">
      {mapUrl && (
        <iframe 
          ref={iframeRef} src={mapUrl} title="Carte Oracle"
          className="w-full h-full border-none"
          onLoad={handleIframeLoad} 
          style={{ filter: "contrast(1.1) saturate(1.1)" }}
        />
      )}
      
      {/* Overlay Vignettage */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(2,6,23,0.9)] z-[400]"></div>
      
      {/* Badge Live */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2 bg-slate-950/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-purple-500/30 shadow-lg">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        <span className="text-[10px] font-mono text-purple-200 uppercase tracking-widest font-bold">Oracle Live</span>
      </div>

      {/* --- BOUTON POUR OUVRIR LES FILTRES (Visible quand fermé) --- */}
      {!isPanelOpen && (
        <button 
          onClick={() => setIsPanelOpen(true)}
          className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-3 rounded-full border border-slate-700/50 shadow-2xl hover:scale-110 transition-transform duration-200 group"
          title="Ouvrir les filtres"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-purple-400 group-hover:text-white transition-colors">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
          </svg>
        </button>
      )}

      {/* --- PANNEAU DE CONTRÔLE (Visible quand ouvert) --- */}
      {isPanelOpen && (
        <div className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-4 rounded-xl border border-slate-700/50 shadow-2xl w-64 overflow-y-auto max-h-[80vh] transition-all duration-300 ease-in-out">
          
          <div className="flex items-center justify-between mb-3 border-b border-slate-700 pb-2">
            <h3 className="text-[10px] uppercase tracking-widest text-slate-400 font-bold">
              Contrôle des Calques
            </h3>
            <button onClick={() => setIsPanelOpen(false)} className="text-slate-500 hover:text-white transition-colors p-1">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 font-bold">Transports</h3>
          {/* BOUTON UNIQUE METRO */}
          <ToggleItem label="Métro (Lignes & Stations)" color="#818181" isActive={layers['Metro']} onToggle={() => toggleLayer('Metro')} />
          
          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 mt-4 font-bold">Contexte</h3>
          <ToggleItem label="Vice" color="#e74c3c" isActive={layers['Vice']} onToggle={() => toggleLayer('Vice')} />
          <ToggleItem label="Gentrification" color="#3b82f6" isActive={layers['Gentrification']} onToggle={() => toggleLayer('Gentrification')} />
          <ToggleItem label="Nuisance" color="#f39c12" isActive={layers['Nuisance']} onToggle={() => toggleLayer('Nuisance')} />
          <ToggleItem label="Superstition" color="#9b59b6" isActive={layers['Superstition']} onToggle={() => toggleLayer('Superstition')} />
          
          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 mt-4 font-bold">Offres Immobilières</h3>
          <ToggleItem label="Studio / T1" color="#22c55e" isActive={layers['Studio']} onToggle={() => toggleLayer('Studio')} />
          <ToggleItem label="Apparts T2" color="#22c55e" isActive={layers['T2']} onToggle={() => toggleLayer('T2')} />
          <ToggleItem label="Apparts T3" color="#22c55e" isActive={layers['T3']} onToggle={() => toggleLayer('T3')} />
          <ToggleItem label="Grands (T4+)" color="#22c55e" isActive={layers['T4']} onToggle={() => toggleLayer('T4')} />
        </div>
      )}
    </div>
  );
}