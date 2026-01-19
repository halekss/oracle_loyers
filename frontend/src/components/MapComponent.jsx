import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Icône personnalisée "Oracle"
const oracleIcon = L.divIcon({
  className: 'custom-icon',
  html: `<div style="
    background-color: #9333ea;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 3px solid white;
    box-shadow: 0 0 20px #9333ea; 
    animation: pulse 2s infinite;
  "></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

export default function MapComponent({ lat, lon }) {
  if (!lat || !lon) return null;

  return (
    // CORRECTION ICI : 
    // On met h-full w-full pour qu'elle remplisse exactement la colonne définie dans App.jsx
    // J'ai retiré les rounded-3xl et shadow ici car c'est App.jsx qui gère le cadre maintenant.
    <div className="w-full h-full relative z-0">
      
      <MapContainer 
        center={[lat, lon]} 
        zoom={16} 
        scrollWheelZoom={false} 
        className="h-full w-full bg-slate-900"
      >
        <TileLayer
            attribution='&copy; OpenStreetMap'
            // Carte style "Dark Matter"
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <Marker position={[lat, lon]} icon={oracleIcon}>
          <Popup className="text-slate-900 font-bold">
            Cible Localisée.
          </Popup>
        </Marker>
      </MapContainer>
      
      {/* Vignette d'ambiance (ombre interne) */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_50px_rgba(0,0,0,0.5)] z-[400]"></div>
    </div>
  );
}