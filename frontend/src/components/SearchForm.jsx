import React, { useState } from 'react';

export default function SearchForm({ onSearch, isLoading, currentFilter, onFilterChange }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSearch(input);
    }
  };

  const filters = [
    { id: 'all', label: 'TOUT' },
    { id: 't1', label: 'T1' },
    { id: 't2', label: 'T2' },
    { id: 't3', label: 'T3' },
    { id: 't4+', label: 'T4+' }, // ✅ Ajout du bouton ici
  ];

  return (
    <div className="w-full space-y-3">
      {/* Barre de recherche */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Adresse, quartier (ex: Ainay)..."
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
            key={f.id}
            onClick={() => onFilterChange(f.id)}
            className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wide border transition-all ${
              currentFilter === f.id
                ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-900/50'
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:bg-slate-800 hover:text-slate-300'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}