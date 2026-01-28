import React from "react";

export default function ResultCard({ data, loading }) {
  
  const safeData = data || {};
  const stats = safeData.stats || {};
  
  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  const nbBiens = stats.nb_biens_analyse || 0;

  const formatPrice = (p) => p ? Math.round(p).toLocaleString('fr-FR') : "--";

  // Simulation basique de "Tension" pour l'UI (en attendant une vraie data)
  // Si le prix m² > 25€ (exemple Lyon), on considère que c'est tendu
  const isHighTension = m2PriceRaw > 25; 

  if (loading) {
    return (
      <div className="animate-pulse w-full space-y-3">
        <div className="flex gap-3">
           <div className="h-20 bg-slate-800 rounded-xl w-2/3"></div>
           <div className="h-20 bg-slate-800 rounded-xl w-1/3"></div>
        </div>
        <div className="h-2 bg-slate-800 rounded w-full"></div>
      </div>
    );
  }

  return (
    <div className="w-full animate-fade-in">
      
      {/* SECTION PRIX PRINCIPALE */}
      <div className="flex gap-3 mb-4">
        
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
            {/* Indicateur Tendance */}
            <div className="text-right">
                <span className="flex items-center justify-end text-xs font-bold text-green-400 bg-green-400/10 px-2 py-1 rounded-full border border-green-400/20">
                    ↗ +2%
                </span>
                <p className="text-[9px] text-slate-600 mt-1">vs mois dernier</p>
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

      {/* JAUGE DE CONTEXTE (UI UX Advice) */}
      <div className="bg-slate-950/50 rounded-lg p-3 border border-slate-800/50">
        <div className="flex justify-between items-end mb-2">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Indice de Tension Locative</span>
            <span className={`text-[10px] font-bold ${isHighTension ? 'text-red-400' : 'text-green-400'}`}>
                {isHighTension ? "MARCHÉ TENDU" : "MARCHÉ FLUIDE"}
            </span>
        </div>
        
        {/* La barre visuelle */}
        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden flex">
            {/* On simule une jauge remplie selon le prix */}
            <div 
                className={`h-full transition-all duration-1000 ${isHighTension ? 'bg-gradient-to-r from-orange-500 to-red-600' : 'bg-gradient-to-r from-green-500 to-emerald-400'}`} 
                style={{ width: isHighTension ? '85%' : '45%' }}
            ></div>
        </div>
        
        <div className="mt-2 flex justify-between text-[9px] text-slate-600 font-mono">
             <span>Faible</span>
             <span>Moyenne</span>
             <span>Forte</span>
        </div>
      </div>

    </div>
  );
}