import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useEffect } from 'react';

// Icône Oracle (Violette) pour la position recherchée
const oracleIcon = L.divIcon({
  className: 'custom-icon',
  html: `<div style="background-color: #9333ea; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 20px #9333ea; animation: pulse 2s infinite;"></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

// Icône Standard (Bleue) pour les listings
const defaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

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
    <div className="w-full h-full relative z-0">
      <MapContainer 
        center={center} 
        zoom={13} 
        scrollWheelZoom={true} 
        className="h-full w-full bg-slate-900"
      >
        <ChangeView center={center} />
        <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {/* Points bleus des données existantes */}
        {listings.map((item, idx) => (
          <Marker 
            key={idx} 
            position={[item.latitude, item.longitude]} 
            icon={defaultIcon}
          >
            <Popup className="text-slate-900">
              <b>{item.prix} €</b><br/>{item.surface} m²
            </Popup>
          </Marker>
        ))}

        {/* Point violet de la recherche utilisateur */}
        <Marker position={center} icon={oracleIcon}>
          <Popup>🎯 Cible analysée</Popup>
        </Marker>

      </MapContainer>
    </div>
  );
}