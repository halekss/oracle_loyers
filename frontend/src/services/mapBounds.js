// Calcule la bounding-box Leaflet ([[latMin, lngMin], [latMax, lngMax]]) des
// `listings` (payload /api/listings) dont le quartier figure dans
// `quartiers` (ORA-105 : recentrage carte sur les résultats filtrés).
// Renvoie null si aucun point exploitable n'est trouvé — le composant carte
// doit alors retomber sur le centre-ville plutôt que sur une bounding-box vide.
export function computeBoundsForQuartiers(listings, quartiers) {
  const quartierSet = new Set(quartiers || []);
  if (quartierSet.size === 0) return null;

  const points = (listings || []).filter(
    (item) =>
      quartierSet.has(item.quartier) &&
      Number.isFinite(item.latitude) &&
      Number.isFinite(item.longitude),
  );

  if (points.length === 0) return null;

  const lats = points.map((p) => p.latitude);
  const lngs = points.map((p) => p.longitude);

  return [
    [Math.min(...lats), Math.min(...lngs)],
    [Math.max(...lats), Math.max(...lngs)],
  ];
}
