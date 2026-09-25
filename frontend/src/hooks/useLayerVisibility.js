import { useCallback, useEffect, useState } from 'react';
import { defaultLayerVisibility } from '../services/mapLayers';
import { loadLayerVisibility, saveLayerVisibility } from '../services/mapLayersStorage';

// Visibilité des calques carte (ORA-178) : App en est l'unique source de
// vérité (composant contrôlé côté MapComponent), partagée par la vue
// "Calques" du rail ET le panneau flottant mobile. Persistée en localStorage,
// initialisée depuis `defaultVisible` (mapLayers.config.json).
export function useLayerVisibility() {
  const [layers, setLayers] = useState(() => loadLayerVisibility(defaultLayerVisibility()));

  useEffect(() => {
    saveLayerVisibility(layers);
  }, [layers]);

  const toggleLayer = useCallback((key) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const resetLayers = useCallback(() => {
    setLayers(defaultLayerVisibility());
  }, []);

  return { layers, toggleLayer, resetLayers };
}
