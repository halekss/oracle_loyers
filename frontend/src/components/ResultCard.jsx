import React from "react";

export default function ResultCard({ data, loading }) {

  const safeData = data || {};
  const stats = safeData.stats || {};

  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  const confiance = safeData.confiance;
  const quartier = safeData.quartier;
  const facteurs = safeData.facteurs || [];

  const formatPrice = (p) => p ? Math.round(p).toLocaleString('fr-FR') : "--";

  const confidenceStyles = {
    'Élevée': 'bg-green-900/40 text-green-400 border-green-700/50',
    'Moyenne': 'bg-amber-900/40 text-amber-400 border-amber-700/50',
    'Faible': 'bg-red-900/40 text-red-400 border-red-700/50',
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
              <span className={`text-[9px] uppercase font-bold tracking-wide px-2 py-1 rounded-full border ${confidenceStyles[confiance] || 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                Confiance IA : {confiance}
              </span>
            )}
          </div>
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

      {data && (
        <>
          {/* Les 4 Cavaliers ne sont plus affichés ici à l'écran : regroupés
              avec l'historique et les annonces dans le dropdown "Détails du
              quartier" (App.jsx), pour ne garder qu'un seul repli à gérer.
              Toujours repris ci-dessous dans le rapport imprimable. */}

          <button
            type="button"
            onClick={() => window.print()}
            className="print:hidden mt-3 w-full text-[10px] uppercase tracking-widest font-bold text-purple-400 border border-purple-500/30 rounded-lg py-2 hover:bg-purple-500/10 transition-colors"
          >
            Exporter en PDF
          </button>

          {/* RAPPORT IMPRIMABLE — masqué à l'écran, seul élément visible à l'impression (voir index.css) */}
          <div id="printable-report" className="hidden print:block text-black">
            <h1 className="text-2xl font-black mb-1">Oracle des Loyers — Rapport d'estimation</h1>
            {quartier && <p className="text-sm mb-4">Quartier : {quartier}</p>}
            <p className="text-xl font-bold mb-1">Estimation : {formatPrice(estimatedPrice)} € / mois</p>
            <p className="text-sm mb-4">Prix moyen au m² : {formatPrice(m2PriceRaw)} €</p>
            {facteurs.length > 0 && (
              <>
                <h2 className="text-lg font-bold mb-2">Les 4 Cavaliers du quartier</h2>
                <ul className="space-y-1 text-sm list-disc list-inside">
                  {facteurs.map((f) => (
                    <li key={f.categorie}><strong>{f.categorie}</strong> — {f.phrase}</li>
                  ))}
                </ul>
              </>
            )}
            <p className="text-[10px] text-gray-500 mt-6">Estimation générée par l'Oracle des Loyers, à titre indicatif — non contractuelle.</p>
          </div>
        </>
      )}
    </div>
  );
}