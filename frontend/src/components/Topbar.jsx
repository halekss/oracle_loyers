import { useState, useRef, useId } from 'react';
import { normalizeText } from '../services/normalizeText';
import { loadRecentSearches, pushRecentSearch } from '../services/recentSearchesStorage';

// ORA-170 : barre supérieure pleine largeur (maquette "carte sombre" 01-09,
// socle commun à tous les écrans de l'epic 169) — remplace l'ancien bloc
// recherche empilé dans la colonne Oracle par une topbar horizontale
// persistante au-dessus de la carte ET du panneau latéral.
const TYPE_FILTERS = ['Tout', 'T1', 'T2', 'T3', 'T4+'];
const MIN_QUARTIER_LENGTH = 2;
const MAX_PALETTE_RESULTS = 8;

function formatEuros(value) {
  if (value == null) return null;
  return `${value.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} €/m²`;
}

// Segmente `label` en { before, match, after } autour de la première
// occurrence (insensible accents/casse) de `query`, pour mettre `match` en
// gras dans la palette (ORA-176, maquette 08 : "Croix-Rousse Plateau" avec
// "Croix" en évidence). `match` vide si `query` ne matche pas `label`.
function splitAtMatch(label, query) {
  const normLabel = normalizeText(label);
  const normQuery = normalizeText(query);
  const index = normQuery ? normLabel.indexOf(normQuery) : -1;
  if (index === -1) return { before: label, match: '', after: '' };
  return {
    before: label.slice(0, index),
    match: label.slice(index, index + query.length),
    after: label.slice(index + query.length),
  };
}

