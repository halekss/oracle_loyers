import React, { useState } from 'react';

// ORA-111 : en dessous de ce nombre de caractères, un scan ne peut rien
// résoudre (le fuzzy matching a besoin d'un minimum de signal) — on évite
// donc un aller-retour API inutile plutôt que de le déclencher à vide.
const MIN_QUARTIER_LENGTH = 2;

export default function SearchForm({ onScan, isLoading }) {
  const [input, setInput] = useState('');
  const [surface, setSurface] = useState('');
  const [currentFilter, setCurrentFilter] = useState('Tout');

  const canScan = input.trim().length >= MIN_QUARTIER_LENGTH;

  // Soumission du formulaire (Bouton SCAN ou Entrée)
  const handleSubmit = (e) => {
    e.preventDefault();
    if (canScan) {
      onScan(input, currentFilter, surface);
    }
  };

  // Clic sur un bouton de filtre (T1, T2...)
  const handleFilterClick = (filterId) => {
    setCurrentFilter(filterId);
    // Si l'utilisateur a déjà tapé un quartier exploitable, on relance le scan immédiatement
    if (canScan) {
      onScan(input, filterId, surface);
    }
  };

  const filters = ['Tout', 'T1', 'T2', 'T3', 'T4+'];

  return (
    <div className="w-full space-y-3">
      {/* Barre de recherche */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Entrez un quartier (ex: Ainay)..."
          className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 px-4 py-3 rounded-xl focus:outline-none focus:border-purple-500 transition-colors text-sm placeholder-slate-500"
        />
        <input
          type="number"
          min="1"
          value={surface}
          onChange={(e) => setSurface(e.target.value)}
          placeholder="m²"
          aria-label="Surface en m² (pour l'estimation IA)"
          className="w-20 bg-slate-900 border border-slate-700 text-slate-200 px-3 py-3 rounded-xl focus:outline-none focus:border-purple-500 transition-colors text-sm placeholder-slate-500"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="px-5 py-3 bg-slate-800 hover:bg-slate-700 text-purple-400 font-bold rounded-xl border border-slate-700 transition-all uppercase text-xs tracking-wider disabled:opacity-50"
        >
          {isLoading ? '...' : 'SCAN'}
        </button>
      </form>

      {/* Filtres T1, T2, etc. */}
      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => handleFilterClick(f)}
            className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide border transition-all ${
              currentFilter === f
                ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-900/40' // Style Actif
                : 'bg-transparent border-slate-700 text-slate-400 hover:bg-slate-800' // Style Inactif
            }`}
          >
            {f}
          </button>
        ))}
      </div>
    </div>
  );
}