import { useState, useEffect } from 'react';

export default function MapComponent() {
  // L'URL servie par FastAPI (backend/main.py)
  // On ajoute un timestamp (?t=...) pour forcer le rafraîchissement
  // à chaque rechargement de page (évite le cache du navigateur)
  const [mapUrl, setMapUrl] = useState('');

  useEffect(() => {
    setMapUrl(`http://localhost:8000/static/map_lyon.html?t=${Date.now()}`);
  }, []);

  return (
    <div className="w-full h-full relative z-0 bg-slate-900 overflow-hidden rounded-2xl border border-slate-800 shadow-2xl">
      
      {/* 1. L'IFRAME : La fenêtre vers ta carte Folium */}
      {mapUrl && (
        <iframe 
          src={mapUrl}
          title="Carte Oracle Lyon"
          className="w-full h-full border-none"
          // Petit ajustement visuel pour que la carte s'intègre mieux
          // (Optionnel : augmente légèrement le contraste)
          style={{ filter: "contrast(1.1) saturate(1.1)" }}
        />
      )}

      {/* 2. LE STYLE "ORACLE" : Superpositions visuelles */}
      
      {/* Ombre interne pour fondre les bords de la carte dans l'interface */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_60px_rgba(2,6,23,0.9)] z-[400]"></div>
      
      {/* Badge "LIVE DATA" en haut à droite */}
      <div className="absolute top-4 right-4 z-[500] flex items-center gap-2 bg-slate-950/90 backdrop-blur-sm px-3 py-1.5 rounded-full border border-purple-500/30 shadow-lg">
        <span className="relative flex h-2.5 w-2.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
        </span>
        <span className="text-[10px] font-mono text-purple-200 uppercase tracking-widest font-bold">
          Live Intelligence
        </span>
      </div>

      {/* Légende rapide en bas à gauche (Pour rappel visuel) */}
      <div className="absolute bottom-6 left-6 z-[500] bg-slate-950/90 backdrop-blur-md p-3 rounded-xl border border-slate-800/50 text-xs text-slate-300 shadow-xl pointer-events-none">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-[#e74c3c]"></div> 
          <span>Vice & Nuit</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-[#3498db]"></div> 
          <span>Gentrification</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#2ecc71]"></div> 
          <span>Immobilier</span>
        </div>
      </div>
    </div>
  );
}