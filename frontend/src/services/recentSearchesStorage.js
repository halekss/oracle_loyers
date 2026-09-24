// ORA-176 : historique des recherches de quartier (palette topbar, maquette
// 08 — "Ainay · T2 · 45 m²"), localStorage comme les favoris (ORA-132) : doit
// survivre à un refresh/à la fermeture de l'onglet, pas seulement à la
// session (contrairement à l'historique du chat, sessionStorage — ORA-117).
const STORAGE_KEY = 'oracle-loyers:recent-searches';
const MAX_ENTRIES = 5;

export function loadRecentSearches() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // localStorage indisponible (navigation privée stricte...) ou valeur
    // stockée corrompue : liste vide plutôt qu'un crash.
    return [];
  }
}

// `entry` : { quartier, typeLocal, surface, ville }. Dédupliquée par
// quartier+ville (un nouveau scan du même quartier remonte en tête plutôt
// que de créer un doublon), bornée à MAX_ENTRIES (les plus anciennes
// disparaissent silencieusement, pas de UI de gestion dédiée).
export function pushRecentSearch(entry) {
  if (!entry?.quartier) return loadRecentSearches();

  const current = loadRecentSearches();
  const deduped = current.filter(
    (item) => !(item.quartier === entry.quartier && item.ville === entry.ville),
  );
  const next = [entry, ...deduped].slice(0, MAX_ENTRIES);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // Écriture impossible (quota dépassé...) : la liste en mémoire reste
    // utilisable pour la session React courante, perdue au refresh.
  }
  return next;
}
