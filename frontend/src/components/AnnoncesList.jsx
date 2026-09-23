import { useState, useEffect } from 'react';
import AnnonceCard from './AnnonceCard';
import { api, describeApiError } from '../services/api';
import { useFavorites } from '../hooks/useFavorites';
import { getTypeCategory } from '../services/annonceType';

// ORA-127 : options de tri exposées à l'utilisateur (label FR + clé/ordre
// envoyés au backend, qui trie côté SQL avant de paginer — cf. api.getAnnonces).
// ORA-173 (maquette 05) : "€/m² croissant" est le tri par défaut (premier de
// la liste, cf. `sortValue` initial ci-dessous) ; "Meilleures affaires" s'appuie
// sur le même tri serveur (prix_m2 asc — pas de médiane par annonce stockée
// en base) puis, quand un quartier est scanné (`referencePrixM2` fourni),
// réordonne la page reçue par écart croissant au lieu du simple €/m².
const SORT_OPTIONS = [
  { value: 'prix_m2-asc', label: '€/m² croissant', sort: 'prix_m2', order: 'asc' },
  { value: 'meilleures-affaires', label: 'Meilleures affaires', sort: 'prix_m2', order: 'asc' },
  { value: '', label: 'Plus récentes', sort: undefined, order: undefined },
  { value: 'prix-asc', label: 'Prix croissant', sort: 'prix', order: 'asc' },
  { value: 'prix-desc', label: 'Prix décroissant', sort: 'prix', order: 'desc' },
  { value: 'surface-asc', label: 'Surface croissante', sort: 'surface', order: 'asc' },
  { value: 'surface-desc', label: 'Surface décroissante', sort: 'surface', order: 'desc' },
  { value: 'date-asc', label: 'Plus anciennes', sort: 'date', order: 'asc' },
  { value: 'date-desc', label: 'Plus récentes en premier', sort: 'date', order: 'desc' },
];

