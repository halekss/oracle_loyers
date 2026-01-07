import { useEffect, useState } from 'react';

// Petit composant interne pour une barre de progression
const StatGauge = ({ label, value, color }) => (
  <div className="mb-3 group">
    <div className="flex justify-between text-[10px] uppercase font-bold tracking-widest text-slate-400 mb-1 group-hover:text-white transition-colors">
      <span>{label}</span>
      <span>{value}/100</span>
    </div>
    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden border border-slate-700">
      <div 
        className={`h-full transition-all duration-1000 ease-out ${color} shadow-[0_0_10px_currentColor]`} 
        style={{ width: `${value}%` }}
      ></div>
    </div>
  </div>
);

export default function ResultCard({ data }) {
  // Animation du score au chargement
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    // Petit effet de "compteur" qui monte
    let start = 0;
    const end = data.score || 0;
    if (start === end) return;

    const duration = 1000;
    const increment = end / (duration / 16); // 60fps

    const timer = setInterval(() => {
      start += increment;
      if (start >= end) {
        setDisplayScore(end);
        clearInterval(timer);
      } else {
        setDisplayScore(Math.floor(start));
      }
    }, 16);

    return () => clearInterval(timer);
  }, [data.score]);

  // Calcul de la couleur du score
  const getScoreColor = (s) => {
    if (s < 30) return "text-green-400 border-green-500/30 shadow-green-900/20"; // Calme
    if (s < 60) return "text-yellow-400 border-yellow-500/30 shadow-yellow-900/20"; // Vivant
    return "text-red-500 border-red-500/30 shadow-red-900/20"; // L'Enfer
  };

  // Sécurisation des données (si le backend renvoie rien)
  const stats = data.details || {};
  
  // Normalisation des valeurs pour les jauges (0-100)
  // On multiplie un peu arbitrairement pour remplir la barre
  const kebabScore = Math.min((stats.kebabs || 0) * 10, 100);
  const barScore = Math.min((stats.bars || 0) * 8, 100);
  const viceScore = Math.min((stats.adult_shops || 0) * 50, 100);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-purple-500/20 rounded-3xl p-6 shadow-2xl relative overflow-hidden w-full">
      
      {/* Bandeau décoratif "Analyse terminée" */}
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50"></div>

      <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
        
        {/* BLOC GAUCHE : SCORE */}
        <div className="flex flex-col items-center">
          <div className={`w-24 h-24 rounded-full border-4 flex items-center justify-center bg-slate-950/50 backdrop-blur-sm shadow-xl ${getScoreColor(displayScore)} transition-colors duration-500`}>
            <span className="text-4xl font-black">{displayScore}</span>
          </div>
          <span className="mt-2 text-[10px] uppercase tracking-widest text-slate-500 font-bold">
            Indice de Vice
          </span>
        </div>

        {/* BLOC DROITE : INFOS */}
        <div className="flex-1 w-full space-y-4">
          
          {/* Le verdict textuel */}
          <div className="bg-slate-950/50 p-3 rounded-xl border border-white/5">
             <p className="text-sm italic text-purple-200 leading-relaxed text-center md:text-left">
               "{data.message || "L'Oracle reste muet..."}"
             </p>
          </div>

          {/* Les Jauges */}
          <div className="space-y-1 pt-2">
            <StatGauge label="Risque Cardiovasculaire (Kebabs)" value={kebabScore} color="bg-yellow-500" />
            <StatGauge label="Nuisance Sonore (Bars)" value={barScore} color="bg-orange-500" />
            <StatGauge label="Indice Glauque (Sex-shops)" value={viceScore} color="bg-purple-600" />
          </div>

          {/* Faux Prix Estimé (En attendant P2) */}
          <div className="pt-4 border-t border-white/5 flex justify-between items-end">
            <div className="text-xs text-slate-500">Loyer Estimé (T2)</div>
            <div className="text-2xl font-mono font-bold text-white">
               {/* Génération d'un faux prix basé sur le score pour le fun */}
               {850 + (data.score * 2)} € <span className="text-xs text-slate-600 font-normal">/mois</span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}