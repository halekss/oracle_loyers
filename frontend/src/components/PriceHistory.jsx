import { useId, useState } from "react";

// ORA-72/ORA-182/ORA-199 : évolution du prix moyen/m² par quartier, en
// courbe (remplace l'ancien tableau) — un point par date de scan distincte
// trouvée dans master + archive par défaut (plus dense, api.getQuartierHistorique),
// ou par snapshot périodique (backend/data/snapshots/) si l'appelant passe
// `source: 'snapshots'` — ce composant affiche `historique`/`status` tels
// quels, sans connaître la source. Les points sont déjà agrégés par jour et
// débarrassés des annonces suspectes côté backend (ORA-195/ORA-199,
// services/price_history.py) : ce composant ne fait que les tracer.
//
// Statuts distincts (ORA-199) :
// - `status` absent : rien n'a encore été scanné -> rien.
// - "insufficient_history" (backend : moins de 2 dates au total, tous
//   quartiers confondus) : message honnête du backend (ORA-129, cadence de
//   mise à jour), jamais une fausse tendance.
// - "ok" + historique vide : ce quartier précis n'a jamais eu de données
//   exploitables -> bloc masqué (rien à montrer, ce n'est pas "insuffisant").
// - "ok" + un seul point : la valeur seule + note honnête (pas de tendance
//   traçable avec un point).
// - "ok" + 2+ points : la courbe.
export default function PriceHistory({ status, message, historique }) {
  if (!status) return null;

  if (status === "insufficient_history") {
    return (
      <div className="print:hidden">
        <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-1.5">
          Évolution du prix moyen/m²
        </p>
        <p className="text-[11px] text-slate-500 italic">{message}</p>
      </div>
    );
  }

  if (!historique || historique.length === 0) return null;

  if (historique.length === 1) {
    const [point] = historique;
    return (
      <div className="print:hidden">
        <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-1.5">
          Évolution du prix moyen/m²
        </p>
        <p className="text-lg font-bold text-yellow-400">{Math.round(point.prix_m2_moyen)} €/m²</p>
        <p className="text-[11px] text-slate-500 italic mt-1">
          Pas encore assez d'historique pour une tendance ({new Date(point.date).toLocaleDateString('fr-FR')}, {point.count} bien{point.count > 1 ? 's' : ''}).
        </p>
      </div>
    );
  }

  return <PriceHistoryChart historique={historique} />;
}

const CHART_WIDTH = 320;
const CHART_HEIGHT = 120;
const PADDING = { top: 12, right: 8, bottom: 20, left: 8 };
const GRID_LINES = 3;

function formatDateShort(dateStr) {
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' });
}