// `compact` : variante utilisée dans la colonne Oracle en desktop (peu de
// place, scroll interne borné) ; en plein écran (onglet mobile "Annonces"),
// on charge une page plus large.
// `onItemsChange` (optionnel) : notifie le parent des annonces actuellement
// affichées, pour recentrer la carte sur leur bounding-box (ORA-105).
// `focusedQuartier` (optionnel, ORA-127) : `{ quartier, token }` fourni par
// le parent (ex. après un scan de quartier) pour présélectionner le filtre
// quartier et sauter directement sur ses annonces. `token` doit changer à
// chaque nouvelle demande (même quartier scanné deux fois de suite compris)
// pour redéclencher le saut.
// `referencePrixM2`/`referenceType` (optionnels, ORA-173) : €/m² moyen et
// type_local du quartier scanné (App.jsx, `result.quartierPrixM2`/`result.type`)
// — alimentent le badge d'écart de chaque AnnonceCard et le tri "Meilleures
// affaires" ci-dessous. `referenceType` évite de comparer un T4+ à une
// référence calculée pour des T2 (gammes de prix différentes).
export default function AnnoncesList({ compact = false, onItemsChange, focusedQuartier, referencePrixM2, referenceType }) {
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quartierFilter, setQuartierFilter] = useState('');
  const [sortValue, setSortValue] = useState('prix_m2-asc');
  // ORA-115 : options dérivées de /api/listings (même liste de quartiers
  // canoniques que celle écrite dans annonces.db par clean_immo.py) —
  // annonces.db n'a pas d'endpoint dédié pour lister les quartiers connus.
  const [quartierOptions, setQuartierOptions] = useState([]);
  // ORA-132 : filtre additif "Mes favoris" — n'affecte ni le tri, ni la
  // pagination/le fetch (filtre client-side sur la page déjà chargée).
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const { isFavorite, favoriteIds } = useFavorites();

  const perPage = compact ? 4 : 12;
  const activeSort = SORT_OPTIONS.find((opt) => opt.value === sortValue) || SORT_OPTIONS[0];

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

  // ORA-127 : saute directement sur les annonces du quartier scanné quand le
  // parent le demande (nouveau `token`), même si `quartier` est identique au
  // filtre déjà actif (ex. deux scans successifs du même quartier).
  useEffect(() => {
    if (!focusedQuartier?.quartier) return;
    setQuartierFilter(focusedQuartier.quartier);
    setPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedQuartier?.token]);

  useEffect(() => {
    let cancelled = false;

    async function loadAnnonces() {
      setLoading(true);
      setError(null);

      try {
        const data = await api.getAnnonces({
          page,
          perPage,
          quartier: quartierFilter || undefined,
          sort: activeSort.sort,
          order: activeSort.order,
        });
        if (cancelled) return;
        setItems(data.items || []);
        setTotal(data.total || 0);
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
  }, [page, perPage, quartierFilter, activeSort.sort, activeSort.order]);

  const handleQuartierChange = (e) => {
    setQuartierFilter(e.target.value);
    setPage(1);
  };

  const handleSortChange = (e) => {
    setSortValue(e.target.value);
    setPage(1);
  };

  const filterId = compact ? 'annonces-quartier-filter-compact' : 'annonces-quartier-filter';
  const sortId = compact ? 'annonces-sort-compact' : 'annonces-sort';

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

  // ORA-127 : contrôle de tri, toujours affiché (indépendant des quartiers
  // connus contrairement au filtre ci-dessus).
  const sortControl = (
    <div className="mb-2">
      <label htmlFor={sortId} className="sr-only">Trier les annonces</label>
      <select
        id={sortId}
        value={sortValue}
        onChange={handleSortChange}
        className="w-full bg-slate-900 border border-slate-700 text-slate-300 text-[10px] uppercase tracking-widest font-bold px-2 py-1.5 rounded-lg focus:outline-none focus:border-purple-500"
      >
        {SORT_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );

  // ORA-132 : bascule "Toutes" / "Mes favoris", additive au filtre quartier
  // et au tri existants — ne modifie ni le tri, ni le fetch paginé.
  const favoritesToggleControl = (
    <div className="mb-2 flex items-center gap-2" role="tablist" aria-label="Filtrer les annonces">
      <button
        type="button"
        role="tab"
        aria-selected={!showFavoritesOnly}
        onClick={() => setShowFavoritesOnly(false)}
        className={`text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded-lg border transition-colors ${
          !showFavoritesOnly
            ? 'bg-purple-900/40 text-purple-300 border-purple-700/50'
            : 'text-slate-500 border-slate-700 hover:text-slate-300'
        }`}
      >
        Toutes · {total}
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={showFavoritesOnly}
        onClick={() => setShowFavoritesOnly(true)}
        className={`text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded-lg border transition-colors ${
          showFavoritesOnly
            ? 'bg-purple-900/40 text-purple-300 border-purple-700/50'
            : 'text-slate-500 border-slate-700 hover:text-slate-300'
        }`}
      >
        ★ Mes favoris · {favoriteIds.size}
      </button>
    </div>
  );

  if (loading) {
    return (
      <div>
        {quartierFilterControl}
        {sortControl}
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
        {sortControl}
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
        {sortControl}
        <p className="text-xs text-slate-500 text-center py-4">Aucune annonce disponible pour le moment.</p>
      </div>
    );
  }

  const favoriteFiltered = showFavoritesOnly ? items.filter((annonce) => isFavorite(annonce.id)) : items;

  // ORA-173 : "Meilleures affaires" — le tri serveur (prix_m2 asc) est déjà
  // une bonne approximation ; avec une référence quartier disponible (scan en
  // cours), on affine par écart croissant plutôt que par €/m² brut, pour un
  // classement qui tient compte du niveau de prix propre au quartier. Ne
  // classe que les annonces du même type que la référence (sinon un T4+ moins
  // cher au m² qu'un T2 remonterait en tête pour une raison trompeuse) ; les
  // autres types restent en fin de liste, à leur ordre de tri serveur.
  const displayedItems =
    sortValue === 'meilleures-affaires' && Number.isFinite(referencePrixM2) && referencePrixM2 > 0
      ? [...favoriteFiltered].sort((a, b) => {
          const ecart = (item) => {
            if (referenceType && referenceType !== 'Tout' && getTypeCategory(item.titre, item.surface) !== referenceType) return Infinity;
            return Number.isFinite(item.prix) && Number.isFinite(item.surface) && item.surface > 0
              ? (item.prix / item.surface - referencePrixM2) / referencePrixM2
              : Infinity;
          };
          return ecart(a) - ecart(b);
        })
      : favoriteFiltered;

  return (
    <div className={compact ? 'max-h-72 overflow-y-auto pr-1' : ''}>
      {quartierFilterControl}
      {sortControl}
      {favoritesToggleControl}
      {displayedItems.length === 0 ? (
        <p className="text-xs text-slate-500 text-center py-4">
          Aucun favori pour le moment sur cette page.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {displayedItems.map((annonce) => (
            <AnnonceCard key={annonce.id} annonce={annonce} referencePrixM2={referencePrixM2} referenceType={referenceType} />
          ))}
        </div>
      )}

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
