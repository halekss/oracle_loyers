// ORA-190 : médiane ville (même type de bien) pour le bar chart du panneau
// "Estimation personnalisée" — troisième repère à côté de l'estimation du
// modèle et de la médiane du quartier (déjà fournie par /api/quartier-stats,
// prixStats). Calculée côté client à partir de /api/listings (déjà chargé
// par App.jsx pour la carte et l'accueil), pas de nouvel endpoint — même
// approche que homeStats.js/quartierStats.js (médiane dupliquée
// volontairement, cf. leurs notes en tête de fichier : le besoin diffère à
// chaque fois, pas la peine de partager un module pour 6 lignes).
function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;
  if (n === 0) return null;
  const mid = Math.floor(n / 2);
  return n % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

// `listings` : payload brut de /api/listings. `ville` : 'lyon' | 'lille'.
// `typeLocal` : catégorie exacte du scan ('Studio/T1', 'T2', 'T3', 'Grand
// (T4+)') — comparer un studio à la médiane ville tous types confondus
// serait trompeur (gammes de prix différentes, cf. AnnoncesList.jsx).
export function computeVilleMedianPrice(listings, ville, typeLocal) {
  const prices = (listings || [])
    .filter((item) => (item.ville || '').toLowerCase() === (ville || '').toLowerCase())
    .filter((item) => item.type_local === typeLocal)
    .map((item) => item.prix)
    .filter((p) => isFiniteNumber(p) && p > 0);
  return median(prices);
}
