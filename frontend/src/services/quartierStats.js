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

// ORA-179 : même dérivation que homeStats.js#arrondissementLabel (dupliquée
// volontairement, cf. note en tête de fichier) — alimente le sous-titre de
// chaque suggestion de la palette de recherche ("Lyon 2e · 31 annonces").
// Les arrondissements lyonnais sont codés 69001-69009 ; Lille n'a pas ce
// découpage (retombe sur le nom de ville seul).
function arrondissementLabel(codePostal) {
  const n = Number(codePostal);
  if (!Number.isInteger(n) || n < 69001 || n > 69009) return null;
  const numero = n - 69000;
  return numero === 1 ? '1er' : `${numero}e`;
}

function mostFrequent(values) {
  const counts = new Map();
  for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
  let best = null;
  let bestCount = 0;
  for (const [v, c] of counts) {
    if (c > bestCount) {
      best = v;
      bestCount = c;
    }
  }
  return best;
}

// `listings` : payload brut de /api/listings. `ville` : 'lyon' | 'lille'.
// Renvoie [{ quartier, count, prixM2Median, arrondissement }], trié
// alphabétiquement. `arrondissement` : "Lyon 2e" (code postal le plus
// fréquent du quartier) ou juste "Lyon"/"Lille" si non déterminable.
export function computeQuartierOptions(listings, ville) {
  const villeLabel = (ville || '').toLowerCase() === 'lille' ? 'Lille' : 'Lyon';
  const byQuartier = new Map();
  for (const item of listings || []) {
    if ((item.ville || '').toLowerCase() !== (ville || '').toLowerCase()) continue;
    if (!isLocated(item.quartier)) continue;
    if (!byQuartier.has(item.quartier)) byQuartier.set(item.quartier, { count: 0, prixM2Values: [], codePostaux: [] });
    const entry = byQuartier.get(item.quartier);
    entry.count += 1;
    if (isFiniteNumber(item.prix_m2) && item.prix_m2 > 0) {
      entry.prixM2Values.push(item.prix_m2);
    }
    if (item.code_postal != null) {
      entry.codePostaux.push(item.code_postal);
    }
  }

  const options = [...byQuartier.entries()].map(([quartier, { count, prixM2Values, codePostaux }]) => {
    const arr = arrondissementLabel(mostFrequent(codePostaux));
    return {
      quartier,
      count,
      prixM2Median: median(prixM2Values),
      arrondissement: arr ? `${villeLabel} ${arr}` : villeLabel,
    };
  });
  options.sort((a, b) => a.quartier.localeCompare(b.quartier, 'fr'));
  return options;
}
