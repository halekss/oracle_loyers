import React, { useState } from 'react';

export default function SearchForm({ onSearch, isLoading, currentFilter, onFilterChange }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) onSearch(input);
  };

  const filters = [
    { id: 'all', label: 'Tout' },
    { id: 't1', label: 'T1' },
    { id: 't2', label: 'T2' },
    { id: 't3', label: 'T3' },
  ];

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Barre de recherche */}
      <form onSubmit={handleSubmit} className="relative w-full">
        <div className="relative flex items-center bg-slate-900 rounded-xl overflow-hidden border border-slate-700 focus-within:border-purple-500 focus-within:ring-1 focus-within:ring-purple-500/50 transition-all shadow-lg">
          <input
            type="text"
            className="w-full bg-transparent text-white px-4 py-3 outline-none placeholder-slate-600 text-sm font-medium"
            placeholder="Rue, Quartier (ex: Garibaldi)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-3 bg-slate-800 hover:bg-slate-700 text-purple-400 font-bold text-xs uppercase tracking-wider border-l border-slate-700 transition-colors hover:text-purple-300"
          >
            {isLoading ? "..." : "SCAN"}
          </button>
        </div>
      </form>

      {/* Filtres alignés */}
      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button"
            onClick={() => onFilterChange(f.id)}
            className={`
              flex-1 py-2 rounded-lg text-[10px] md:text-xs font-bold uppercase tracking-wide transition-all border
              ${currentFilter === f.id 
                ? 'bg-purple-600 border-purple-500 text-white shadow-lg shadow-purple-900/20' 
                : 'bg-slate-900 border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300'}
            `}
          >
            {f.label}
          </button>
        ))}
      </div>
    </div>
  );
}