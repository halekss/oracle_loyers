import { useState, useEffect, useRef } from 'react';

// --- LE COMPOSANT SLIDER (Ton Design) ---
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

  // État des calques
  const [layers, setLayers] = useState({
    'Immo': true,           // Les offres (Vert)
    'Metro': true,          // Métro (Rouge)
    'Vice': true,           // Bars/Sexe (Rouge foncé)
    'Nuisance': false,      // Écoles (Orange) - Désactivé par défaut
    'Gentrification': false // Bio/Yoga (Bleu) - Désactivé par défaut
  });

  // Au chargement, on définit l'URL de la carte
  useEffect(() => {
    // On pointe vers la route Flask '/maps/' qui sert le fichier HTML généré
    setMapUrl(`http://localhost:5000/maps/map_pings_lyon_calques.html?t=${Date.now()}`);
  }, []);

  // Fonction pour envoyer l'ordre à l'iframe
  const toggleLayer = (layerName) => {
    const newState = !layers[layerName];
    setLayers(prev => ({ ...prev, [layerName]: newState }));

    // C'est ici que la magie opère : on parle à l'iFrame
    if (iframeRef.current) {
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_LAYER',
        name: layerName, // Le nom doit correspondre au 'FeatureGroup' dans Python/Folium
        show: newState
      }, '*');
    }
  };

  return (
    <div className="w-full h-full relative z-0 bg-slate-900 overflow-hidden rounded-2xl border border-slate-800 shadow-2xl">
      
      {/* 1. L'IFRAME (La Carte Moche-mais-Complète de Python) */}
      {mapUrl && (
        <iframe 
          ref={iframeRef}
          src={mapUrl}
          title="Carte Oracle Lyon"
          className="w-full h-full border-none"
          // On booste un peu le contraste pour que ça fasse moins "Google Maps vieux"
          style={{ filter: "contrast(1.1) saturate(1.1)" }}
        />
      )}

      {/* 2. OVERLAY OMBRE (Pour l'ambiance) */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(2,6,23,0.9)] z-[400]"></div>
      
      {/* 3. BADGE LIVE */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2 bg-slate-950/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-purple-500/30 shadow-lg">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        <span className="text-[10px] font-mono text-purple-200 uppercase tracking-widest font-bold">
          Oracle Live
        </span>
      </div>

      {/* 4. TON PANNEAU DE CONTRÔLE (La Légende Interactive) */}
      <div className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-4 rounded-xl border border-slate-700/50 shadow-2xl w-64">
        <h3 className="text-[10px] uppercase tracking-widest text-slate-400 mb-3 font-bold border-b border-slate-700 pb-2">
          Contrôle des Calques
        </h3>
        
        {/* --- SECTION 1 : INFRASTRUCTURE --- */}
        <ToggleItem 
          label="Réseau Métro" 
          color="#ef4444" 
          isActive={layers['Metro']} 
          onToggle={() => toggleLayer('Metro')} 
        />
        
        <div className="h-px bg-slate-800 my-2"></div>

        {/* --- SECTION 2 : L'ORACLE (Vices & Vertus) --- */}
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

        {/* Note : Superstition n'est pas activé car souvent vide, on le met en disabled */}
        <ToggleItem 
          label="Superstition" 
          color="#9b59b6" 
          isActive={false} 
          disabled={true} 
          onToggle={() => {}} 
        />

        <div className="h-px bg-slate-800 my-2"></div>

        {/* --- SECTION 3 : IMMOBILIER --- */}
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