// `quartierOptions` (ORA-176, optionnel) : [{ quartier, count, prixM2Median }]
// (services/quartierStats.js) — palette + historique désactivés (champ texte
// libre classique) si absent, pour ne pas casser un appelant qui ne les
// fournit pas encore (tests existants, ex.).
export default function Topbar({ ville, onVilleChange, onScan, isLoading, dataAsOf, quartierOptions }) {
  const [quartier, setQuartier] = useState('');
  const [surface, setSurface] = useState('');
  const [typeFilter, setTypeFilter] = useState('Tout');
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState(() => loadRecentSearches());
  const inputRef = useRef(null);
  const listboxId = useId();

  const canScan = quartier.trim().length >= MIN_QUARTIER_LENGTH;
  const hasPalette = Array.isArray(quartierOptions);

  // ORA-176 : quartiers filtrés (recherche tolérante accents/casse, via la
  // normalisation partagée) quand une saisie existe, sinon l'historique
  // récent — jamais les deux en même temps (la maquette 08 montre l'un ou
  // l'autre selon que le champ est vide).
  const showingRecent = hasPalette && quartier.trim().length === 0;
  const filteredOptions = showingRecent
    ? []
    : (quartierOptions || [])
        .filter((opt) => normalizeText(opt.quartier).includes(normalizeText(quartier)))
        .slice(0, MAX_PALETTE_RESULTS);
  const paletteItems = showingRecent
    ? recentSearches.map((s) => ({ quartier: s.quartier, recent: s }))
    : filteredOptions.map((opt) => ({ quartier: opt.quartier, option: opt }));

  const runScan = (targetQuartier, targetType, targetSurface) => {
    onScan(targetQuartier, targetType, targetSurface);
    const next = pushRecentSearch({
      quartier: targetQuartier,
      typeLocal: targetType !== 'Tout' ? targetType : undefined,
      surface: targetSurface || undefined,
      ville,
    });
    setRecentSearches(next);
  };

  const closePalette = () => {
    setIsPaletteOpen(false);
    setActiveIndex(-1);
  };

  const selectItem = (item) => {
    setQuartier(item.quartier);
    closePalette();
    if (item.quartier.trim().length >= MIN_QUARTIER_LENGTH) {
      runScan(item.quartier, typeFilter, surface);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    closePalette();
    if (canScan) runScan(quartier, typeFilter, surface);
  };

  const handleTypeClick = (filterId) => {
    setTypeFilter(filterId);
    if (canScan) runScan(quartier, filterId, surface);
  };

  const handleInputKeyDown = (e) => {
    if (!hasPalette) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setIsPaletteOpen(true);
      setActiveIndex((i) => (paletteItems.length === 0 ? -1 : Math.min(i + 1, paletteItems.length - 1)));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setIsPaletteOpen(true);
      setActiveIndex((i) => (paletteItems.length === 0 ? -1 : Math.max(i - 1, 0)));
    } else if (e.key === 'Enter') {
      if (isPaletteOpen && activeIndex >= 0 && paletteItems[activeIndex]) {
        e.preventDefault();
        selectItem(paletteItems[activeIndex]);
      }
      // Sinon : laisse le <form onSubmit> gérer (Entrée depuis un champ texte
      // hors palette ouverte = validation classique du scan).
    } else if (e.key === 'Escape') {
      if (isPaletteOpen) {
        e.preventDefault();
        closePalette();
      }
    }
  };

  const activeOptionId = activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined;

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
            ref={inputRef}
            id="topbar-quartier-input"
            type="text"
            value={quartier}
            onChange={(e) => {
              setQuartier(e.target.value);
              setIsPaletteOpen(true);
              setActiveIndex(-1);
            }}
            onFocus={() => hasPalette && setIsPaletteOpen(true)}
            onBlur={closePalette}
            onKeyDown={handleInputKeyDown}
            placeholder="Entrez un quartier (ex : Ainay)…"
            aria-label="Quartier à scanner"
            {...(hasPalette
              ? {
                  role: 'combobox',
                  'aria-expanded': isPaletteOpen,
                  'aria-controls': listboxId,
                  'aria-autocomplete': 'list',
                  'aria-activedescendant': activeOptionId,
                }
              : {})}
            className="w-full bg-ink-900 border border-ink-700 text-slate-200 text-xs pl-8 pr-3 py-2 rounded-lg focus:outline-none focus:border-violet-500 placeholder-slate-500"
          />

          {/* ORA-176 : palette (maquette 08) — quartiers filtrés ou
              recherches récentes, navigation 100% clavier. */}
          {hasPalette && isPaletteOpen && (paletteItems.length > 0 || showingRecent) && (
            <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-ink-900 border border-ink-700 rounded-lg shadow-2xl overflow-hidden">
              <p className="px-3 pt-2 pb-1 text-[9px] uppercase tracking-widest font-bold text-slate-500">
                {showingRecent ? 'Recherches récentes' : 'Quartiers'}
              </p>
              {paletteItems.length === 0 ? (
                <p className="px-3 pb-2 text-[11px] text-slate-500">Aucun quartier ne correspond.</p>
              ) : (
                <ul id={listboxId} role="listbox" aria-label="Quartiers" className="max-h-64 overflow-y-auto">
                  {paletteItems.map((item, i) => {
                    const { before, match, after } = showingRecent
                      ? { before: item.quartier, match: '', after: '' }
                      : splitAtMatch(item.quartier, quartier);
                    return (
                      <li key={`${item.quartier}-${i}`} role="presentation">
                        <button
                          type="button"
                          id={`${listboxId}-option-${i}`}
                          role="option"
                          aria-selected={i === activeIndex}
                          onMouseDown={(e) => e.preventDefault()}
                          onClick={() => selectItem(item)}
                          onMouseEnter={() => setActiveIndex(i)}
                          className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 text-left text-xs transition-colors ${
                            i === activeIndex ? 'bg-violet-900/40 text-white' : 'text-slate-300 hover:bg-ink-800'
                          }`}
                        >
                          <span className="truncate">
                            {before}
                            {match && <span className="font-bold text-violet-300">{match}</span>}
                            {after}
                            {showingRecent && item.recent?.typeLocal && (
                              <span className="text-slate-500"> · {item.recent.typeLocal}</span>
                            )}
                            {showingRecent && item.recent?.surface && (
                              <span className="text-slate-500"> · {item.recent.surface} m²</span>
                            )}
                          </span>
                          {!showingRecent && (
                            <span className="shrink-0 text-[10px] text-slate-500">
                              {item.option.count} annonce{item.option.count > 1 ? 's' : ''}
                              {formatEuros(item.option.prixM2Median) ? ` · ${formatEuros(item.option.prixM2Median)}` : ''}
                            </span>
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
              <p className="px-3 py-1.5 border-t border-ink-800 text-[9px] text-slate-600">
                ↑↓ naviguer · Entrée valider · Échap fermer
              </p>
            </div>
          )}
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
