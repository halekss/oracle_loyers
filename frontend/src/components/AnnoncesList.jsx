import { useState, useEffect } from 'react';
import AnnonceCard from './AnnonceCard';
import { api, describeApiError } from '../services/api';

// `compact` : variante utilisée dans la colonne Oracle en desktop (peu de
// place, scroll interne borné) ; en plein écran (onglet mobile "Annonces"),
// on charge une page plus large.
// `onItemsChange` (optionnel) : notifie le parent des annonces actuellement
// affichées, pour recentrer la carte sur leur bounding-box (ORA-105).
export default function AnnoncesList({ compact = false, onItemsChange }) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quartierFilter, setQuartierFilter] = useState('');
  // ORA-115 : options dérivées de /api/listings (même liste de quartiers
  // canoniques que celle écrite dans annonces.db par clean_immo.py) —
  // annonces.db n'a pas d'endpoint dédié pour lister les quartiers connus.
  const [quartierOptions, setQuartierOptions] = useState([]);

  const perPage = compact ? 4 : 12;

  useEffect(() => {
    let cancelled = false;

    api.getListings()
      .then((data) => {
        if (cancelled) return;
        const uniqueSorted = [...new Set((data || []).map((item) => item.quartier).filter(Boolean))].sort();
        setQuartierOptions(uniqueSorted);
      })
      .catch((err) => console.error("Quartiers indisponibles pour le filtre AnnoncesList :", err));

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadAnnonces() {
      setLoading(true);
      setError(null);

      try {
        const data = await api.getAnnonces({ page, perPage, quartier: quartierFilter || undefined });
        if (cancelled) return;
        setItems(data.items || []);
        setTotalPages(data.total_pages || 0);
        onItemsChange?.(data.items || []);
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        setError(describeApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadAnnonces();

    return () => {
      cancelled = true;
    };
  }, [page, perPage, quartierFilter]);

  const handleQuartierChange = (e) => {
    setQuartierFilter(e.target.value);
    setPage(1);
  };

  const filterId = compact ? 'annonces-quartier-filter-compact' : 'annonces-quartier-filter';

  const quartierFilterControl = quartierOptions.length > 0 && (
    <div className="mb-2">
      <label htmlFor={filterId} className="sr-only">Filtrer par quartier</label>
      <select
        id={filterId}
        value={quartierFilter}
        onChange={handleQuartierChange}
        className="w-full bg-slate-900 border border-slate-700 text-slate-300 text-[10px] uppercase tracking-widest font-bold px-2 py-1.5 rounded-lg focus:outline-none focus:border-purple-500"
      >
        <option value="">Tous les quartiers</option>
        {quartierOptions.map((q) => (
          <option key={q} value={q}>{q}</option>
        ))}
      </select>
    </div>
  );

  if (loading) {
    return (
      <div>
        {quartierFilterControl}
        <div className="animate-pulse grid grid-cols-2 gap-3">
          {Array.from({ length: compact ? 2 : 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-slate-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        {quartierFilterControl}
        <p className="text-xs text-red-400 font-bold bg-red-900/20 p-2 rounded border border-red-900/50">
          {error}
        </p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div>
        {quartierFilterControl}
        <p className="text-xs text-slate-500 text-center py-4">Aucune annonce disponible pour le moment.</p>
      </div>
    );
  }

  return (
    <div className={compact ? 'max-h-72 overflow-y-auto pr-1' : ''}>
      {quartierFilterControl}
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
