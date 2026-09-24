import { useRef } from 'react';
import { PANEL_VIEWS } from '../services/panelViews';

const ICON_PROPS = {
  width: 18, height: 18, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round',
};

const icons = {
  accueil: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10v9.5h13V10" />
      <path d="M10 19.5v-6h4v6" />
    </svg>
  ),
  scan: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <path d="M3 8V5a2 2 0 0 1 2-2h3" />
      <path d="M16 3h3a2 2 0 0 1 2 2v3" />
      <path d="M21 16v3a2 2 0 0 1-2 2h-3" />
      <path d="M8 21H5a2 2 0 0 1-2-2v-3" />
      <circle cx="12" cy="12" r="3.2" />
    </svg>
  ),
  estimation: () => (
    <svg {...ICON_PROPS} fill="currentColor" stroke="none" aria-hidden="true">
      <path d="M11 2l1.8 5.2L18 9l-5.2 1.8L11 16l-1.8-5.2L4 9l5.2-1.8L11 2z" />
      <path d="M19 13l.9 2.6L22.5 16.5l-2.6.9L19 20l-.9-2.6-2.6-.9 2.6-.9L19 13z" />
    </svg>
  ),
  calques: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <polygon points="12 3 21 8 12 13 3 8 12 3" />
      <polyline points="3 12 12 17 21 12" />
      <polyline points="3 16 12 21 21 16" />
    </svg>
  ),
  annonces: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  ),
  fiche: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="13" y2="17" />
    </svg>
  ),
  immotep: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  recherche: () => (
    <svg {...ICON_PROPS} aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
};

// ORA-178 : rail vertical "classeur" du panneau droit (maquette
// nav-b3-classeur) — la carte (colonne gauche) ne bouge jamais, seule cette
// navigation change quelle vue la feuille de contenu (PanelSheet) affiche.
// `annonceCount` (optionnel) : pastille jaune sur "Annonces" (nombre
// d'annonces du quartier scanné). `ficheDisabled` : "Fiche" reste dans
// l'ordre de tabulation (accessible, explicable) mais n'active rien tant
// qu'aucune annonce n'est sélectionnée — `aria-disabled`, pas `disabled`
// natif, pour rester découvrable au clavier plutôt que sauté silencieusement.
// `chatAvailable` (défaut true : Immotep n'a pas d'état hors-ligne dans cette
// app) : pastille verte sur "Immotep".
export default function PanelNav({ activeView, onChange, annonceCount, ficheDisabled = false, chatAvailable = true, sheetId }) {
  const buttonRefs = useRef([]);

  const handleKeyDown = (e, index) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    const delta = e.key === 'ArrowDown' ? 1 : -1;
    const nextIndex = (index + delta + PANEL_VIEWS.length) % PANEL_VIEWS.length;
    buttonRefs.current[nextIndex]?.focus();
  };

  return (
    <nav aria-label="Vues" className="w-[76px] shrink-0 flex flex-col items-stretch py-2 gap-0.5" style={{ background: '#0E1428' }}>
      {PANEL_VIEWS.map((view, index) => {
        const isActive = activeView === view.id;
        const isDisabled = view.id === 'fiche' && ficheDisabled;
        const Icon = icons[view.id];
        const showAnnoncesBadge = view.id === 'annonces' && annonceCount != null;
        const showChatDot = view.id === 'immotep' && chatAvailable;

        let ariaLabel = view.label;
        if (showAnnoncesBadge) {
          ariaLabel = `${view.label}, ${annonceCount} résultat${annonceCount > 1 ? 's' : ''}`;
        } else if (showChatDot) {
          ariaLabel = `${view.label}, chat disponible`;
        }

        return (
          <button
            key={view.id}
            ref={(el) => { buttonRefs.current[index] = el; }}
            type="button"
            aria-current={isActive ? 'page' : undefined}
            aria-disabled={isDisabled ? 'true' : undefined}
            aria-label={ariaLabel}
            aria-controls={sheetId}
            tabIndex={isActive ? 0 : -1}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onClick={() => { if (!isDisabled) onChange(view.id); }}
            className={`relative min-h-[58px] flex flex-col items-center justify-center gap-1 rounded-l-[14px] transition-colors focus-visible:outline-none focus-visible:ring-2 ${
              isDisabled ? 'cursor-not-allowed' : 'cursor-pointer'
            }`}
            style={{
              color: isActive ? '#C4B5FD' : isDisabled ? '#4B5266' : '#94A3B8',
              background: isActive ? '#151C33' : 'transparent',
              marginRight: isActive ? '-1px' : undefined,
              borderLeft: isActive ? '3px solid #7C3AED' : '3px solid transparent',
              boxShadow: isActive ? '0 0 18px rgba(124,58,237,.5)' : undefined,
              outlineColor: '#A78BFA',
            }}
          >
            <Icon />
            <span className="text-[10px] leading-none font-semibold">{view.label}</span>
            {showAnnoncesBadge && (
              <span
                aria-hidden="true"
                className="absolute top-1.5 right-2 min-w-[16px] h-4 px-1 rounded-full text-[9px] font-bold flex items-center justify-center"
                style={{ background: '#FACC15', color: '#1C1400' }}
              >
                {annonceCount}
              </span>
            )}
            {showChatDot && (
              <span
                aria-hidden="true"
                className="absolute top-2 right-3 w-2 h-2 rounded-full"
                style={{ background: '#22C55E', boxShadow: '0 0 6px #22C55E' }}
              />
            )}
          </button>
        );
      })}
    </nav>
  );
}
