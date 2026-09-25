import mapLayersConfig from '../config/mapLayers.config.json';

// ORA-178 : extrait de MapComponent.jsx (contrainte react-refresh — un
// fichier de composant ne peut exporter que des composants) pour être
// réutilisable à la fois par MapComponent (panneau flottant, mobile) et la
// vue "Calques" du rail (App.jsx, desktop) sans dupliquer le regroupement.
export const LAYER_MAPPING = Object.fromEntries(
  mapLayersConfig.map((layer) => [layer.key, layer.name])
);

export const layersByGroup = (group) => mapLayersConfig.filter((layer) => layer.group === group);

// Visibilité initiale de chaque calque (`defaultVisible`) — source unique
// réutilisée à la fois par `App` (état remonté, source de vérité) et
// `mapLayersStorage` (repli quand rien n'est encore persisté).
export const defaultLayerVisibility = () =>
  Object.fromEntries(mapLayersConfig.map((layer) => [layer.key, layer.defaultVisible]));
