import { useState, useRef, useId } from 'react';
import { normalizeText } from '../services/normalizeText';
import { loadRecentSearches, pushRecentSearch } from '../services/recentSearchesStorage';

// ORA-179 : formulaire de recherche (maquette nav-b3v2-recherche), extrait
// de l'ancienne Topbar (ORA-170/176) — seul point d'entrée pour lancer un
// scan désormais (la topbar ne garde que le logo et le badge "Données au").
// Vit dans la vue "Recherche" du rail (desktop) et dans la colonne Oracle
// mobile (avant un premier scan) : mêmes props, aucune logique dupliquée.
const TYPE_FILTERS = ['Tout', 'T1', 'T2', 'T3', 'T4+'];
const MIN_QUARTIER_LENGTH = 2;
const MAX_PALETTE_RESULTS = 8;
const MAX_RECENT_DISPLAYED = 3;

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

// `quartierOptions` (ORA-176, optionnel) : [{ quartier, count, prixM2Median,
// arrondissement }] (services/quartierStats.js) — palette désactivée (champ
// texte libre classique) si absent, pour ne pas casser un appelant qui ne le
// fournit pas encore (tests).
// `initialQuartier`/`initialTypeLocal`/`initialSurface` (optionnels, ORA-179) :
// pré-remplissage (dernier scan, via le lien "Modifier" des vues Scan/
// Estimation) — ne s'appliquent qu'au montage (composant remonté à chaque
// fois que la vue "Recherche" redevient active, cf. App.jsx).
// `autoFocus` (optionnel, défaut true) : focus le champ Quartier au montage
// — satisfait à la fois l'ouverture normale de la vue et le raccourci `/`.
export default function SearchForm({
  ville, onVilleChange, onScan, isLoading, quartierOptions,
  initialQuartier = '', initialTypeLocal = 'Tout', initialSurface = '',
  autoFocus = true,
}) {
  const [quartier, setQuartier] = useState(initialQuartier);
  const [surface, setSurface] = useState(initialSurface ? String(initialSurface) : '');
  const [typeFilter, setTypeFilter] = useState(initialTypeLocal || 'Tout');
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recentSearches, setRecentSearches] = useState(() => loadRecentSearches());
  const inputRef = useRef(null);
  const listboxId = useId();

  const canScan = quartier.trim().length >= MIN_QUARTIER_LENGTH;
  const hasPalette = Array.isArray(quartierOptions);

  // ORA-176 : quartiers filtrés (recherche tolérante accents/casse, via la
  // normalisation partagée) quand une saisie existe, sinon l'historique
  // récent — jamais les deux en même temps (la maquette montre l'un ou
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

  const handleSelectRecent = (entry) => {
    setQuartier(entry.quartier);
    setTypeFilter(entry.typeLocal || 'Tout');
    setSurface(entry.surface ? String(entry.surface) : '');
    runScan(entry.quartier, entry.typeLocal || 'Tout', entry.surface || '');
  };

  const activeOptionId = activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined;

  return (
    <div className="p-4 md:p-5 space-y-5">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-violet-400">Nouvelle recherche</p>
        <h2 className="text-xl font-black text-white mt-0.5">Que cherches-tu ?</h2>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Ville — contrôle segmenté */}
        <div>
          <span id="searchform-ville-label" className="block text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">
            Ville
          </span>
          <div role="group" aria-label="Ville" className="grid grid-cols-2 gap-2">
            {['lyon', 'lille'].map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={ville === v}
                onClick={() => onVilleChange(v)}
                className={`min-h-[44px] rounded-lg text-xs font-bold uppercase tracking-wide transition-colors ${
                  ville === v
                    ? 'bg-violet-600 text-white shadow-[0_0_18px_rgba(124,58,237,.5)]'
                    : 'bg-ink-900 border border-ink-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        {/* Quartier — combobox avec suggestions */}
        <div className="relative">
          <label htmlFor="searchform-quartier" className="block text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">
            Quartier
          </label>
          <div className="relative">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input
              ref={inputRef}
              id="searchform-quartier"
              autoFocus={autoFocus}
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
              className="w-full min-h-[44px] bg-ink-900 border border-ink-700 text-slate-200 text-sm pl-9 pr-3 py-2.5 rounded-lg focus:outline-none focus:border-violet-500 placeholder-slate-500"
            />
          </div>

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
                          className={`w-full min-h-[44px] flex items-center justify-between gap-2 px-3 py-2 text-left text-xs transition-colors ${
                            i === activeIndex ? 'bg-violet-900/40 text-white' : 'text-slate-300 hover:bg-ink-800'
                          }`}
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-bold">
                              {before}
                              {match && <span className="font-bold text-violet-300">{match}</span>}
                              {after}
                            </span>
                            <span className="block truncate text-[10px] text-slate-500">
                              {showingRecent ? (
                                <>
                                  {item.recent?.typeLocal ? `${item.recent.typeLocal} · ` : ''}
                                  {item.recent?.surface ? `${item.recent.surface} m²` : ''}
                                </>
                              ) : (
                                <>
                                  {item.option.arrondissement ? `${item.option.arrondissement} · ` : ''}
                                  {item.option.count} annonce{item.option.count > 1 ? 's' : ''}
                                </>
                              )}
                            </span>
                          </span>
                          {!showingRecent && formatEuros(item.option.prixM2Median) && (
                            <span className="shrink-0 text-[11px] font-bold" style={{ color: '#FACC15' }}>
                              {formatEuros(item.option.prixM2Median)}
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

        {/* Type de bien — contrôle segmenté */}
        <div>
          <span id="searchform-type-label" className="block text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">
            Type de bien
          </span>
          <div role="group" aria-label="Type de bien" className="grid grid-cols-5 gap-1.5">
            {TYPE_FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                aria-pressed={typeFilter === f}
                onClick={() => handleTypeClick(f)}
                className={`min-h-[44px] rounded-lg text-[11px] font-bold uppercase tracking-wide transition-colors ${
                  typeFilter === f
                    ? 'bg-violet-600 text-white shadow-[0_0_18px_rgba(124,58,237,.5)]'
                    : 'bg-ink-900 border border-ink-700 text-slate-400 hover:text-slate-200'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Surface — optionnelle */}
        <div>
          <label htmlFor="searchform-surface" className="block text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">
            Surface <span className="normal-case text-slate-600 font-normal">· optionnel, active l'estimation du modèle</span>
          </label>
          <div className="relative">
            <input
              id="searchform-surface"
              type="number"
              min="1"
              value={surface}
              onChange={(e) => setSurface(e.target.value)}
              aria-label="Surface en m² (pour l'estimation IA)"
              className="w-full min-h-[44px] bg-ink-900 border border-ink-700 text-slate-200 text-sm px-3 py-2.5 rounded-lg focus:outline-none focus:border-violet-500 placeholder-slate-500"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-500 pointer-events-none">m²</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading || !canScan}
          className="w-full h-[52px] rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold uppercase text-sm tracking-widest transition-colors"
        >
          {isLoading ? '…' : 'Scan'}
        </button>
      </form>

      {recentSearches.length > 0 && (
        <div>
          <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">Recherches récentes</p>
          <ul className="space-y-1.5">
            {recentSearches.slice(0, MAX_RECENT_DISPLAYED).map((entry, i) => (
              <li key={`${entry.quartier}-${i}`}>
                <button
                  type="button"
                  onClick={() => handleSelectRecent(entry)}
                  className="w-full min-h-[44px] flex items-center justify-between gap-2 bg-ink-900 border border-ink-700 hover:border-violet-500 rounded-lg px-3 py-2 text-left transition-colors"
                >
                  <span className="text-xs text-slate-200 truncate">
                    {entry.quartier}{entry.typeLocal ? ` · ${entry.typeLocal}` : ''}{entry.surface ? ` · ${entry.surface} m²` : ''}
                  </span>
                  <span className="shrink-0 text-[9px] uppercase text-violet-400 font-bold">Scanner</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
