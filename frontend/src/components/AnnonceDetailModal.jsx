import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useAnnonceDetail } from '../hooks/useAnnonceDetail';
import AnnonceDetailContent from './AnnonceDetailContent';

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Vue détail d'une annonce (ORA-131, refondue maquette 06 par ORA-174),
// consommant GET /api/annonces/:id enrichi (ORA-174 : coordonnées,
// quartier_prix_m2_moyen, cavaliers_detail — services/annonce_detail.py).
// Aucune photo/capture du site source affichée (ORA-94/ORA-133) —
// uniquement un pictogramme générique, jamais une image tierce (contrainte
// légale, LEGAL_DECISIONS.md). `annonceId` null : rien à afficher.
//
// ORA-178 : ce composant ne porte plus que le chrome de la modale (portail,
// fond, piège de focus, Échap) — le fetch/les actions viennent de
// `useAnnonceDetail` et le contenu de `AnnonceDetailContent`, partagés avec
// la vue "Fiche" du rail (rendue inline, sans ce chrome).
export default function AnnonceDetailModal({ annonceId, onClose }) {
  const dialogRef = useRef(null);
  const detail = useAnnonceDetail(annonceId);

  // ORA-174 : fermeture Échap + piège de focus (a11y d'une modale) — le
  // focus revient sur l'élément qui l'a ouverte à la fermeture, il ne doit
  // jamais s'échapper vers le reste de la page tant que la modale est ouverte.
  useEffect(() => {
    if (annonceId == null) return;

    const previouslyFocused = document.activeElement;
    const node = dialogRef.current;
    node?.focus();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !node) return;

      const focusable = Array.from(node.querySelectorAll(FOCUSABLE_SELECTOR));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [annonceId]);

  if (annonceId == null) return null;

  const { annonce } = detail;

  // ORA-174 (fix visuel) : rendu via portail dans document.body plutôt
  // qu'à sa place dans l'arbre React — une modale `fixed inset-0` imbriquée
  // sous un ancêtre `backdrop-blur` (colonne Oracle, App.jsx) reste piégée
  // dans son containing block (backdrop-filter en crée un pour les
  // descendants `position: fixed`) au lieu de couvrir tout l'écran.
  return createPortal(
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-ink-950/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Détail de l'annonce"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm bg-ink-900 border border-ink-700 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-4 py-3 bg-ink-950/80 border-b border-ink-700 sticky top-0 z-10">
          {annonce?.type_local && annonce?.quartier ? (
            <span className="text-[10px] font-black uppercase tracking-widest text-violet-400">
              {annonce.type_local} · {annonce.quartier}
            </span>
          ) : (
            <span className="text-xs font-black uppercase tracking-widest text-white">Détail de l'annonce</span>
          )}
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="text-slate-500 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <AnnonceDetailContent
          {...detail}
          onToggleFavorite={detail.toggleFavorite}
          onVoirAnnonce={detail.handleVoirAnnonce}
          onExportPdf={detail.handleExportPdf}
        />
      </div>
    </div>,
    document.body,
  );
}
