import { useState, useEffect } from 'react';
import { api, describeApiError } from '../services/api';

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');

const formatDate = (iso) => {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
};

// Vue détail d'une annonce (ORA-131), consommant GET /api/annonces/:id
// (jusqu'ici jamais utilisé côté frontend). Aucune photo/capture du site
// source affichée (ORA-94/ORA-133) — uniquement les champs texte déjà
// exposés par l'API. `annonceId` null : rien à afficher (composant inerte).
export default function AnnonceDetailModal({ annonceId, onClose }) {
  const [annonce, setAnnonce] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (annonceId == null) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setAnnonce(null);

    api.getAnnonceDetail(annonceId)
      .then((data) => {
        if (!cancelled) setAnnonce(data);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError(describeApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [annonceId]);

  if (annonceId == null) return null;

  const handleVoirAnnonce = () => {
    api.logAnnonceClick(annonceId).catch((err) => {
      console.error('❌ Erreur tracking clic annonce:', err);
    });
    if (annonce?.url) {
      window.open(annonce.url, '_blank', 'noopener,noreferrer');
    }
  };

  const publishedLabel = formatDate(annonce?.date_scraping);

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Détail de l'annonce"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-4 py-3 bg-slate-950/80 border-b border-slate-800">
          <span className="text-xs font-black uppercase tracking-widest text-white">Détail de l'annonce</span>
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

        <div className="p-4 space-y-3">
          {loading && (
            <div className="animate-pulse space-y-2">
              <div className="h-5 bg-slate-800 rounded w-3/4"></div>
              <div className="h-4 bg-slate-800 rounded w-1/2"></div>
            </div>
          )}

          {!loading && error && (
            <p className="text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
              {error}
            </p>
          )}

          {!loading && !error && annonce && (
            <>
              <p className="text-base font-bold text-white">{annonce.titre || 'Annonce sans titre'}</p>

              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-black text-white">{formatPrice(annonce.prix)} €</span>
                {annonce.surface != null && <span className="text-sm text-slate-500">{annonce.surface} m²</span>}
              </div>

              <div className="flex flex-wrap gap-2 text-[10px] uppercase tracking-widest font-bold">
                {annonce.quartier && (
                  <span className="px-2 py-1 rounded-full border bg-purple-900/40 text-purple-400 border-purple-700/50">
                    {annonce.quartier}
                  </span>
                )}
                {annonce.ville && <span className="text-slate-500 self-center">{annonce.ville}</span>}
              </div>

              {publishedLabel && (
                <p className="text-[11px] text-slate-500">Publiée le {publishedLabel}</p>
              )}

              <button
                type="button"
                onClick={handleVoirAnnonce}
                className="mt-2 w-full text-[10px] uppercase tracking-widest font-bold text-purple-400 border border-purple-500/30 rounded-lg py-2 hover:bg-purple-500/10 transition-colors"
              >
                Voir l'annonce ↗
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
