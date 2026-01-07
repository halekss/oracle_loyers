import { useState } from 'react';

export default function SearchForm({ onSearch, isLoading }) {
const [address, setAddress] = useState('');

const handleSubmit = (e) => {
    e.preventDefault();
    if (address.trim()) onSearch(address);
};

return (
    <div className="w-full max-w-md mx-auto p-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <label className="text-sm font-bold text-purple-400 uppercase tracking-widest">
            Interrogez l'Oracle
        </label>
        <div className="flex gap-2">
            <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Ex: 15 rue de la République, Lyon"
            className="flex-1 p-3 rounded bg-slate-800 border border-slate-700 focus:border-purple-500 focus:outline-none text-white transition-colors"
            disabled={isLoading}
            />
            <button
                type="submit"
                disabled={isLoading}
                className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
            {isLoading ? '...' : 'Juger'}
            </button>
        </div>
        </form>
    </div>
);
}