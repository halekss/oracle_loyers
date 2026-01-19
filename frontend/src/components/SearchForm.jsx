import { useState } from 'react';

export default function SearchForm({ onSearch, isLoading }) {
  const [address, setAddress] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (address.trim()) onSearch(address);
  };

  return (
    <div className="w-full max-w-2xl mx-auto relative z-10">
      <form onSubmit={handleSubmit} className="flex flex-col md:flex-row gap-4 relative">
        
        {/* INPUT : Fond semi-transparent et bordure lumineuse au focus */}
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Entrez une adresse (ex: 15 rue de la République...)"
          className="flex-1 p-4 rounded-xl bg-slate-900/60 backdrop-blur-md border border-slate-700/50 focus:border-purple-500 focus:ring-4 focus:ring-purple-500/20 focus:outline-none text-white placeholder-slate-400 transition-all duration-300 shadow-xl"
          disabled={isLoading}
        />
        
        {/* BOUTON : Dégradé violet/rose */}
        <button
          type="submit"
          disabled={isLoading || !address.trim()}
          className="px-8 py-4 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-bold rounded-xl transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 shadow-lg shadow-purple-900/40 whitespace-nowrap"
        >
          {isLoading ? 'Analyse...' : 'Juger'}
        </button>
      </form>
      
      <p className="text-xs text-purple-300/50 mt-3 ml-2 tracking-[0.2em] uppercase font-semibold">
        Interrogez l'Oracle
      </p>
    </div>
  );
}