import React from "react";

export default function ResultCard({ data, loading }) {
  
  const safeData = data || {};
  const stats = safeData.stats || {};
  
  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;

  const formatPrice = (p) => p ? Math.round(p).toLocaleString('fr-FR') : "--";

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

    </div>
  );
}