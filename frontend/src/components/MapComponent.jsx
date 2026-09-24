import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react';
import { api, getApiBaseUrl } from '../services/api';
import mapLayersConfig from '../config/mapLayers.config.json';
import { LAYER_MAPPING, layersByGroup } from '../services/mapLayers';

// Contrat des messages postMessage échangés avec la carte HTML embarquée
// (générée par backend/scripts/generate_map.py) : voir MAP_CONTRACT.md (ORA-125).

// Centre par défaut de chaque carte Folium (backend/scripts/generate_map.py,
// VILLE_CONFIG) — repli quand la bounding-box des résultats filtrés est vide
// (ORA-105), par ville (ORA-71 POC).
const VILLE_CENTERS = {
  lyon: { lat: 45.7640, lng: 4.8357, zoom: 13 },
  lille: { lat: 50.6292, lng: 3.0573, zoom: 13 },
};

// --- CONFIGURATION DES CALQUES ---
// Source de vérité unique (frontend/src/config/mapLayers.config.json),
// consommée aussi par backend/scripts/generate_map.py (ORA-130) : ajouter un
// calque = éditer ce JSON, pas ce composant ET le script Python séparément.
// `LAYER_MAPPING` (clé interne React -> libellé du calque Folium/TOGGLE_LAYER)
// dérive de ce fichier plutôt que d'être recopié à la main.
// Exporté (ORA-178) : réutilisé tel quel par la vue "Calques" du rail
// (App.jsx) pour afficher les mêmes lignes que le panneau flottant
// ci-dessous, sans dupliquer le style des lignes.
export const ToggleItem = ({ label, color, isActive, onToggle, disabled, count }) => (
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
      {/* ORA-172 : compteur calculé depuis les données à la génération de la
          carte (map_metadata_<ville>.json), jamais codé en dur. */}
      {count != null && (
        <span className="text-[10px] text-slate-500 font-mono">{count}</span>
      )}
    </div>
    <div className={`w-9 h-5 flex items-center bg-slate-800 rounded-full p-1 duration-300 ease-in-out ${isActive ? 'bg-slate-700' : 'bg-slate-900 border border-slate-800'}`}>
      <div 
        className={`bg-white w-3 h-3 rounded-full shadow-md transform duration-300 ease-in-out ${isActive ? 'translate-x-4 bg-purple-400' : ''}`}
      ></div>
    </div>
  </div>
);

