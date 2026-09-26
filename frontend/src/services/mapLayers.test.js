import { describe, expect, it } from 'vitest';
import mapLayersConfig from '../config/mapLayers.config.json';
import { defaultLayerVisibility } from './mapLayers.js';

describe('defaultLayerVisibility', () => {
  it('maps every layer key from the shared config to its defaultVisible flag', () => {
    const result = defaultLayerVisibility();

    for (const layer of mapLayersConfig) {
      expect(result[layer.key]).toBe(layer.defaultVisible);
    }
  });

  it('returns exactly one entry per configured layer, no more no less', () => {
    const result = defaultLayerVisibility();

    expect(Object.keys(result)).toHaveLength(mapLayersConfig.length);
  });
});
