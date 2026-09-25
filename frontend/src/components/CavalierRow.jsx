import { cavalierMeta } from '../services/cavaliersDisplay';
import CavalierShapeIcon from './CavalierShapeIcon';
import LayerSwitch from './LayerSwitch';

function Chevron({ open }) {
  return (
    <svg
      width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      className={`shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
      style={{ color: '#8B93A7' }}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

// Une ligne "cavalier" de la vue Calques (maquette vue-calques.png) :
// forme + nom colorés, méta (compte · distance), chevron pour déplier le
// détail par sous-catégorie, interrupteur de visibilité sur la carte.
//
// `detail` (entrée de `cavaliers_detail`, /api/quartier-stats) est optionnel
// : sans scan encore lancé, la ligne retombe sur un mode simplifié (forme +
// nom + interrupteur seuls, pas de méta ni de chevron) — l'interrupteur
// reste utilisable même dans cet état (ORA-178, état vide de la vue Calques).
export default function CavalierRow({
  categorie, color, shape, detail, phrase, isLoading,
  isVisible, onToggleVisibility, isExpanded, onToggleExpand,
}) {
  const meta = !isLoading && detail ? cavalierMeta(detail) : null;
  const metaText = meta
    ? (meta.count > 0
      ? `${meta.count} lieu${meta.count > 1 ? 'x' : ''}${meta.distM != null ? ` · dès ${meta.distM} m` : ''}`
      : (meta.distM != null ? `0 · le 1er à ${meta.distM} m` : '0 lieu'))
    : null;
  const contentId = `cavalier-${categorie}`;
  const maxCount = detail ? Math.max(1, ...detail.items.map((item) => item.count)) : 1;

  return (
    <div className="border-b" style={{ borderColor: '#1C2440' }}>
      <div className="flex items-center gap-2 min-h-[38px] py-1.5">
        {detail ? (
          <button
            type="button"
            aria-expanded={isExpanded}
            aria-controls={contentId}
            onClick={onToggleExpand}
            className="flex-1 flex items-center gap-2 min-w-0 text-left rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#A78BFA]"
          >
            <CavalierShapeIcon shape={shape} color={color} />
            <span className="font-bold text-sm truncate" style={{ color }}>{categorie}</span>
            {isLoading ? (
              <span
                data-testid="cavalier-meta-skeleton"
                aria-hidden="true"
                className="ml-auto shrink-0 w-16 h-3 rounded animate-pulse"
                style={{ background: '#232B45' }}
              />
            ) : metaText && (
              <span className="text-[11px] ml-auto shrink-0 whitespace-nowrap" style={{ color: '#8B93A7' }}>
                {metaText}
              </span>
            )}
            <Chevron open={isExpanded} />
          </button>
        ) : (
          <div className="flex-1 flex items-center gap-2 min-w-0">
            <CavalierShapeIcon shape={shape} color={color} />
            <span className="font-bold text-sm truncate" style={{ color }}>{categorie}</span>
          </div>
        )}
        <LayerSwitch checked={isVisible} onChange={onToggleVisibility} label={categorie} />
      </div>

      {detail && isExpanded && !isLoading && (
        <div id={contentId} className="pb-3 pl-1">
          {detail.items.length > 0 && (
            <div className="space-y-1 mb-2">
              {detail.items.map((item) => (
                <div key={item.poi} className="flex items-center gap-2 text-[11px]">
                  <span className="w-20 shrink-0 truncate" style={{ color: '#8B93A7' }} title={item.poi}>
                    {item.poi}
                  </span>
                  <div className="flex-1 h-1.5 rounded overflow-hidden" style={{ background: '#1C2440' }}>
                    <div
                      className="h-full rounded"
                      style={{ width: `${Math.max(8, (item.count / maxCount) * 100)}%`, background: color }}
                    />
                  </div>
                  <span className="w-6 shrink-0 text-right font-bold" style={{ color: '#F1F5F9' }}>{item.count}</span>
                  {item.dist_m != null && (
                    <span className="w-16 shrink-0 text-right whitespace-nowrap" style={{ color: '#8B93A7' }}>
                      dès {item.dist_m} m
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
          {phrase && (
            <p className="text-[11px] rounded-lg px-3 py-2" style={{ background: `${color}22`, color: '#F1F5F9' }}>
              {phrase}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
