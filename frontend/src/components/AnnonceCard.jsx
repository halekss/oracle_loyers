import React from 'react';
import { api } from '../services/api';

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');

// Pas de photo hébergée par nous (décision ORA-94/ORA-86 : cf. LEGAL_DECISIONS.md)
// — la carte affiche un simple bandeau placeholder, la photo réelle reste sur le
// site source, atteint via la redirection au clic.
export default function AnnonceCard({ annonce }) {
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
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
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
      <div className="h-20 bg-slate-800/60 flex items-center justify-center text-slate-600 text-[9px] uppercase tracking-widest font-bold px-2 text-center">
        Photo sur le site source
      </div>

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

        <p className="mt-2 text-[10px] uppercase tracking-widest font-bold text-purple-400 group-hover:text-purple-300">
          Voir l'annonce ↗
        </p>
      </div>
    </div>
  );
}
