import { useEffect, useState } from 'react';

// ORA-172 : compteurs par calque (Vice 526, T2 300...), écrits par
// generate_map.py dans map_metadata_<ville>.json à chaque génération —
// fichier statique servi par Vite/nginx, pas un appel /api/. Extrait de
// MapComponent.jsx (panneau flottant mobile) pour être réutilisé aussi par
// le bloc "Annonces" de la vue Calques du rail (ORA-183, v3), sans dupliquer
// la logique de fetch.
export function useLayerCounts(ville) {
  const [layerCounts, setLayerCounts] = useState({});

  useEffect(() => {
    let cancelled = false;
    fetch(`/data/map_metadata_${ville}.json?t=${Date.now()}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled) setLayerCounts(data?.layer_counts || {});
      })
      .catch(() => {
        if (!cancelled) setLayerCounts({});
      });
    return () => {
      cancelled = true;
    };
  }, [ville]);

  return layerCounts;
}
