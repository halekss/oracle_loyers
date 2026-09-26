// Persistance de la visibilité des calques carte : même schéma que
// favoritesStorage.js (localStorage, try/catch silencieux). `defaults` est
// toujours fourni par l'appelant (defaultLayerVisibility()) plutôt que codé
// ici, pour qu'un calque ajouté depuis mapLayers.config.json après la
// dernière sauvegarde récupère bien son `defaultVisible` au lieu de
// disparaître silencieusement de l'état.
const STORAGE_KEY = 'oracle-loyers:mapLayers';

export function loadLayerVisibility(defaults) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...defaults };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return { ...defaults };
    return { ...defaults, ...parsed };
  } catch {
    return { ...defaults };
  }
}

export function saveLayerVisibility(layers) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layers));
  } catch {
    // Écriture impossible (quota dépassé, navigation privée stricte...) :
    // l'état reste en mémoire pour la session React courante uniquement.
  }
}
