import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { CAVALIERS_RADIUS_M } from '../services/cavaliersDisplay';

// Détail des 4 cavaliers pour le rayon choisi (vue Calques, sélecteur 300 m/
// 500 m/1 km) — au rayon par défaut (500 m), reprend directement
// `defaultDetail`/`defaultFacteurs` (déjà fournis par le scan,
// /api/quartier-stats) sans appel réseau ; pour les autres rayons, appelle
// GET /api/cavaliers et met le résultat en cache (état React, pas une ref —
// lue pendant le rendu) par (quartier, rayon), pour qu'un aller-retour entre
// deux rayons déjà visités ne déclenche jamais un second appel — et donc
// jamais de skeleton pour une valeur déjà connue (pas de clignotement).
//
// Les valeurs par défaut/rayon 500m/cache sont dérivées directement au
// rendu (pas de setState pour ça dans l'effet, cf. react-hooks/
// set-state-in-effect) : l'effet ne fait que déclencher le fetch réseau
// quand c'est réellement nécessaire (cache-miss), et met à jour l'état
// uniquement depuis les callbacks (asynchrones) de la promesse.
export function useCavaliersRadius({ quartier, center, ville, radiusM, defaultDetail, defaultFacteurs }) {
  const [cache, setCache] = useState({});
  const [loadingKey, setLoadingKey] = useState(null);

  const cacheKey = quartier ? `${quartier}:${radiusM}` : null;
  const isDefaultRadius = radiusM === CAVALIERS_RADIUS_M;
  const isCacheMiss = Boolean(
    quartier && !isDefaultRadius && center && !cache[cacheKey],
  );

  useEffect(() => {
    if (!isCacheMiss) return;

    let cancelled = false;
    const request = api.getCavaliers(center.lat, center.lng, ville, radiusM);

    // Diffère le flag de chargement à un microtask plutôt que de faire un
    // setState synchrone en plein corps d'effet.
    Promise.resolve().then(() => {
      if (!cancelled) setLoadingKey(cacheKey);
    });

    request
      .then((data) => {
        if (cancelled) return;
        const next = { cavaliersDetail: data.cavaliers_detail || [], facteurs: data.facteurs || [] };
        setCache((prev) => ({ ...prev, [cacheKey]: next }));
      })
      .catch(() => {
        // Échec réseau : on ne casse pas la vue, elle retombe simplement sur
        // l'état vide pour ce rayon (rien n'est mis en cache).
      })
      .finally(() => {
        if (!cancelled) setLoadingKey((prev) => (prev === cacheKey ? null : prev));
      });

    return () => {
      cancelled = true;
    };
  }, [isCacheMiss, cacheKey, center?.lat, center?.lng, ville, radiusM]);

  if (!quartier) {
    return { cavaliersDetail: undefined, facteurs: undefined, isLoading: false };
  }
  if (isDefaultRadius) {
    return { cavaliersDetail: defaultDetail, facteurs: defaultFacteurs, isLoading: false };
  }

  const cached = cache[cacheKey];
  if (cached) {
    return { ...cached, isLoading: false };
  }
  return { cavaliersDetail: undefined, facteurs: undefined, isLoading: loadingKey === cacheKey };
}
