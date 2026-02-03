import React, { useState } from 'react';

export default function SearchForm({ onScan, isLoading }) {
  const [input, setInput] = useState('');
  const [currentFilter, setCurrentFilter] = useState('Tout');

  // Soumission du formulaire (Bouton SCAN ou Entrée)
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onScan(input, currentFilter);
    }
  };

  // Clic sur un bouton de filtre (T1, T2...)
  const handleFilterClick = (filterId) => {
    setCurrentFilter(filterId);
    // Si l'utilisateur a déjà tapé un quartier, on relance le scan immédiatement
    if (input.trim()) {
      onScan(input, filterId);
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