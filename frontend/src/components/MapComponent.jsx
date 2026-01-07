import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix pour les icônes Leaflet qui buggent parfois avec React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

export default function MapComponent({ lat, lon }) {
  if (!lat || !lon) return null;

  return (
    <div className="w-full max-w-md mx-auto mt-6 h-64 rounded-lg overflow-hidden border border-slate-700 shadow-lg z-0 relative">
      <MapContainer center={[lat, lon]} zoom={15} scrollWheelZoom={false} className="h-full w-full">
        <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <Marker position={[lat, lon]}>
          <Popup>
            ICI <br /> Zone de Vice détectée.
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}