import { useState } from 'react';
import { layersByGroup } from '../services/mapLayers';
import { CAVALIER_STYLES } from '../services/cavaliersDisplay';
import CavalierShapeIcon from './CavalierShapeIcon';

// Libellés compacts des calques "Offres Immobilières" (maquette vue-calques.png,
// ex. "T1 · T2 · T3") — les labels de mapLayers.config.json ("Studio / T1",
// "Grands (T4+)"...) sont trop longs pour tenir sur une seule ligne de légende.
const IMMO_SHORT_LABELS = { Studio: 'T1', T2: 'T2', T3: 'T3', T4: 'T4+' };
const ANNONCES_COLOR = '#22C55E';

function SectionTitle({ children }) {
  return (
    <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">{children}</p>
  );
}

function ChevronIcon({ collapsed }) {
  return (
    <svg
      width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      className={`transition-transform ${collapsed ? '-rotate-90' : ''}`}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// Légende unique de la carte (ORA-183, v3) — remplace l'ancienne légende
// Folium (build_legend_html, supprimée de generate_map.py) ET la précédente
// légende React limitée aux seuls cavaliers : ne liste désormais que les
// calques réellement actifs, regroupés par section (Annonces/Métro/
// Cavaliers/Rayon). Une section sans calque actif n'apparaît pas ; sans
// aucun calque actif ni rayon, rien n'est rendu du tout — jamais de légende
// vide flottant sur la carte.
export default function MapLegend({ layers, focus }) {
  const [collapsed, setCollapsed] = useState(false);

  const activeImmo = layersByGroup('immobilier').filter((layer) => layers?.[layer.key]);
  const activeTransport = layersByGroup('transports').filter((layer) => layers?.[layer.key]);
  const activeCavaliers = CAVALIER_STYLES.filter((style) => layers?.[style.categorie]);

  const hasContent = activeImmo.length > 0 || activeTransport.length > 0 || activeCavaliers.length > 0 || Boolean(focus);
  if (!hasContent) return null;

  return (
    <div
      className="absolute top-4 left-4 z-[500] bg-slate-950/90 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl text-xs"
      style={{ maxWidth: 190 }}
    >
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        aria-expanded={!collapsed}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-[9px] uppercase tracking-widest font-bold text-slate-400 hover:text-slate-200 transition-colors"
      >
        Légende
        <ChevronIcon collapsed={collapsed} />
      </button>

      {!collapsed && (
        <div className="px-3 pb-3 space-y-2.5">
          {activeImmo.length > 0 && (
            <div>
              <SectionTitle>Annonces</SectionTitle>
              <div className="flex items-center gap-1.5">
                <span className="shrink-0 w-2.5 h-2.5 rounded-full" style={{ background: ANNONCES_COLOR }} aria-hidden="true" />
                <span style={{ color: ANNONCES_COLOR }}>
                  {activeImmo.map((layer) => IMMO_SHORT_LABELS[layer.key] || layer.label).join(' · ')}
                </span>
              </div>
            </div>
          )}

          {activeTransport.length > 0 && (
            <div>
              <SectionTitle>Métro</SectionTitle>
              <ul className="space-y-1">
                {activeTransport.map((layer) => (
                  <li key={layer.key} className="flex items-center gap-1.5">
                    <span className="shrink-0 w-2.5 h-2.5 rounded-full" style={{ background: layer.uiColor }} aria-hidden="true" />
                    <span className="text-slate-200">{layer.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {activeCavaliers.length > 0 && (
            <div>
              <SectionTitle>Cavaliers</SectionTitle>
              <ul className="space-y-1">
                {activeCavaliers.map((style) => (
                  <li key={style.categorie} className="flex items-center gap-1.5">
                    <CavalierShapeIcon shape={style.shape} color={style.color} />
                    <span style={{ color: style.color }}>{style.categorie}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {focus && (
            <div>
              <SectionTitle>Rayon</SectionTitle>
              <p className="text-slate-400">{focus.radiusM} m</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
