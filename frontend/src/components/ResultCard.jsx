import React, { useState } from "react";
import { api, describeApiError } from "../services/api";
import { downloadBlob } from "../services/downloadBlob";

// `onViewAnnonces` (optionnel, ORA-127) : appelé avec le quartier scanné
// (`data.quartier`) quand l'utilisateur clique le lien direct vers ses
// annonces — le parent (App) s'en sert pour présélectionner AnnoncesList.
export default function ResultCard({ data, loading, priceHistory, onViewAnnonces }) {

  const safeData = data || {};
  const stats = safeData.stats || {};

  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  const confiance = safeData.confiance;
  const quartier = safeData.quartier;
  const facteurs = safeData.facteurs || [];
  const comparables = safeData.comparables || [];

  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);

  const formatPrice = (p) => p ? Math.round(p).toLocaleString('fr-FR') : "--";

  const confidenceStyles = {
    'Élevée': 'bg-green-900/40 text-green-400 border-green-700/50',
    'Moyenne': 'bg-amber-900/40 text-amber-400 border-amber-700/50',
    'Faible': 'bg-red-900/40 text-red-400 border-red-700/50',
  };

  // ORA-121 : génération PDF côté serveur (WeasyPrint) + téléchargement
  // direct, plus de window.print()/sélecteur d'impression système.
  const handleExportPdf = async () => {
    setExporting(true);
    setExportError(null);

    try {
      const blob = await api.exportEstimationPdf({
        quartier,
        estimated_price: estimatedPrice,
        prix_m2: m2PriceRaw,
        confiance,
        count: safeData.count,
        type_local: safeData.type,
        facteurs,
        historique: priceHistory?.historique || undefined,
        comparables: comparables.length > 0 ? comparables : undefined,
      });
      const slug = (quartier || 'estimation').toLowerCase().replace(/[^a-z0-9]+/g, '-');
      downloadBlob(blob, `rapport-oracle-${slug}.pdf`);
    } catch (err) {
      console.error(err);
      setExportError(describeApiError(err));
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse w-full space-y-3">
        <div className="flex gap-3">
           <div className="h-20 bg-slate-800 rounded-xl w-2/3"></div>
           <div className="h-20 bg-slate-800 rounded-xl w-1/3"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full animate-fade-in">

      {/* SECTION PRIX PRINCIPALE */}
      <div className="flex gap-3">

        {/* GROS BLOC : LOYER */}
        <div className="flex-1 bg-gradient-to-br from-slate-800 to-slate-900 p-4 rounded-xl border border-purple-500/20 shadow-[0_4px_20px_rgba(0,0,0,0.2)] relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-5 text-6xl font-black text-white pointer-events-none">€</div>

          <div className="flex justify-between items-start">
            <div>
                <p className="text-[10px] uppercase text-purple-400 font-bold tracking-widest mb-1">Estimation Loyer</p>
                <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black text-white tracking-tighter shadow-black drop-shadow-lg">
                    {formatPrice(estimatedPrice)}
                    </span>
                    <span className="text-lg text-slate-500">€</span>
                </div>
            </div>
            {confiance && (
              <span
                className={`text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border ${confidenceStyles[confiance] || 'bg-slate-800 text-slate-400 border-slate-700'}`}
                title={safeData.count != null ? `Basée sur ${safeData.count} bien(s) comparable(s) du même quartier et type` : undefined}
              >
                Confiance IA : {confiance}
              </span>
            )}
          </div>
          {/* ORA-128 : explique la confiance plutôt que de la laisser abstraite */}
          {safeData.count != null && (
            <p className="mt-2 text-[9px] text-slate-500">
              Basée sur {safeData.count} bien{safeData.count > 1 ? 's' : ''} comparable{safeData.count > 1 ? 's' : ''} du même quartier et type.
            </p>
          )}
          {/* ORA-127 : lien direct depuis le quartier scanné vers ses annonces */}
          {quartier && onViewAnnonces && (
            <button
              type="button"
              onClick={() => onViewAnnonces(quartier)}
              className="mt-2 text-[9px] uppercase tracking-widest font-bold text-purple-400 hover:text-purple-300 transition-colors underline decoration-purple-500/40 underline-offset-2"
            >
              Voir les annonces de {quartier} →
            </button>
          )}
        </div>

        {/* PETIT BLOC : PRIX M2 */}
        <div className="w-1/3 bg-slate-900 p-3 rounded-xl border border-slate-700 flex flex-col justify-center items-center relative">
          <p className="text-[9px] uppercase text-slate-500 font-bold mb-1">Prix m²</p>
          <div className="text-xl font-bold text-yellow-400 font-mono">
            {formatPrice(m2PriceRaw)}
          </div>
          <p className="text-[9px] text-slate-600 mt-1">Moyenne</p>
        </div>
      </div>

      {comparables.length > 0 && (
        <div className="mt-3 bg-slate-900 rounded-xl border border-slate-700 p-3">
          <p className="text-[9px] uppercase text-slate-500 font-bold tracking-widest mb-2">Biens comparables</p>
          <ul className="space-y-1">
            {comparables.map((c, i) => (
              <li key={i} className="flex justify-between text-[11px] text-slate-300">
                <span>{c.type_local || '—'}</span>
                <span>{formatPrice(c.prix)} € · {formatPrice(c.surface)} m²</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data && (
        <>
          <button
            type="button"
            onClick={handleExportPdf}
            disabled={exporting}
            className="mt-3 w-full text-[10px] uppercase tracking-widest font-bold text-purple-400 border border-purple-500/30 rounded-lg py-2 hover:bg-purple-500/10 transition-colors disabled:opacity-50"
          >
            {exporting ? 'Génération du PDF...' : 'Exporter en PDF'}
          </button>

          {exportError && (
            <p className="mt-2 text-[10px] text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
              Erreur lors de l'export PDF : {exportError}
            </p>
          )}
        </>
      )}
    </div>
  );
}
