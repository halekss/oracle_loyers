// ORA-172 : détail des 4 Cavaliers (maquette 04) — remplace l'ancien
// affichage plat (une phrase par catégorie) par 4 cartes avec le détail par
// sous-type (compte + distance minimale), alimentées par
// `cavaliers_detail` (/api/quartier-stats, services/cavaliers_factors.py).
const CATEGORY_STYLES = {
  Vice: { text: 'text-red-400', bar: 'bg-red-500' },
  Gentrification: { text: 'text-violet-400', bar: 'bg-violet-500' },
  Nuisance: { text: 'text-orange-400', bar: 'bg-orange-500' },
  Superstition: { text: 'text-slate-400', bar: 'bg-slate-500' },
};

export default function CavaliersDetail({ detail, quartier }) {
  if (!detail || detail.length === 0) return null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest">
          {quartier ? `${quartier} · ` : ''}Les 4 Cavaliers
        </p>
        <p className="text-[9px] uppercase text-slate-600 font-bold tracking-widest">rayon 500 m</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {detail.map((cat) => {
          const style = CATEGORY_STYLES[cat.categorie] || CATEGORY_STYLES.Superstition;
          const maxCount = Math.max(1, ...cat.items.map((i) => i.count));
          return (
            <div key={cat.categorie} className="bg-slate-900/50 rounded-lg px-2.5 py-2 border border-slate-800">
              <div className="flex items-baseline justify-between mb-1">
                <span className={`text-[11px] font-bold ${style.text}`}>{cat.categorie}</span>
                <span className="text-[10px] text-slate-500">
                  {cat.total} lieu{cat.total > 1 ? 'x' : ''}
                </span>
              </div>
              {cat.items.length > 0 ? (
                <div className="space-y-1">
                  {cat.items.map((item) => (
                    <div key={item.poi} className="flex items-center gap-1.5 text-[10px]">
                      <span className="w-16 shrink-0 text-slate-400 truncate" title={item.poi}>{item.poi}</span>
                      <div className="flex-1 h-1.5 bg-slate-800 rounded overflow-hidden">
                        <div
                          className={`h-full rounded ${style.bar}`}
                          style={{ width: `${Math.max(8, (item.count / maxCount) * 100)}%` }}
                        />
                      </div>
                      <span className="w-5 shrink-0 text-right font-bold text-slate-300">{item.count}</span>
                      {item.dist_m != null && (
                        <span className="w-16 shrink-0 text-right text-slate-500">dès {item.dist_m} m</span>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-slate-500">{cat.empty_message}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
