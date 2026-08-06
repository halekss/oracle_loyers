import { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

// Contrat des messages postMessage échangés avec la carte HTML embarquée
// (générée par backend/scripts/generate_map.py) : voir MAP_CONTRACT.md (ORA-125).

// Centre par défaut de la carte Folium (backend/scripts/generate_map.py) —
// repli quand la bounding-box des résultats filtrés est vide (ORA-105).
const LYON_CENTER = { lat: 45.7640, lng: 4.8357, zoom: 13 };

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
  'Superstition': 'Superstition',
  'Quartiers': 'Quartiers' // Limites des arrondissements (ORA-104)
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

export default function MapComponent({ center, bounds, chatOpen = false }) {
  const [mapUrl] = useState(() => `/data/map_pings_lyon_calques.html?t=${Date.now()}`);
  const iframeRef = useRef(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);

  // ORA-116 : sur mobile (onglet "Carte"), le panneau de calques et le chat
  // ouvert se chevauchent entièrement (panneau ~256x444px, chat quasi plein
  // écran) — le chat, ouvert après, passe au-dessus et rend le panneau
  // totalement inatteignable. On le replie tant que le chat est ouvert,
  // plutôt que de laisser un élément interactif durablement masqué.
  useEffect(() => {
    if (chatOpen) setIsPanelOpen(false);
  }, [chatOpen]);
  
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
    'Superstition': false,
    'Quartiers': false
  });

  useEffect(() => {
    if (center && iframeRef.current && iframeRef.current.contentWindow) {
      iframeRef.current.contentWindow.postMessage({
        type: 'FLY_TO',
        lat: center[0], lng: center[1], zoom: center[2] || 16
      }, window.location.origin);
    }
  }, [center]);

  // ORA-105 : recentrage/zoom sur les résultats filtrés (bounding-box).
  // `bounds` vaut undefined tant qu'aucun calcul n'a eu lieu (rien à faire),
  // null quand le calcul n'a trouvé aucune coordonnée exploitable (repli
  // explicite sur le centre-ville plutôt qu'un saut brutal ou une absence
  // de réaction).
  useEffect(() => {
    if (bounds === undefined || !iframeRef.current || !iframeRef.current.contentWindow) {
      return;
    }
    if (bounds === null) {
      iframeRef.current.contentWindow.postMessage({
        type: 'FLY_TO',
        lat: LYON_CENTER.lat, lng: LYON_CENTER.lng, zoom: LYON_CENTER.zoom
      }, window.location.origin);
      return;
    }
    iframeRef.current.contentWindow.postMessage({
      type: 'FLY_TO_BOUNDS',
      bounds
    }, window.location.origin);
  }, [bounds]);

  // ORA-107 : réception du seul message iframe → React du contrat
  // (ANNONCE_CLICK, MAP_CONTRACT.md) — clic sur un marker carte, tracké
  // exactement comme AnnonceCard.jsx (même api.logAnnonceClick).
  useEffect(() => {
    const handleMessage = (e) => {
      if (e.origin !== window.location.origin) return;
      if (e.data?.type !== 'ANNONCE_CLICK') return;
      api.logAnnonceClick(e.data.id).catch((err) => {
        console.error('❌ Erreur tracking clic annonce (carte) :', err);
      });
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const sendLayerCommand = (layerKey, show) => {
    if (iframeRef.current && iframeRef.current.contentWindow) {
      const realName = LAYER_MAPPING[layerKey];
      iframeRef.current.contentWindow.postMessage({
        type: 'TOGGLE_LAYER',
        name: realName,
        show: show
      }, window.location.origin);
    }
  };

  const toggleLayer = (layerKey) => {
    const newState = !layers[layerKey];
    setLayers(prev => ({ ...prev, [layerKey]: newState }));
    sendLayerCommand(layerKey, newState);
  };

  const handleIframeLoad = () => {
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

      {/* --- BOUTON POUR OUVRIR LES FILTRES (Visible quand fermé, masqué
          tant que le chat est ouvert — ORA-116) --- */}
      {!isPanelOpen && !chatOpen && (
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
          
          <details className="mt-4 group" open>
            <summary className="text-[10px] uppercase tracking-widest text-slate-500 font-bold mb-2 cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden flex items-center justify-between hover:text-slate-300 transition-colors">
              <span>Contexte</span>
              <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-open:rotate-180">
                <polyline points="6 9 12 15 18 9"></polyline>
              </svg>
            </summary>
            <ToggleItem label="Vice" color="#e74c3c" isActive={layers['Vice']} onToggle={() => toggleLayer('Vice')} />
            <ToggleItem label="Gentrification" color="#3b82f6" isActive={layers['Gentrification']} onToggle={() => toggleLayer('Gentrification')} />
            <ToggleItem label="Nuisance" color="#f39c12" isActive={layers['Nuisance']} onToggle={() => toggleLayer('Nuisance')} />
            <ToggleItem label="Superstition" color="#9b59b6" isActive={layers['Superstition']} onToggle={() => toggleLayer('Superstition')} />
            <ToggleItem label="Quartiers" color="#a78bfa" isActive={layers['Quartiers']} onToggle={() => toggleLayer('Quartiers')} />
          </details>
          
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
