// ORA-170 : panneau "Le marché en un coup d'œil" — état par défaut de la
// colonne Oracle (aucun quartier scanné), maquette 01 de l'epic 169.
const numberFmt = new Intl.NumberFormat('fr-FR');

function formatEuros(value, digits = 0) {
  if (value === null || value === undefined) return '—';
  return `${value.toLocaleString('fr-FR', { minimumFractionDigits: digits, maximumFractionDigits: digits })} €`;
}

export default function HomeOverview({ stats, ville, onOpenChat }) {
  const villeLabel = ville === 'lille' ? 'LILLE' : 'LYON';
  const districtUnit = stats.districtLabel === 'PAR ARRONDISSEMENT' ? 'ARRONDISSEMENTS' : 'QUARTIERS';
  const maxPrixM2 = Math.max(1, ...stats.districts.map((d) => d.prixM2Median));

  return (
    <div className="p-4 md:p-5 space-y-4">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400">
          {villeLabel} · {stats.districts.length} {districtUnit}
        </p>
        <h2 className="text-xl font-black text-white mt-0.5">Le marché en un coup d'œil</h2>
      </div>

      {/* Stats clés */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Loyer médian</p>
          <p className="text-lg font-black text-white">{formatEuros(stats.loyerMedian)}</p>
        </div>
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">€/m² médian</p>
          <p className="text-lg font-black text-yellow-400">{formatEuros(stats.prixM2Median, 1)}</p>
        </div>
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Annonces</p>
          <p className="text-lg font-black text-white">{numberFmt.format(stats.annoncesCount)}</p>
        </div>
      </div>

      {/* Barres par arrondissement/quartier */}
      {stats.districts.length > 0 && (
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">
              €/m² médian {stats.districtLabel.toLowerCase()}
            </p>
            <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Annonces</p>
          </div>
          <div className="space-y-1.5">
            {stats.districts.map((d) => (
              <div key={d.label} className="flex items-center gap-2">
                <span className="w-20 shrink-0 text-[11px] font-bold text-slate-300 truncate" title={d.label}>
                  {d.label}
                </span>
                <div className="flex-1 h-4 bg-ink-800 rounded overflow-hidden">
                  <div
                    className="h-full bg-violet-600 rounded"
                    style={{ width: `${Math.max(6, (d.prixM2Median / maxPrixM2) * 100)}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right text-[11px] font-bold text-yellow-400">
                  {formatEuros(d.prixM2Median, 1)}
                </span>
                <span className="w-8 shrink-0 text-right text-[10px] text-slate-500">{d.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {stats.excludedCount > 0 && (
        <p className="text-[10px] text-slate-500 flex items-start gap-1.5">
          <span className="shrink-0">ⓘ</span>
          <span>
            {numberFmt.format(stats.excludedCount)} annonce{stats.excludedCount > 1 ? 's' : ''} sans quartier
            précis exclue{stats.excludedCount > 1 ? 's' : ''} des cartes et des médianes.
          </span>
        </p>
      )}

      {/* Extrêmes */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-green-400 font-bold mb-1.5">Les plus abordables</p>
          <div className="space-y-1">
            {stats.quartiersAbordables.map((q) => (
              <div key={q.label} className="flex items-center justify-between text-[11px]">
                <span className="text-slate-300 truncate">{q.label}</span>
                <span className="text-yellow-400 font-bold shrink-0">{formatEuros(q.prixM2Median, 1)}/m²</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-ink-900 border border-ink-700 rounded-xl p-3">
          <p className="text-[9px] uppercase tracking-widest text-red-400 font-bold mb-1.5">Les plus chers</p>
          <div className="space-y-1">
            {stats.quartiersChers.map((q) => (
              <div key={q.label} className="flex items-center justify-between text-[11px]">
                <span className="text-slate-300 truncate">{q.label}</span>
                <span className="text-yellow-400 font-bold shrink-0">{formatEuros(q.prixM2Median, 1)}/m²</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {onOpenChat && (
        <button
          type="button"
          onClick={onOpenChat}
          className="w-full flex items-center justify-between gap-2 bg-ink-900 border border-ink-700 hover:border-violet-500 rounded-xl px-3 py-2.5 text-left transition-colors"
        >
          <span className="text-[11px] text-slate-400">
            Demande à Immotep : <span className="text-slate-300">un T2 sous 1 000 € près d'un métro ?</span>
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400 shrink-0">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      )}
    </div>
  );
}