// `hidePanel` (ORA-178, optionnel) : masque le panneau flottant "Contrôle
// des calques" — utilisé sur desktop une fois que la vue "Calques" du rail
// (App.jsx) affiche les mêmes lignes dans la feuille de contenu, pour éviter
// un doublon. Mobile (pas de rail) garde `hidePanel=false` : c'est son seul
// point d'accès aux calques, comportement inchangé.
// `onLayersChange`/`onAnnonceClick` (optionnels) : MapComponent reste
// l'unique source de vérité (état interne inchangé, contrat postMessage
// intact) — ces callbacks se contentent de refléter son état vers le
// parent, qui pilote alors les calques à distance via la ref (`toggleLayer`)
// plutôt que de dupliquer la logique d'envoi des messages à l'iframe.
const MapComponent = forwardRef(function MapComponent(
  { center, bounds, chatOpen = false, ville = 'lyon', hidePanel = false, onLayersChange, onAnnonceClick },
  ref,
) {
  const [mapUrl, setMapUrl] = useState(() => `/data/map_pings_${ville}_calques.html?t=${Date.now()}`);
  const iframeRef = useRef(null);
  const [isPanelOpen, setIsPanelOpen] = useState(true);

  // ORA-71 POC : recharge l'iframe carte statique quand la ville active
  // change (sélecteur Lyon/Lille) — le `useState` initial ne se réévalue
  // qu'au montage, insuffisant si l'utilisateur bascule de ville sans que
  // MapComponent soit démonté/remonté.
  useEffect(() => {
    setMapUrl(`/data/map_pings_${ville}_calques.html?t=${Date.now()}`);
  }, [ville]);

  // ORA-172 : compteurs du panneau de calques (Vice 526, T2 300...), écrits
  // par generate_map.py dans map_metadata_<ville>.json à chaque génération —
  // fichier statique servi par Vite/nginx, pas un appel /api/.
  const [layerCounts, setLayerCounts] = useState({});
  useEffect(() => {
    let cancelled = false;
    fetch(`/data/map_metadata_${ville}.json?t=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled) setLayerCounts(data?.layer_counts || {});
      })
      .catch(() => {
        if (!cancelled) setLayerCounts({});
      });
    return () => {
      cancelled = true;
    };
  }, [ville]);

  // ORA-116 : sur mobile (onglet "Carte"), le panneau de calques et le chat
  // ouvert se chevauchent entièrement (panneau ~256x444px, chat quasi plein
  // écran) — le chat, ouvert après, passe au-dessus et rend le panneau
  // totalement inatteignable. On le replie tant que le chat est ouvert,
  // plutôt que de laisser un élément interactif durablement masqué.
  useEffect(() => {
    if (chatOpen) setIsPanelOpen(false);
  }, [chatOpen]);
  
  // --- ETATS ---
  // Visibilité initiale de chaque calque : dérivée de mapLayers.config.json
  // (`defaultVisible`), même source que le `show=` des FeatureGroup/GeoJson
  // Folium correspondants côté generate_map.py (ORA-130).
  const [layers, setLayers] = useState(() =>
    Object.fromEntries(mapLayersConfig.map((layer) => [layer.key, layer.defaultVisible]))
  );

  // ORA-178 : reflète l'état interne (calques + compteurs) vers le parent à
  // chaque changement, pour que la vue "Calques" du rail affiche exactement
  // ce que ce composant sait déjà, sans jamais recalculer/refetcher lui-même.
  useEffect(() => {
    onLayersChange?.(layers, layerCounts);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layers, layerCounts]);

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
      const fallbackCenter = VILLE_CENTERS[ville] || VILLE_CENTERS.lyon;
      iframeRef.current.contentWindow.postMessage({
        type: 'FLY_TO',
        lat: fallbackCenter.lat, lng: fallbackCenter.lng, zoom: fallbackCenter.zoom
      }, window.location.origin);
      return;
    }
    iframeRef.current.contentWindow.postMessage({
      type: 'FLY_TO_BOUNDS',
      bounds
    }, window.location.origin);
  }, [bounds, ville]);

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
      onAnnonceClick?.(e.data.id);
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  // Fond de carte : les tuiles passent par le proxy du backend (/api/tiles),
  // qui détient la clé CARTO — aucune clé côté navigateur. L'URL dépend du
  // déploiement (VITE_API_URL), d'où son envoi à l'iframe au chargement plutôt
  // que son écriture dans la carte générée, versionnée (MAP_CONTRACT.md,
  // SET_TILE_URL).
  const sendTileUrl = () => {
    if (iframeRef.current?.contentWindow) {
      iframeRef.current.contentWindow.postMessage(
        { type: 'SET_TILE_URL', url: `${getApiBaseUrl()}/tiles/{z}/{x}/{y}{r}.png` },
        window.location.origin,
      );
    }
  };

  const handleIframeLoad = () => {
    sendTileUrl();
    Object.keys(layers).forEach(key => sendLayerCommand(key, layers[key]));
  };

  // ORA-178 : pilotage à distance depuis la vue "Calques" du rail (App.jsx) —
  // réutilise `toggleLayer` telle quelle, jamais de second état/logique
  // d'envoi des calques ailleurs dans le code.
  useImperativeHandle(ref, () => ({ toggleLayer }));

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
      {!hidePanel && !isPanelOpen && !chatOpen && (
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
      {!hidePanel && isPanelOpen && (
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
          {layersByGroup('transports').map((layer) => (
            <ToggleItem
              key={layer.key}
              label={layer.label}
              color={layer.uiColor}
              isActive={layers[layer.key]}
              onToggle={() => toggleLayer(layer.key)}
            />
          ))}

          {/* ORA-172 : "Les 4 Cavaliers" (maquette 04) — toujours dépliée,
              contrairement à l'ancien groupe générique "Contexte" repliable
              (le calque "Quartiers", pas un cavalier, y reste rattaché faute
              de groupe dédié dans mapLayers.config.json). */}
          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 mt-4 font-bold">Les 4 Cavaliers</h3>
          {layersByGroup('contexte').map((layer) => (
            <ToggleItem
              key={layer.key}
              label={layer.label}
              color={layer.uiColor}
              isActive={layers[layer.key]}
              onToggle={() => toggleLayer(layer.key)}
              count={layerCounts[layer.key]}
            />
          ))}

          <h3 className="text-[10px] uppercase tracking-widest text-slate-500 mb-2 mt-4 font-bold">Offres Immobilières</h3>
          {layersByGroup('immobilier').map((layer) => (
            <ToggleItem
              key={layer.key}
              label={layer.label}
              color={layer.uiColor}
              isActive={layers[layer.key]}
              onToggle={() => toggleLayer(layer.key)}
              count={layerCounts[layer.key]}
            />
          ))}
        </div>
      )}
    </div>
  );
});

export default MapComponent;