function PriceHistoryChart({ historique }) {
  const [activeIndex, setActiveIndex] = useState(null);
  const titleId = useId();

  const values = historique.map((p) => p.prix_m2_moyen);
  const min = Math.min(...values);
  const max = Math.max(...values);
  // Un plateau parfait (min===max) écraserait la courbe à une seule ligne :
  // une marge artificielle de ±1 garde une échelle Y exploitable.
  const yMin = min === max ? min - 1 : min;
  const yMax = min === max ? max + 1 : max;

  const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;

  const xFor = (i) => PADDING.left + (i / (historique.length - 1)) * innerWidth;
  const yFor = (value) => PADDING.top + (1 - (value - yMin) / (yMax - yMin)) * innerHeight;

  const linePath = historique
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i).toFixed(1)} ${yFor(p.prix_m2_moyen).toFixed(1)}`)
    .join(' ');

  const first = historique[0];
  const last = historique[historique.length - 1];
  const trend = last.prix_m2_moyen > first.prix_m2_moyen ? 'en hausse' : last.prix_m2_moyen < first.prix_m2_moyen ? 'en baisse' : 'stable';
  const ariaLabel =
    `Évolution du prix moyen au m², ${trend} : de ${Math.round(first.prix_m2_moyen)} €/m² le ${formatDateShort(first.date)} ` +
    `à ${Math.round(last.prix_m2_moyen)} €/m² le ${formatDateShort(last.date)}, sur ${historique.length} points de mesure.`;

  const gridValues = Array.from({ length: GRID_LINES }, (_, i) => yMin + ((yMax - yMin) * i) / (GRID_LINES - 1));

  const active = activeIndex != null ? historique[activeIndex] : null;

  return (
    <div className="print:hidden">
      <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-1.5">
        Évolution du prix moyen/m²
      </p>
      <div className="relative">
        <svg
          role="img"
          aria-label={ariaLabel}
          aria-labelledby={titleId}
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="w-full h-auto"
          onMouseLeave={() => setActiveIndex(null)}
        >
          <title id={titleId}>{ariaLabel}</title>
          {gridValues.map((value) => (
            <line
              key={value}
              x1={PADDING.left}
              x2={CHART_WIDTH - PADDING.right}
              y1={yFor(value)}
              y2={yFor(value)}
              stroke="#1C2440"
              strokeWidth={1}
            />
          ))}
          <path d={linePath} fill="none" stroke="#A78BFA" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          {activeIndex != null && (
            <line
              x1={xFor(activeIndex)}
              x2={xFor(activeIndex)}
              y1={PADDING.top}
              y2={CHART_HEIGHT - PADDING.bottom}
              stroke="#3A4570"
              strokeWidth={1}
              strokeDasharray="2,2"
            />
          )}
          {historique.map((p, i) => {
            const isLast = i === historique.length - 1;
            const isActive = i === activeIndex;
            return (
              <g key={p.date}>
                <circle
                  cx={xFor(i)}
                  cy={yFor(p.prix_m2_moyen)}
                  r={isLast ? 4 : isActive ? 3.5 : 2.5}
                  fill={isLast ? '#FACC15' : '#A78BFA'}
                />
                {/* Cible de survol agrandie (≥16px), invisible — le marqueur
                    visuel reste petit (mark spec) sans réduire la zone cliquable. */}
                <circle
                  data-testid="price-history-point"
                  cx={xFor(i)}
                  cy={yFor(p.prix_m2_moyen)}
                  r={8}
                  fill="transparent"
                  onMouseEnter={() => setActiveIndex(i)}
                  onFocus={() => setActiveIndex(i)}
                  tabIndex={0}
                  role="button"
                  aria-label={`${formatDateShort(p.date)} : ${Math.round(p.prix_m2_moyen)} €/m², ${p.count} bien${p.count > 1 ? 's' : ''}`}
                />
              </g>
            );
          })}
        </svg>
        {active && (
          <div
            role="tooltip"
            className="absolute pointer-events-none text-[10px] rounded-lg border px-2 py-1 shadow-lg whitespace-nowrap"
            style={{
              background: '#0E1428',
              borderColor: '#3A4570',
              color: '#E2E8F0',
              left: `${(xFor(activeIndex) / CHART_WIDTH) * 100}%`,
              top: `${(yFor(active.prix_m2_moyen) / CHART_HEIGHT) * 100}%`,
              transform: 'translate(-50%, -130%)',
            }}
          >
            <span className="font-bold" style={{ color: '#FACC15' }}>{Math.round(active.prix_m2_moyen)} €/m²</span>
            {' · '}{new Date(active.date).toLocaleDateString('fr-FR')}
            {' · '}{active.count} bien{active.count > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* ORA-199 : mêmes valeurs pour les lecteurs d'écran, masquées visuellement. */}
      <table className="sr-only">
        <caption>Évolution du prix moyen au m² par date</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Prix/m²</th>
            <th scope="col">Biens</th>
          </tr>
        </thead>
        <tbody>
          {historique.map((point) => (
            <tr key={point.date}>
              <td>{new Date(point.date).toLocaleDateString('fr-FR')}</td>
              <td>{Math.round(point.prix_m2_moyen)} €</td>
              <td>{point.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
