import { useState } from 'react';

// ORA-170 : barre supérieure pleine largeur (maquette "carte sombre" 01-09,
// socle commun à tous les écrans de l'epic 169) — remplace l'ancien bloc
// recherche empilé dans la colonne Oracle par une topbar horizontale
// persistante au-dessus de la carte ET du panneau latéral.
//
// L'autocomplétion/désambiguïsation du champ quartier (maquette 08) est hors
// périmètre ici : ce champ reste un simple texte libre, cf. ORA-176.
const TYPE_FILTERS = ['Tout', 'T1', 'T2', 'T3', 'T4+'];
const MIN_QUARTIER_LENGTH = 2;

export default function Topbar({ ville, onVilleChange, onScan, isLoading, dataAsOf }) {
  const [quartier, setQuartier] = useState('');
  const [surface, setSurface] = useState('');
  const [typeFilter, setTypeFilter] = useState('Tout');

  const canScan = quartier.trim().length >= MIN_QUARTIER_LENGTH;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (canScan) onScan(quartier, typeFilter, surface);
  };

  const handleTypeClick = (filterId) => {
    setTypeFilter(filterId);
    if (canScan) onScan(quartier, filterId, surface);
  };

  return (
    <header className="shrink-0 bg-ink-950 border-b border-ink-800 px-3 md:px-4 py-2.5 flex flex-wrap items-center gap-2 md:gap-3">
      <span className="font-display font-extrabold text-sm md:text-base tracking-tight text-white shrink-0">
        ORACLE <span className="text-violet-500">DES LOYERS</span>
      </span>

      <div className="flex gap-1.5 shrink-0">
        {['lyon', 'lille'].map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => onVilleChange(v)}
            className={`px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-colors ${
              ville === v
                ? 'bg-violet-600 text-white'
                : 'bg-ink-900 border border-ink-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2 flex-1 min-w-[180px]">
        <div className="relative flex-1 min-w-[140px]">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            value={quartier}
            onChange={(e) => setQuartier(e.target.value)}
            placeholder="Entrez un quartier (ex : Ainay)…"
            aria-label="Quartier à scanner"
            className="w-full bg-ink-900 border border-ink-700 text-slate-200 text-xs pl-8 pr-3 py-2 rounded-lg focus:outline-none focus:border-violet-500 placeholder-slate-500"
          />
        </div>

        <div className="hidden lg:flex gap-1.5 shrink-0">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => handleTypeClick(f)}
              className={`px-2.5 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-colors ${
                typeFilter === f
                  ? 'bg-violet-600 text-white'
                  : 'bg-ink-900 border border-ink-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <input
          type="number"
          min="1"
          value={surface}
          onChange={(e) => setSurface(e.target.value)}
          placeholder="Surface m²"
          aria-label="Surface en m² (pour l'estimation IA)"
          className="hidden md:block w-24 bg-ink-900 border border-ink-700 text-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:border-violet-500 placeholder-slate-500"
        />

        <button
          type="submit"
          disabled={isLoading || !canScan}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold rounded-lg uppercase text-[10px] tracking-widest transition-colors shrink-0"
        >
          {isLoading ? '…' : 'Scan'}
        </button>
      </form>

      {dataAsOf && (
        <div className="hidden xl:flex items-center gap-1.5 shrink-0 px-2.5 py-1.5 rounded-lg bg-ink-900 border border-ink-700 text-[10px] text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
          <span className="uppercase tracking-widest font-bold text-slate-500">Données au</span>
          <span className="text-slate-300 font-semibold">{dataAsOf}</span>
        </div>
      )}
    </header>
  );
}
