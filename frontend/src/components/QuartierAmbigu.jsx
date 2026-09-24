// ORA-176 : "Quel quartier ?" (maquette 08) — quand /api/quartier-stats
// renvoie `ambiguous: true` (plusieurs quartiers correspondent d'assez près
// à la saisie, ORA-111), l'Oracle demande explicitement plutôt que de
// deviner silencieusement (jamais de choix implicite).
function formatEuros(value) {
  if (value == null) return null;
  return `${value.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} €/m²`;
}

// `ambiguous` : { query, suggestions } (suggestions = noms de quartiers,
// /api/quartier-stats). `quartierOptions` (services/quartierStats.js) sert
// uniquement à afficher le compte/€m² de chaque suggestion — absent ou sans
// correspondance, le bouton reste utilisable (juste sans ces stats).
export default function QuartierAmbigu({ ambiguous, quartierOptions, onSelect }) {
  if (!ambiguous?.suggestions?.length) return null;

  const statsByQuartier = new Map((quartierOptions || []).map((o) => [o.quartier, o]));

  return (
    <div className="p-4 md:p-5 space-y-3">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400">Recherche</p>
        <h2 className="text-xl font-black text-white mt-0.5">Quel quartier ?</h2>
      </div>

      <div className="bg-amber-900/20 border border-amber-700/40 rounded-xl p-3">
        <p className="text-[11px] text-amber-300">
          <span className="font-bold">« {ambiguous.query} »</span> : {ambiguous.suggestions.length} quartiers possibles
        </p>
        <p className="mt-1 text-[10px] text-slate-400">
          L'Oracle préfère demander plutôt que deviner.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {ambiguous.suggestions.map((name) => {
          const stats = statsByQuartier.get(name);
          return (
            <button
              key={name}
              type="button"
              onClick={() => onSelect(name)}
              className="text-left bg-ink-900 border border-ink-700 hover:border-violet-500 rounded-xl p-3 transition-colors"
            >
              <p className="text-sm font-bold text-white">{name}</p>
              {stats && (
                <p className="mt-1 text-[10px] text-slate-500">
                  {stats.count} annonce{stats.count > 1 ? 's' : ''}
                  {formatEuros(stats.prixM2Median) ? ` · ${formatEuros(stats.prixM2Median)}` : ''}
                </p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
