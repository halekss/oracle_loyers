import React from 'react';

export default function ResultCard({ data }) {
  // --- SÉCURISATION DES DONNÉES ---
  // Si 'data' est vide ou n'existe pas encore, on met des valeurs par défaut pour éviter le crash.
  const safeData = data || {};
  const estimatedPrice = safeData.estimated_price || 0;
  // La note contient tout le texte : "24.5 €/m² (Basé sur...)"
  const fullNote = safeData.price_note || "En attente de données...";

  // On essaie d'extraire le prix au m2 (le chiffre au début) et le détail (entre parenthèses)
  // Si ça échoue, on affiche des tirets, mais on ne plante pas.
  let m2PriceDisplay = "---";
  let m2DetailDisplay = "Estimation théorique";

  if (fullNote.includes("€/m²")) {
    try {
        const parts = fullNote.split("€/m²");
        m2PriceDisplay = parts[0].trim(); // La partie avant "€/m²"
        if (parts[1] && parts[1].includes("(")) {
            m2DetailDisplay = parts[1].replace("(", "").replace(")", "").trim();
        }
    } catch (e) {
        // Si le format n'est pas celui attendu, on ne fait rien et on garde les tirets
        console.warn("Format de note inattendu :", fullNote);
    }
  }

  return (
    <div className="bg-slate-900/90 backdrop-blur-xl border border-blue-500/30 rounded-3xl p-8 shadow-2xl w-full max-w-2xl mx-auto relative overflow-hidden">
      
      {/* Effet de brillance haut */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-70"></div>

      {/* EN-TÊTE : MESSAGE */}
      <div className="mb-8 text-center">
        <h2 className="text-blue-400 text-xs font-bold tracking-[0.2em] uppercase mb-2">
            Rapport d'analyse
        </h2>
        <p className="text-white text-lg font-light italic opacity-90">
            "{safeData.message || "Prêt pour l'analyse."}"
        </p>
      </div>

      {/* GRILLE DE DONNÉES */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* BLOC 1 : LOYER TOTAL */}
        <div className="bg-slate-950/50 p-6 rounded-2xl border border-white/5 flex flex-col items-center justify-center group hover:border-blue-500/30 transition-all">
            <span className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-2">
                Loyer Mensuel Estimé
            </span>
            <div className="flex items-baseline gap-1">
                <span className="text-5xl font-mono font-bold text-white tracking-tighter">
                    {estimatedPrice > 0 ? estimatedPrice : "---"}
                </span>
                <span className="text-xl text-blue-400">€</span>
            </div>
            <span className="text-slate-600 text-xs mt-1">Hors charges (T2 standard)</span>
        </div>

        {/* BLOC 2 : PRIX AU M² */}
        <div className="bg-slate-950/50 p-6 rounded-2xl border border-white/5 flex flex-col items-center justify-center group hover:border-yellow-500/30 transition-all">
            <span className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-2">
                Moyenne du Secteur
            </span>
            <div className="flex items-baseline gap-1">
                <span className="text-4xl font-mono font-bold text-yellow-400 tracking-tighter">
                    {m2PriceDisplay}
                </span>
                <span className="text-lg text-yellow-600">€/m²</span>
            </div>
            <span className="text-slate-600 text-[10px] uppercase mt-1">
                {m2DetailDisplay}
            </span>
        </div>

      </div>

      {/* PIED DE PAGE : STATUT */}
      <div className="mt-6 pt-6 border-t border-white/5 flex justify-between items-center text-xs text-slate-500">
        <div className="flex items-center gap-2">
            {/* Pastille verte si on a un prix, rouge sinon */}
            <div className={`w-2 h-2 rounded-full ${estimatedPrice > 0 ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-red-500'}`}></div>
            <span>{estimatedPrice > 0 ? "Données live" : "En attente"}</span>
        </div>
        <div className="font-mono opacity-50">
            ORACLE_DATA_V2
        </div>
      </div>

    </div>
  );
}