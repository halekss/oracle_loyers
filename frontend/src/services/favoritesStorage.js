// Persistance des favoris (ORA-132) : localStorage, contrairement à
// l'historique du chat qui utilise sessionStorage (ORA-117) - un favori doit
// survivre à un refresh ET à la fermeture de l'onglet/navigateur, c'est
// l'intérêt même d'une liste de favoris.
//
// Décision de cadrage produit (ORA-132) : l'app n'a aujourd'hui aucune
// notion de compte/session persistante (pas d'auth, pas de backend user).
// Le ticket proposait deux options : localStorage simple, ou comptes
// utilisateurs (nécessitant un système d'auth complet, hors périmètre
// actuel). On implémente l'option localStorage, la plus légère et la seule
// cohérente avec l'architecture actuelle de l'app.
const STORAGE_KEY = 'oracle-loyers:favorites';

export function loadFavoriteIds() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    // localStorage indisponible (navigation privée stricte...) ou valeur
    // stockée corrompue : on démarre avec une liste vide plutôt que de
    // faire planter l'app.
    return [];
  }
}

export function saveFavoriteIds(ids) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Écriture impossible (quota dépassé, navigation privée stricte qui
    // désactive localStorage...) : les favoris restent en mémoire pour la
    // session React courante uniquement (perdus au refresh), sans jamais
    // faire planter l'app.
  }
}
