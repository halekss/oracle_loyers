import React, { useState } from 'react';
import { api } from '../services/api';
import { sanitizeListingUrl } from '../services/sanitizeUrl';
import AnnonceDetailModal from './AnnonceDetailModal';
import AnnonceIllustration from './AnnonceIllustration';
import { useFavorites } from '../hooks/useFavorites';
import { BAND_BADGE_CLASSES, MARKET_BANDS, ecartPct, marketBand } from '../services/marketBand';
import { getTypeCategory, deriveSource } from '../services/annonceType';

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');

// `referencePrixM2` (optionnel, ORA-173) : €/m² moyen du quartier scanné
// (App.jsx, `result.quartierPrixM2` — ORA-171), pour le badge d'écart de la
// maquette 05 ("−18 %"). Sans scan actif, aucune référence : pas de badge
// plutôt qu'une comparaison inventée. `referenceType` (le type_local pour
// lequel cette référence a été calculée, ex. "T2") : le badge ne s'affiche
// que si l'annonce est du même type — comparer un T4+ à une référence T2
// produirait un écart trompeur (types à des gammes de prix différentes).
// `onOpenDetail` (optionnel, ORA-178) : quand fourni (rail présent, App.jsx),
// "Détails" bascule sur la vue "Fiche" du panneau au lieu d'ouvrir la modale
// locale — repli sur l'ancien comportement (modale) sans ce prop, pour tout
// appelant qui ne le fournit pas encore.
export default function AnnonceCard({ annonce, referencePrixM2, referenceType, onOpenDetail }) {
  const [detailOpen, setDetailOpen] = useState(false);
  // ORA-132 : favoris "Mes favoris" — persistance localStorage uniquement
  // (décision de cadrage, cf. useFavorites.js), pas de compte utilisateur.
  const { isFavorite, toggleFavorite } = useFavorites();

  if (!annonce) return null;

  const { id, titre, prix, surface, ville, quartier, url, images, suspect, suspect_reason: suspectReason } = annonce;
  const favorite = isFavorite(id);
  const source = deriveSource(url);

  const prixM2 = Number.isFinite(prix) && Number.isFinite(surface) && surface > 0 ? prix / surface : null;
  const sameTypeAsReference =
    !referenceType || referenceType === 'Tout' || getTypeCategory(titre, surface) === referenceType;
  const ecart = sameTypeAsReference ? ecartPct(prixM2, referencePrixM2) : null;
  const band = ecart != null ? marketBand(ecart) : null;
  // ORA-113 : sans URL exploitable (absente, vide ou rejetée par la
  // sanitisation), la carte est explicitement désactivée au lieu d'un clic muet.
  const safeUrl = sanitizeListingUrl(url);

  const handleToggleFavorite = (e) => {
    e.stopPropagation();
    toggleFavorite(id);
  };

  const handleOpen = () => {
    if (!safeUrl) return;
    if (id != null) {
      // Fire-and-forget (ORA-89/ORA-91) : le tracking ne doit jamais retarder
      // ni bloquer la redirection vers le site source.
      api.logAnnonceClick(id).catch((error) => {
        console.error('❌ Erreur tracking clic annonce:', error);
      });
    }
    window.open(safeUrl, '_blank', 'noopener,noreferrer');
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
      aria-disabled={!safeUrl}
      aria-label={
        safeUrl
          ? `Voir l'annonce${titre ? ` : ${titre}` : ''} sur le site source`
          : `Lien indisponible${titre ? ` : ${titre}` : ''}`
      }
      onClick={handleOpen}
      onKeyDown={handleKeyDown}
      className={`animate-fade-in text-left w-full bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl border border-purple-500/20 overflow-hidden group ${
        safeUrl ? 'cursor-pointer hover:border-purple-500/50 transition-colors' : 'cursor-not-allowed opacity-60'
      }`}
    >
      <AnnonceIllustration titre={titre} surface={surface} image={images?.[0]} />

      <div className="p-3">
        <div className="flex justify-between items-start gap-2 min-w-0">
          <p className="min-w-0 text-sm font-bold text-white truncate">{titre || 'Annonce sans titre'}</p>
          <div className="flex items-center gap-1.5 shrink-0">
            {id != null && (
              <button
                type="button"
                onClick={handleToggleFavorite}
                aria-pressed={favorite}
                aria-label={favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                className={`leading-none text-base transition-colors ${
                  favorite ? 'text-amber-400 hover:text-amber-300' : 'text-slate-600 hover:text-amber-300'
                }`}
              >
                {favorite ? '★' : '☆'}
              </button>
            )}
            {quartier && (
              <span className="shrink-0 text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border bg-purple-900/40 text-purple-400 border-purple-700/50">
                {quartier}
              </span>
            )}
            {suspect && (
              // ORA-195 : badge discret — signale sans alarmer, l'annonce
              // reste consultable (règle : ne jamais rien supprimer).
              <span
                title={suspectReason || 'Donnée douteuse'}
                className="shrink-0 text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border bg-slate-800 text-slate-400 border-slate-700"
              >
                ⚠ Donnée douteuse
              </span>
            )}
          </div>
        </div>

        <div className="mt-2 flex items-baseline justify-between gap-2 min-w-0">
          <div className="flex items-baseline gap-2 min-w-0">
            <span className="shrink-0 text-xl font-black text-white">{formatPrice(prix)} €</span>
            {surface != null && (
              <span className="min-w-0 truncate text-xs text-slate-500">
                {surface} m²{prixM2 != null && ` · ${prixM2.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} €/m²`}
              </span>
            )}
          </div>
          {ecart != null && (
            <span
              className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${BAND_BADGE_CLASSES[band]}`}
              title={`${MARKET_BANDS[band].label} — écart vs €/m² moyen du quartier scanné`}
            >
              {ecart > 0 ? '+' : ''}{ecart} %
            </span>
          )}
        </div>

        <div className="mt-1 flex items-center gap-1.5">
          {ville && <p className="text-[10px] text-slate-500">{ville}</p>}
          {source && (
            <span className="text-[9px] uppercase font-bold tracking-wide px-1.5 py-0.5 rounded bg-ink-800 text-slate-400">
              {source}
            </span>
          )}
        </div>

        <div className="mt-2 flex items-center justify-between gap-2">
          {safeUrl ? (
            <p className="text-[10px] uppercase tracking-widest font-bold text-purple-400 group-hover:text-purple-300">
              Voir l'annonce ↗
            </p>
          ) : (
            <p className="text-[10px] uppercase tracking-widest font-bold text-slate-500">Lien indisponible</p>
          )}
          {id != null && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (onOpenDetail) {
                  onOpenDetail(id);
                } else {
                  setDetailOpen(true);
                }
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
