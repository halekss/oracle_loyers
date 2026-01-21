import React from "react";

export default function ResultCard({ data }) {
  // --- 1. SÉCURISATION ET MAPPING DES DONNÉES ---
  // On s'assure que data existe, sinon objet vide
  const safeData = data || {};

  // 🔥 LE FIX EST ICI : On va chercher dans 'stats' (ce que le Python envoie)
  const stats = safeData.stats || {};

  // On récupère le prix moyen calculé par Python
  const estimatedPrice = stats.prix_moyen || 0;

  // On récupère le prix au m² calculé par Python
  const m2PriceRaw = stats.prix_m2 || 0;

  // --- 2. LOGIQUE D'AFFICHAGE ---
  const m2PriceDisplay = m2PriceRaw > 0 ? m2PriceRaw : "---";

  // Le message de verdict (ex: "Quartier Riche")
  const verdict = safeData.verdict || "Analyse en cours...";

  // Le nombre de biens utilisés pour le calcul
  const nbBiens = stats.nb_biens_analyse || 0;

  return (
    <div className="bg-slate-900/90 backdrop-blur-xl border border-blue-500/30 rounded-3xl p-8 shadow-2xl w-full max-w-2xl mx-auto relative overflow-hidden animate-fade-in-up">
      {/* Effet de brillance haut */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-70"></div>

      {/* EN-TÊTE : ADRESSE & VERDICT */}
      <div className="mb-8 text-center">
        <h2 className="text-blue-400 text-xs font-bold tracking-[0.2em] uppercase mb-2">
          Rapport pour : {safeData.address || "Localisation inconnue"}
        </h2>
        <p className="text-white text-2xl font-light italic opacity-90">
          "{verdict}"
        </p>
      </div>

      {/* GRILLE DE DONNÉES */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* BLOC 1 : LOYER MOYEN */}
        <div className="bg-slate-950/50 p-6 rounded-2xl border border-white/5 flex flex-col items-center justify-center group hover:border-blue-500/30 transition-all">
          <span className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-2">
            Loyer Moyen Est.
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-5xl font-mono font-bold text-white tracking-tighter">
              {estimatedPrice > 0 ? estimatedPrice : "---"}
            </span>
            <span className="text-xl text-blue-400">€</span>
          </div>
          <span className="text-slate-600 text-[10px] mt-2">
            Basé sur {nbBiens} annonces similaires
          </span>
        </div>

        {/* BLOC 2 : PRIX AU M² */}
        <div className="bg-slate-950/50 p-6 rounded-2xl border border-white/5 flex flex-col items-center justify-center group hover:border-yellow-500/30 transition-all">
          <span className="text-slate-500 text-xs uppercase tracking-wider font-semibold mb-2">
            Prix au m²
          </span>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-mono font-bold text-yellow-400 tracking-tighter">
              {m2PriceDisplay}
            </span>
            <span className="text-lg text-yellow-600">€</span>
          </div>
          <span className="text-slate-600 text-[10px] uppercase mt-2">
            Moyenne du secteur
          </span>
        </div>
      </div>

      {/* PIED DE PAGE : INDICATEUR LIVE */}
      <div className="mt-6 pt-6 border-t border-white/5 flex justify-between items-center text-xs text-slate-500">
        <div className="flex items-center gap-2">
          {/* Pastille verte qui pulse si on a des données */}
          <div
            className={`w-2 h-2 rounded-full ${estimatedPrice > 0 ? "bg-green-500 shadow-[0_0_8px_#22c55e] animate-pulse" : "bg-slate-500"}`}
          ></div>
          <span>
            {estimatedPrice > 0
              ? "Données agrégées en temps réel"
              : "En attente de signal"}
          </span>
        </div>
        <div className="font-mono opacity-50">ORACLE_DATA_V2.1</div>
      </div>
    </div>
  );
}
