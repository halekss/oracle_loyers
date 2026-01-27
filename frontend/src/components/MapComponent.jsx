import { useState, useEffect, useRef } from 'react';

// Le Composant Slider (Design)
const ToggleItem = ({ label, color, isActive, onToggle }) => (
  <div className="flex items-center justify-between mb-2 group cursor-pointer select-none" onClick={onToggle}>
    <div className="flex items-center gap-2">
      <div 
        className={`w-3 h-3 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] transition-all duration-300 ${isActive ? 'opacity-100' : 'opacity-30 grayscale'}`}
        style={{ backgroundColor: color, boxShadow: isActive ? `0 0 10px ${color}` : 'none' }}
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

  // État local des sliders (Tout ON par défaut)
  const [layers, setLayers] = useState({
    'MetroLines': true,
    'MetroStations': true,
    'Vice': true,
    'Gentrification': true,
    'Nuisance': true,
    'Superstition': true,
    'Immo': true,
  });

  useEffect(() => {
    setMapUrl(`http://localhost:8000/static/map_lyon.html?t=${Date.now()}`);
  }, []);

  // Fonction appelée quand tu cliques sur un slider
  const toggleLayer = (layerName) => {
    const newState = !layers[layerName];
    setLayers(prev => ({ ...prev, [layerName]: newState }));

    // On envoie l'ordre à l'iframe : "Simule un clic sur le calque X"
    if (iframeRef.current) {
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_LAYER',
        name: layerName, // Doit correspondre exactement au nom dans Python
        show: newState
      }, '*');
    }
  };

// Composant pour recentrer la carte
function ChangeView({ center }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, 14, { duration: 1.5 });
  }, [center, map]);
  return null;
}

export default function MapComponent({ listings = [], center }) {
  return (
    <div className="w-full h-full relative z-0 bg-slate-900 overflow-hidden rounded-2xl border border-slate-800 shadow-2xl">
      
      {/* IFRAME CARTE */}
      {mapUrl && (
        <iframe 
          ref={iframeRef}
          src={mapUrl}
          title="Carte Oracle Lyon"
          className="w-full h-full border-none"
          style={{ filter: "contrast(1.1) saturate(1.1)" }}
        />
      )}

      {/* OVERLAY OMBRE */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(2,6,23,0.9)] z-[400]"></div>
      
      {/* BADGE LIVE */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2 bg-slate-950/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-purple-500/30 shadow-lg">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        <span className="text-[10px] font-mono text-purple-200 uppercase tracking-widest font-bold">
          Oracle Live
        </span>
      </div>

      {/* TES SLIDERS (PANNEAU DE CONTRÔLE) */}
      <div className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-4 rounded-xl border border-slate-700/50 shadow-2xl w-64">
        <h3 className="text-[10px] uppercase tracking-widest text-slate-400 mb-3 font-bold border-b border-slate-700 pb-2">
          Contrôle des Calques
        </h3>
        
        <ToggleItem 
          label="Réseau Métro (API)" 
          color="#ef4444" 
          isActive={layers['MetroStations']} 
          onToggle={() => { toggleLayer('MetroStations'); toggleLayer('MetroLines'); }} 
        />
        
        <div className="h-px bg-slate-800 my-2"></div>

        <ToggleItem 
          label="Nuisance (Bruit/Jeux)" 
          color="#f39c12" 
          isActive={layers['Nuisance']} 
          onToggle={() => toggleLayer('Nuisance')} 
        />

        <ToggleItem 
          label="Superstition (Mort/Culte)" 
          color="#9b59b6" 
          isActive={layers['Superstition']} 
          onToggle={() => toggleLayer('Superstition')} 
        />

        <ToggleItem 
          label="Vice (Sexe/Bar)" 
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

        <div className="h-px bg-slate-800 my-2"></div>

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