import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, beforeEach } from 'vitest';
import { useLayerVisibility } from './useLayerVisibility.js';
import { defaultLayerVisibility } from '../services/mapLayers.js';

describe('useLayerVisibility', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts from defaultVisible (mapLayers.config.json) when nothing is persisted', () => {
    const { result } = renderHook(() => useLayerVisibility());
    expect(result.current.layers).toEqual(defaultLayerVisibility());
  });

  it('toggling a key flips only that key', () => {
    const { result } = renderHook(() => useLayerVisibility());
    const before = result.current.layers.Vice;

    act(() => result.current.toggleLayer('Vice'));

    expect(result.current.layers.Vice).toBe(!before);
    expect(result.current.layers.Gentrification).toBe(defaultLayerVisibility().Gentrification);
  });

  it('persists a toggle to localStorage immediately', () => {
    const { result } = renderHook(() => useLayerVisibility());

    act(() => result.current.toggleLayer('Quartiers'));

    const stored = JSON.parse(localStorage.getItem('oracle-loyers:mapLayers'));
    expect(stored.Quartiers).toBe(true);
  });

  it('picks up a visibility map persisted in a previous "session" (reload)', () => {
    localStorage.setItem('oracle-loyers:mapLayers', JSON.stringify({ ...defaultLayerVisibility(), Vice: false }));

    const { result } = renderHook(() => useLayerVisibility());

    expect(result.current.layers.Vice).toBe(false);
  });

  it('resetLayers restores defaultVisible, even overriding a persisted custom state', () => {
    localStorage.setItem('oracle-loyers:mapLayers', JSON.stringify({ ...defaultLayerVisibility(), Vice: false, Quartiers: true }));
    const { result } = renderHook(() => useLayerVisibility());
    expect(result.current.layers).not.toEqual(defaultLayerVisibility());

    act(() => result.current.resetLayers());

    expect(result.current.layers).toEqual(defaultLayerVisibility());
  });

  it('does not throw when localStorage is unavailable', () => {
    const originalGet = Storage.prototype.getItem;
    const originalSet = Storage.prototype.setItem;
    Storage.prototype.getItem = () => {
      throw new Error('unavailable');
    };
    Storage.prototype.setItem = () => {
      throw new Error('unavailable');
    };

    const { result } = renderHook(() => useLayerVisibility());

    expect(() => act(() => result.current.toggleLayer('Vice'))).not.toThrow();

    Storage.prototype.getItem = originalGet;
    Storage.prototype.setItem = originalSet;
  });
});
