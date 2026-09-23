import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { api, describeApiError } from '../services/api';
import { sanitizeListingUrl } from '../services/sanitizeUrl';
import { deriveSource } from '../services/annonceType';
import { downloadBlob } from '../services/downloadBlob';
import { useFavorites } from '../hooks/useFavorites';

const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');
const formatM2 = (p) => (p != null ? p.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : '--');
const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])';

const CATEGORY_STYLES = {
  Vice: 'text-red-400',
  Gentrification: 'text-violet-400',
  Nuisance: 'text-orange-400',
  Superstition: 'text-slate-400',
};

// Vue détail d'une annonce (ORA-131, refondue maquette 06 par ORA-174),
// consommant GET /api/annonces/:id enrichi (ORA-174 : coordonnées,
// quartier_prix_m2_moyen, cavaliers_detail — services/annonce_detail.py).
// Aucune photo/capture du site source affichée (ORA-94/ORA-133) —
// uniquement un pictogramme générique, jamais une image tierce (contrainte
// légale, LEGAL_DECISIONS.md). `annonceId` null : rien à afficher.
export default function AnnonceDetailModal({ annonceId, onClose }) {
  const [annonce, setAnnonce] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const dialogRef = useRef(null);
  const { isFavorite, toggleFavorite } = useFavorites();

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

  const safeUrl = sanitizeListingUrl(annonce?.url);
  const source = deriveSource(annonce?.url);
  const favorite = isFavorite(annonceId);

  const handleVoirAnnonce = () => {
    api.logAnnonceClick(annonceId).catch((err) => {
      console.error('❌ Erreur tracking clic annonce:', err);
    });
    if (safeUrl) {
      window.open(safeUrl, '_blank', 'noopener,noreferrer');
    }
  };

  // ORA-174 : réutilise le générateur PDF existant (/api/report/pdf, ORA-121)
  // — pas de nouvel endpoint pour une fiche annonce, dont les champs
  // recouvrent ceux déjà acceptés (quartier/estimation/prix_m2/facteurs).
  const handleExportPdf = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const facteurs = (annonce?.cavaliers_detail || [])
        .filter((cat) => cat.items.length > 0)
        .map((cat) => ({
          categorie: cat.categorie,
          phrase: `${cat.items[0].poi} à ${cat.items[0].dist_m} m (${cat.total} lieu${cat.total > 1 ? 'x' : ''} dans le rayon).`,
        }));
      const blob = await api.exportEstimationPdf({
        quartier: annonce.quartier,
        estimated_price: annonce.prix,
        prix_m2: annonce.prix_m2,
        type_local: annonce.type_local,
        facteurs,
      });
      const slug = (annonce.quartier || 'annonce').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      downloadBlob(blob, `annonce-oracle-${slug}.pdf`);
    } catch (err) {
      console.error(err);
      setExportError(describeApiError(err));
    } finally {
      setExporting(false);
    }
  };

  const prixM2 = annonce?.prix_m2 ?? (annonce?.prix && annonce?.surface ? annonce.prix / annonce.surface : null);
  const ecart =
    prixM2 != null && annonce?.quartier_prix_m2_moyen
      ? Math.round(((prixM2 - annonce.quartier_prix_m2_moyen) / annonce.quartier_prix_m2_moyen) * 100)
      : null;

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

        {/* ORA-133/légal : pictogramme générique, jamais une photo du bien */}
        <div className="h-32 flex flex-col items-center justify-center gap-1.5 bg-ink-800 text-slate-600 border-b border-ink-700">
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2"></rect>
            <circle cx="9" cy="9" r="2"></circle>
            <path d="m21 15-5-5L5 21"></path>
          </svg>
          <span className="text-[10px] uppercase tracking-widest font-bold">Photo de l'annonce</span>
        </div>

        <div className="p-4 space-y-3">
          {loading && (
            <div className="animate-pulse space-y-2">
              <div className="h-5 bg-ink-800 rounded w-3/4"></div>
              <div className="h-4 bg-ink-800 rounded w-1/2"></div>
            </div>
          )}

          {!loading && error && (
            <p className="text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
              {error}
            </p>
          )}

          {!loading && !error && annonce && (
            <>
              <div className="flex items-baseline justify-between gap-2">
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-white">{formatPrice(annonce.prix)} €</span>
                  <span className="text-sm text-slate-500">/ mois</span>
                </div>
                {ecart != null && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${ecart > 0 ? 'bg-red-900/40 text-red-400' : 'bg-green-900/40 text-green-400'}`}>
                    {ecart > 0 ? '+' : ''}{ecart} % vs médiane du quartier
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-500">
                Appartement · {annonce.ville}{annonce.quartier ? ` · ${annonce.quartier}` : ''}
                {source ? ` · publié sur ${source}` : ''}
              </p>

              <div className="grid grid-cols-3 gap-2 pt-1">
                <div className="bg-ink-800 rounded-lg p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Surface</p>
                  <p className="text-sm font-bold text-white">{annonce.surface != null ? `${annonce.surface} m²` : '—'}</p>
                </div>
                <div className="bg-ink-800 rounded-lg p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">Prix m²</p>
                  <p className="text-sm font-bold text-yellow-400">{formatM2(prixM2)} €</p>
                </div>
                <div className="bg-ink-800 rounded-lg p-2">
                  <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold">
                    Médiane {annonce.type_local || ''}
                  </p>
                  <p className="text-sm font-bold text-white">{formatM2(annonce.quartier_prix_m2_moyen)} €/m²</p>
                </div>
              </div>

              {/* ORA-174 : "Autour de l'appartement" — cavaliers autour des
                  coordonnées de CETTE annonce (services/annonce_detail.py),
                  absence gérée par le 0/"—" plutôt qu'une catégorie masquée. */}
              {annonce.cavaliers_detail && annonce.cavaliers_detail.length > 0 && (
                <div>
                  <p className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1.5">
                    Autour de l'appartement · 500 m
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {annonce.cavaliers_detail.map((cat) => {
                      const closest = cat.items.length > 0 ? Math.min(...cat.items.map((i) => i.dist_m)) : null;
                      return (
                        <div key={cat.categorie} className="bg-ink-800 rounded-lg p-2">
                          <p className={`text-[11px] font-bold ${CATEGORY_STYLES[cat.categorie] || 'text-slate-400'}`}>
                            {cat.categorie}
                          </p>
                          <p className="text-sm font-bold text-white">{cat.total}</p>
                          <p className="text-[9px] text-slate-500">
                            {closest != null ? `le plus proche ${closest} m` : '—'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={handleVoirAnnonce}
                  disabled={!safeUrl}
                  className="flex-1 text-[10px] uppercase tracking-widest font-bold text-white bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg py-2.5 transition-colors"
                >
                  {source ? `Voir sur ${source}` : "Voir l'annonce"} ↗
                </button>
                <button
                  type="button"
                  onClick={() => toggleFavorite(annonceId)}
                  aria-pressed={favorite}
                  aria-label={favorite ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                  className={`shrink-0 text-[10px] uppercase tracking-widest font-bold border rounded-lg py-2.5 px-3 transition-colors ${
                    favorite ? 'text-amber-400 border-amber-500/40 bg-amber-900/20' : 'text-slate-400 border-ink-700 hover:text-amber-300'
                  }`}
                >
                  {favorite ? '★' : '☆'} favori
                </button>
                <button
                  type="button"
                  onClick={handleExportPdf}
                  disabled={exporting}
                  aria-label="Exporter en PDF"
                  className="shrink-0 text-[10px] uppercase tracking-widest font-bold text-slate-400 hover:text-slate-200 border border-ink-700 rounded-lg py-2.5 px-3 transition-colors disabled:opacity-40"
                >
                  {exporting ? '…' : 'PDF'}
                </button>
              </div>

              {exportError && (
                <p className="text-[10px] text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
                  Erreur lors de l'export PDF : {exportError}
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
