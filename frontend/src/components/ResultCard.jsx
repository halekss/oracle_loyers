import React from "react";

export default function ResultCard({ data }) {
  // Sécurisation : si data est null, on met un objet vide
  const safeData = data || {};
  
  // LE FIX EST ICI : On va chercher dans 'stats' envoyé par Python
  const stats = safeData.stats || {};
  
  // Récupération des valeurs (avec fallback à 0 si manquant)
  const estimatedPrice = safeData.estimated_price || 0;
  const m2PriceRaw = stats.prix_m2 || 0;
  
  // Formatage pour l'affichage (ex: "4 500")
  const formatPrice = (p) => p.toLocaleString('fr-FR');

  return (
    <div className="bg-slate-900/90 backdrop-blur-xl border border-blue-500/30 rounded-3xl p-6 shadow-2xl w-full max-w-2xl mx-auto relative overflow-hidden animate-fade-in-up">
      
      {/* Effet de brillance */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>

      <div className="flex flex-row justify-between items-center gap-6">
        
        {/* PARTIE GAUCHE : LOYER TOTAL */}
        <div className="flex-1 text-center border-r border-white/10 pr-6">
          <h2 className="text-slate-400 text-xs uppercase tracking-[0.2em] mb-2 font-bold">
            Estimation Loyer
          </h2>
          <div className="flex items-baseline justify-center gap-1">
            <span className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-br from-white to-blue-400 drop-shadow-lg">
              {formatPrice(estimatedPrice)}
            </span>
            <span className="text-xl text-slate-500 font-light">€</span>
          </div>
          <p className="text-slate-500 text-xs mt-2 italic">
            charges comprises (environ)
          </p>
        </div>

        {/* PARTIE DROITE : PRIX AU M² */}
        <div className="bg-slate-950/50 p-4 rounded-2xl border border-white/5 flex flex-col items-center justify-center min-w-[120px]">
          <span className="text-slate-500 text-[10px] uppercase tracking-wider font-semibold mb-1">
            Prix au m²
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-yellow-400">
              {m2PriceRaw > 0 ? formatPrice(m2PriceRaw) : "---"}
            </span>
            <span className="text-sm text-yellow-600">€</span>
          </div>
          <span className="text-slate-600 text-[9px] uppercase mt-1">
            Moyenne locale
          </span>
        </div>
      </div>

      {/* FOOTER : INFOS DEBUG */}
      <div className="mt-4 pt-4 border-t border-white/5 flex justify-between items-center text-[10px] text-slate-500">
        <div className="flex items-center gap-2">
           <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
           <span>IA Active</span>
        </div>
        <div>
          {stats.nb_biens_analyse 
            ? `Basé sur ${stats.nb_biens_analyse} biens similaires`
            : "Analyse en cours..."}
        </div>
      </div>
    </div>
  );
}