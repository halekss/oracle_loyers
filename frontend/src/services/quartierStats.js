// ORA-176 : liste des quartiers connus avec leur nombre d'annonces et leur
// €/m² médian — alimente la palette de recherche (topbar) et la carte
// d'ambiguïté "Quel quartier ?" (deux suggestions avec leurs stats).
// Même source que homeStats.js (/api/listings) mais agrégation plus simple
// (pas de distinction arrondissement/quartier) : dupliquée volontairement
// plutôt que partagée, le besoin diffère (liste triée alphabétiquement,
// pas un classement par extrême).
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

// clean_immo.py assigne "<Ville> / Non localisé" aux annonces sans quartier
// fiable (cf. homeStats.js) — jamais une option de recherche valide.
function isLocated(quartier) {
  return typeof quartier === 'string' && quartier.length > 0 && !/non localisé/i.test(quartier);
}

// `listings` : payload brut de /api/listings. `ville` : 'lyon' | 'lille'.
// Renvoie [{ quartier, count, prixM2Median }], trié alphabétiquement.
export function computeQuartierOptions(listings, ville) {
  const byQuartier = new Map();
  for (const item of listings || []) {
    if ((item.ville || '').toLowerCase() !== (ville || '').toLowerCase()) continue;
    if (!isLocated(item.quartier)) continue;
    if (!byQuartier.has(item.quartier)) byQuartier.set(item.quartier, { count: 0, prixM2Values: [] });
    const entry = byQuartier.get(item.quartier);
    entry.count += 1;
    if (isFiniteNumber(item.prix_m2) && item.prix_m2 > 0) {
      entry.prixM2Values.push(item.prix_m2);
    }
  }

  const options = [...byQuartier.entries()].map(([quartier, { count, prixM2Values }]) => ({
    quartier,
    count,
    prixM2Median: median(prixM2Values),
  }));
  options.sort((a, b) => a.quartier.localeCompare(b.quartier, 'fr'));
  return options;
}
