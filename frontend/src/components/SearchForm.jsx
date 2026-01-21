import React, { useState } from 'react';

export default function SearchForm({ onSearch, isLoading, currentFilter, onFilterChange }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim()) {
      onSearch(input);
    }
  };

  // Les filtres avec des ICONES
  const filters = [
    { id: 'all', label: 'Tout', icon: '🌍' },
    { id: 't1', label: 'Studio/T1', icon: '🛋️' },
    { id: 't2', label: 'T2', icon: '🛏️' },
    { id: 't3', label: 'T3', icon: '👨‍👩‍👧' },
    { id: 't4+', label: 'Grand (T4+)', icon: '🏰' },
  ];

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in-down">
      
      {/* 1. BARRE DE RECHERCHE */}
      <form onSubmit={handleSubmit} className="relative w-full group z-20">
        {/* Glow effect derrière la barre */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 rounded-xl blur opacity-30 group-hover:opacity-100 transition duration-500"></div>
        
        <div className="relative flex items-center bg-slate-900 rounded-lg overflow-hidden border border-slate-700 shadow-2xl">
          <span className="pl-4 text-2xl">📍</span>
          <input
            type="text"
            className="w-full bg-transparent text-white px-4 py-4 outline-none placeholder-slate-500 font-medium tracking-wide text-lg"
            placeholder="Quelle zone analyser ? (ex: Part-Dieu)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          
          <button
            type="submit"
            disabled={isLoading}
            className="px-8 py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold transition-all border-l border-slate-700 hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-sm"
          >
            {isLoading ? <span className="animate-spin block">↻</span> : "SCANNER"}
          </button>
        </div>
      </form>

      {/* 2. FILTRES ICONES (Boutons magiques) */}
      <div className="flex flex-wrap justify-center gap-3">
        {filters.map((f) => (
          <button
            key={f.id}
            type="button" // Important pour ne pas soumettre le formulaire
            onClick={() => onFilterChange(f.id)}
            className={`
              flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-bold transition-all duration-300 border
              ${currentFilter === f.id 
                ? 'bg-blue-600 border-blue-400 text-white shadow-[0_0_20px_rgba(37,99,235,0.6)] scale-105' 
                : 'bg-slate-900/40 border-slate-700 text-slate-400 hover:bg-slate-800 hover:border-slate-500 hover:text-white'}
            `}
          >
            <span className="text-xl">{f.icon}</span>
            <span>{f.label}</span>
          </button>
        ))}
      </div>

    </div>
  );
}