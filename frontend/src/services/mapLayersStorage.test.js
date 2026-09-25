import { describe, expect, it, beforeEach } from 'vitest';
import { loadLayerVisibility, saveLayerVisibility } from './mapLayersStorage.js';

const DEFAULTS = { Vice: true, Gentrification: false, Quartiers: false };

describe('mapLayersStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns the given defaults when nothing has been saved', () => {
    expect(loadLayerVisibility(DEFAULTS)).toEqual(DEFAULTS);
  });

  it('round-trips a saved visibility map', () => {
    saveLayerVisibility({ Vice: false, Gentrification: true, Quartiers: false });
    expect(loadLayerVisibility(DEFAULTS)).toEqual({ Vice: false, Gentrification: true, Quartiers: false });
  });

  it('fills in a layer missing from the saved map with its default (new layer added to the config since)', () => {
    saveLayerVisibility({ Vice: false });
    expect(loadLayerVisibility(DEFAULTS)).toEqual({ Vice: false, Gentrification: false, Quartiers: false });
  });

  it('persists via the localStorage key (survives across "reloads")', () => {
    saveLayerVisibility({ Vice: false, Gentrification: false, Quartiers: true });
    expect(localStorage.getItem('oracle-loyers:mapLayers')).not.toBeNull();
    expect(loadLayerVisibility(DEFAULTS)).toEqual({ Vice: false, Gentrification: false, Quartiers: true });
  });

  it('returns the defaults instead of throwing when the stored value is corrupted JSON', () => {
    localStorage.setItem('oracle-loyers:mapLayers', '{not valid json');
    expect(loadLayerVisibility(DEFAULTS)).toEqual(DEFAULTS);
  });

  it('returns the defaults when the stored value is not an object', () => {
    localStorage.setItem('oracle-loyers:mapLayers', JSON.stringify([1, 2, 3]));
    expect(loadLayerVisibility(DEFAULTS)).toEqual(DEFAULTS);
  });

  it('does not throw when localStorage.getItem throws (private browsing / unavailable storage)', () => {
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error('localStorage unavailable');
    };

    expect(() => loadLayerVisibility(DEFAULTS)).not.toThrow();
    expect(loadLayerVisibility(DEFAULTS)).toEqual(DEFAULTS);

    Storage.prototype.getItem = original;
  });

  it('does not throw when localStorage.setItem throws (quota exceeded / unavailable storage)', () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error('QuotaExceededError');
    };

    expect(() => saveLayerVisibility({ Vice: true })).not.toThrow();

    Storage.prototype.setItem = original;
  });
});
