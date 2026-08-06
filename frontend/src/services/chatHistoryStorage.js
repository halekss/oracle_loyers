// Persistance de l'historique du chat Immotep (ORA-117) : sessionStorage,
// pas localStorage — un refresh de page conserve l'historique, un nouvel
// onglet en repart vide (comportement natif de sessionStorage, pas de code
// dédié requis pour ce cas).
const STORAGE_KEY = 'oracle-loyers:chat-history';

export function loadChatHistory() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function saveChatHistory(messages) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  } catch {
    // Quota dépassé ou sessionStorage indisponible (navigation privée
    // stricte...) : l'historique reste en mémoire pour la session React
    // courante, seule la persistance au refresh est perdue.
  }
}
