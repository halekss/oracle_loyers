import { useState, useEffect } from 'react';
import AnnonceCard from './AnnonceCard';
import { api, describeApiError } from '../services/api';

// `compact` : variante utilisée dans la colonne Oracle en desktop (peu de
// place, scroll interne borné) ; en plein écran (onglet mobile "Annonces"),
// on charge une page plus large.
export default function AnnoncesList({ compact = false }) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const perPage = compact ? 4 : 12;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api.getAnnonces({ page, perPage })
      .then((data) => {
        if (cancelled) return;
        setItems(data.items || []);
        setTotalPages(data.total_pages || 0);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error(err);
        setError(describeApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [page, perPage]);

  if (loading) {
    return (
      <div className="animate-pulse grid grid-cols-2 gap-3">
        {Array.from({ length: compact ? 2 : 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-slate-800 rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
        {error}
      </p>
    );
  }

  if (items.length === 0) {
    return <p className="text-xs text-slate-500 text-center py-4">Aucune annonce disponible pour le moment.</p>;
  }

  return (
    <div className={compact ? 'max-h-72 overflow-y-auto pr-1' : ''}>
      <div className="grid grid-cols-2 gap-3">
        {items.map((annonce) => (
          <AnnonceCard key={annonce.id} annonce={annonce} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="mt-3 flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="text-[10px] uppercase tracking-widest font-bold text-purple-400 disabled:text-slate-700 disabled:cursor-not-allowed"
          >
            ← Précédent
          </button>
          <span className="text-[10px] text-slate-500">
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="text-[10px] uppercase tracking-widest font-bold text-purple-400 disabled:text-slate-700 disabled:cursor-not-allowed"
          >
            Suivant →
          </button>
        </div>
      )}
    </div>
  );
}
