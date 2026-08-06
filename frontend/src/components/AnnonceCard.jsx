import React, { useState } from 'react';
import { api } from '../services/api';
import { sanitizeListingUrl } from '../services/sanitizeUrl';
import AnnonceDetailModal from './AnnonceDetailModal';

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');

// `annonces.db` ne stocke pas de colonne `type_local` séparée, mais
// `build_titre` (clean_immo.py) préfixe déjà le titre avec elle
// ("T3 — Monplaisir / Bachut") : on la lit là en priorité, pour rester
// cohérent avec le type réellement affiché dans le titre de la carte (basé
// sur le texte de l'annonce, plus fiable que la seule surface). Fallback sur
// les seuils de surface de `determine_type_local` si le titre ne la contient
// pas (annonce sans quartier, titre de repli sur la description...).
const KNOWN_CATEGORIES = ['Studio/T1', 'T2', 'T3', 'Grand (T4+)'];

const getTypeCategory = (titre, surface) => {
  if (typeof titre === 'string') {
    const prefix = titre.split(' — ')[0].trim();
    if (KNOWN_CATEGORIES.includes(prefix)) return prefix;
  }

  const s = Number(surface);
  if (!Number.isFinite(s)) return null;
  if (s < 35) return 'Studio/T1';
  if (s < 55) return 'T2';
  if (s < 75) return 'T3';
  return 'Grand (T4+)';
};

const ILLUSTRATION_BY_CATEGORY = {
  'Studio/T1': 'from-sky-900/50 to-slate-900 text-sky-400',
  'T2': 'from-emerald-900/50 to-slate-900 text-emerald-400',
  'T3': 'from-amber-900/50 to-slate-900 text-amber-400',
  'Grand (T4+)': 'from-rose-900/50 to-slate-900 text-rose-400',
};
const DEFAULT_ILLUSTRATION_CLASSES = 'from-slate-800 to-slate-900 text-slate-500';

// Illustration générique produite par nous (icône SVG maison inline, pas de
// fichier externe) — jamais de photo ni de capture d'écran issue de l'annonce
// ou du site source (ORA-133 ; contrainte légale documentée dans
// LEGAL_DECISIONS.md, section ORA-94 : AnnonceCard ne doit afficher aucune
// image provenant de l'annonce elle-même, y compris via hotlink).
function AnnonceIllustration({ titre, surface }) {
  const category = getTypeCategory(titre, surface);
  const classes = ILLUSTRATION_BY_CATEGORY[category] || DEFAULT_ILLUSTRATION_CLASSES;

  return (
    <div className={`h-20 flex flex-col items-center justify-center gap-1 bg-gradient-to-br ${classes}`}>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="w-7 h-7"
        aria-hidden="true"
      >
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5.5 10v9.5h13V10" />
        <path d="M10 19.5v-6h4v6" />
      </svg>
      {category && (
        <span className="text-[8px] uppercase tracking-widest font-bold opacity-80">{category}</span>
      )}
    </div>
  );
}

export default function AnnonceCard({ annonce }) {
  const [detailOpen, setDetailOpen] = useState(false);

  if (!annonce) return null;

  const { id, titre, prix, surface, ville, quartier, url } = annonce;

  const handleOpen = () => {
    if (id != null) {
      // Fire-and-forget (ORA-89/ORA-91) : le tracking ne doit jamais retarder
      // ni bloquer la redirection vers le site source.
      api.logAnnonceClick(id).catch((error) => {
        console.error('❌ Erreur tracking clic annonce:', error);
      });
    }
    const safeUrl = sanitizeListingUrl(url);
    if (safeUrl) {
      window.open(safeUrl, '_blank', 'noopener,noreferrer');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleOpen();
    }
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Voir l'annonce${titre ? ` : ${titre}` : ''} sur le site source`}
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
      className="animate-fade-in text-left w-full bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl border border-purple-500/20 overflow-hidden cursor-pointer hover:border-purple-500/50 transition-colors group"
    >
      <AnnonceIllustration titre={titre} surface={surface} />

      <div className="p-3">
        <div className="flex justify-between items-start gap-2">
          <p className="text-sm font-bold text-white truncate">{titre || 'Annonce sans titre'}</p>
          {quartier && (
            <span className="shrink-0 text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border bg-purple-900/40 text-purple-400 border-purple-700/50">
              {quartier}
            </span>
          )}
        </div>

        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-xl font-black text-white">{formatPrice(prix)} €</span>
          {surface != null && <span className="text-xs text-slate-500">{surface} m²</span>}
        </div>

        {ville && <p className="mt-1 text-[10px] text-slate-500">{ville}</p>}

        <div className="mt-2 flex items-center justify-between gap-2">
          <p className="text-[10px] uppercase tracking-widest font-bold text-purple-400 group-hover:text-purple-300">
            Voir l'annonce ↗
          </p>
          {id != null && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setDetailOpen(true);
              }}
              className="text-[9px] uppercase tracking-widest font-bold text-slate-500 hover:text-slate-300 transition-colors underline underline-offset-2"
            >
              Détails
            </button>
          )}
        </div>
      </div>

      {detailOpen && (
        <AnnonceDetailModal annonceId={id} onClose={() => setDetailOpen(false)} />
      )}
    </div>
  );
}
