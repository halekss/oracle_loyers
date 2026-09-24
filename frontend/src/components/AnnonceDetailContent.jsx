const formatPrice = (p) => (p ? Math.round(p).toLocaleString('fr-FR') : '--');
const formatM2 = (p) => (p != null ? p.toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : '--');

const CATEGORY_STYLES = {
  Vice: 'text-red-400',
  Gentrification: 'text-violet-400',
  Nuisance: 'text-orange-400',
  Superstition: 'text-slate-400',
};

// ORA-178 : contenu pur du détail d'une annonce (maquette 06, ORA-174),
// extrait de AnnonceDetailModal.jsx pour être réutilisé tel quel par la
// modale (chrome dialog/portail/piège de focus) et par la vue "Fiche" du
// rail (rendue inline dans la feuille de contenu, sans chrome de modale).
// Toutes les données/actions viennent de `useAnnonceDetail(annonceId)`.
export default function AnnonceDetailContent({
  annonce, loading, error, exporting, exportError,
  safeUrl, source, favorite, prixM2, ecart,
  onToggleFavorite, onVoirAnnonce, onExportPdf,
}) {
  return (
    <>
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
                onClick={onVoirAnnonce}
                disabled={!safeUrl}
                className="flex-1 text-[10px] uppercase tracking-widest font-bold text-white bg-violet-600 hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg py-2.5 transition-colors"
              >
                {source ? `Voir sur ${source}` : "Voir l'annonce"} ↗
              </button>
              <button
                type="button"
                onClick={onToggleFavorite}
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
                onClick={onExportPdf}
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
    </>
  );
}
