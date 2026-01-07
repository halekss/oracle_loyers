export default function ResultCard({ data }) {
if (!data) return null;

  // Code couleur selon le score (si le backend renvoie un score de 0 à 100)
const scoreColor = data.score > 50 ? 'text-red-500' : 'text-green-400';

return (
    <div className="mt-8 max-w-md mx-auto bg-slate-800 border border-slate-700 rounded-lg p-6 shadow-2xl">
        <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-slate-200">Verdict</h2>
            <span className={`text-3xl font-black ${scoreColor}`}>
            {data.score}/100
            </span>
        </div>

    <div className="mb-6 p-4 bg-slate-900 rounded border-l-4 border-purple-500 italic text-slate-300">
        "{data.message}"
    </div>

      {/* Détails techniques (optionnel, pour debugger) */}
    <div className="text-xs text-slate-500 font-mono">
        <p>Kebabs: {data.details?.kebabs || 0}</p>
        <p>Bars: {data.details?.bars || 0}</p>
        <p>Sex-shops: {data.details?.adult_shops || 0}</p>
    </div>
    </div>
);
}