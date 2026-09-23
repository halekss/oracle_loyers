// ORA-170 : agrégations du panneau "Le marché en un coup d'œil" (écran
// d'accueil, maquette 01), calculées côté client à partir de /api/listings
// (pas de nouvel endpoint d'agrégation — cf. ORA-150, hors périmètre ici).

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

// clean_immo.py assigne un quartier "<Ville> / Non localisé" (ex. "Lyon /
// Non localisé") aux annonces sans géolocalisation fiable — la maquette 01
// les exclut explicitement des cartes ET des médianes plutôt que de les
// grouper sous un pseudo-quartier trompeur dans le classement.
function isLocated(quartier) {
  return typeof quartier === 'string' && !/non localisé/i.test(quartier);
}

// Les arrondissements lyonnais sont codés 69001-69009 (69000 = ville non
// précisée, exclu) ; Lille n'a pas ce découpage (codes de communes
// hétérogènes : 59000, 59110...) donc `groupBy` retombe sur le quartier.
function arrondissementLabel(codePostal) {
  const n = Number(codePostal);
  if (!Number.isInteger(n) || n < 69001 || n > 69009) return null;
  const numero = n - 69000;
  return numero === 1 ? '1er' : `${numero}e`;
}

function groupMedianPrixM2(items, keyFn) {
  const byKey = new Map();
  for (const item of items) {
    if (!isFiniteNumber(item.prix_m2) || item.prix_m2 <= 0) continue;
    const key = keyFn(item);
    if (!key) continue;
    if (!byKey.has(key)) byKey.set(key, []);
    byKey.get(key).push(item.prix_m2);
  }
  return [...byKey.entries()].map(([label, prixM2Values]) => ({
    label,
    prixM2Median: median(prixM2Values),
    count: prixM2Values.length,
  }));
}

// `listings` : payload brut de /api/listings (déjà filtré hors inactive
// côté backend). `ville` : 'lyon' | 'lille' (ORA-71), comparaison insensible
// à la casse car la colonne CSV porte la casse d'origine ("Lyon"/"Lille").
export function computeHomeStats(listings, ville) {
  const villeItems = (listings || []).filter(
    (item) => (item.ville || '').toLowerCase() === (ville || '').toLowerCase(),
  );
  const filtered = villeItems.filter((item) => isLocated(item.quartier));
  const excludedCount = villeItems.length - filtered.length;

  const loyerMedian = median(filtered.map((i) => i.prix).filter((p) => isFiniteNumber(p) && p > 0));
  const prixM2Median = median(filtered.map((i) => i.prix_m2).filter((p) => isFiniteNumber(p) && p > 0));

  const isLyon = (ville || '').toLowerCase() === 'lyon';
  const districtGroups = isLyon
    ? groupMedianPrixM2(filtered, (i) => arrondissementLabel(i.code_postal))
    : groupMedianPrixM2(filtered, (i) => i.quartier || null);
  districtGroups.sort((a, b) => b.prixM2Median - a.prixM2Median);

  const quartierGroups = groupMedianPrixM2(filtered, (i) => i.quartier || null);
  const byPrixM2Asc = [...quartierGroups].sort((a, b) => a.prixM2Median - b.prixM2Median);
  const byPrixM2Desc = [...quartierGroups].sort((a, b) => b.prixM2Median - a.prixM2Median);

  return {
    annoncesCount: filtered.length,
    excludedCount,
    loyerMedian,
    prixM2Median,
    districtLabel: isLyon ? 'PAR ARRONDISSEMENT' : 'PAR QUARTIER',
    districts: districtGroups,
    quartiersAbordables: byPrixM2Asc.slice(0, 3),
    quartiersChers: byPrixM2Desc.slice(0, 3),
  };
}
