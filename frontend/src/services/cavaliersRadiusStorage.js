// Persistance du rayon choisi pour les cavaliers (vue Calques, sélecteur
// Aucun/300 m/500 m/1 km) — même schéma que mapLayersStorage.js (localStorage,
// try/catch silencieux). `null` (rayon "Aucun") est une valeur légitime à
// mémoriser, distincte de "rien n'a encore été sauvegardé".
const STORAGE_KEY = 'oracle-loyers:cavaliersRadiusM';

export function loadCavaliersRadiusM(defaultValue) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return defaultValue;
    const parsed = JSON.parse(raw);
    if (parsed === null || typeof parsed === 'number') return parsed;
    return defaultValue;
  } catch {
    return defaultValue;
  }
}

export function saveCavaliersRadiusM(radiusM) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(radiusM));
  } catch {
    // Écriture impossible (quota dépassé, navigation privée stricte...) :
    // l'état reste en mémoire pour la session React courante uniquement.
  }
}
