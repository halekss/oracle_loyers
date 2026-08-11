import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, beforeEach } from 'vitest';
import { useFavorites } from './useFavorites.js';

describe('useFavorites', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('starts with no favorites when localStorage is empty', () => {
    const { result } = renderHook(() => useFavorites());
    expect(result.current.isFavorite(1)).toBe(false);
  });

  it('toggles an id on, then off', () => {
    const { result } = renderHook(() => useFavorites());

    act(() => result.current.toggleFavorite(7));
    expect(result.current.isFavorite(7)).toBe(true);

    act(() => result.current.toggleFavorite(7));
    expect(result.current.isFavorite(7)).toBe(false);
  });

  it('persists a favorited id to localStorage immediately', () => {
    const { result } = renderHook(() => useFavorites());

    act(() => result.current.toggleFavorite(99));

    expect(JSON.parse(localStorage.getItem('oracle-loyers:favorites'))).toEqual([99]);
  });

  it('picks up a favorite persisted in localStorage from a previous "session" (reload)', () => {
    localStorage.setItem('oracle-loyers:favorites', JSON.stringify([5]));

    const { result } = renderHook(() => useFavorites());

    expect(result.current.isFavorite(5)).toBe(true);
  });

  it('survives an unmount/remount (simulated reload) of the component tree', () => {
    const first = renderHook(() => useFavorites());
    act(() => first.result.current.toggleFavorite(3));
    first.unmount();

    const second = renderHook(() => useFavorites());
    expect(second.result.current.isFavorite(3)).toBe(true);
  });

  it('keeps multiple mounted instances in sync when one toggles a favorite', () => {
    const cardInstance = renderHook(() => useFavorites());
    const listInstance = renderHook(() => useFavorites());

    act(() => cardInstance.result.current.toggleFavorite(11));

    expect(listInstance.result.current.isFavorite(11)).toBe(true);
  });

  it('ignores null/undefined ids without throwing', () => {
    const { result } = renderHook(() => useFavorites());

    expect(() => act(() => result.current.toggleFavorite(null))).not.toThrow();
    expect(() => act(() => result.current.toggleFavorite(undefined))).not.toThrow();
    expect(result.current.isFavorite(null)).toBe(false);
    expect(result.current.isFavorite(undefined)).toBe(false);
  });

  it('does not throw and behaves as a no-op (in-memory) when localStorage is unavailable', () => {
    const originalGet = Storage.prototype.getItem;
    const originalSet = Storage.prototype.setItem;
    Storage.prototype.getItem = () => {
      throw new Error('unavailable');
    };
    Storage.prototype.setItem = () => {
      throw new Error('unavailable');
    };

    const { result } = renderHook(() => useFavorites());

    expect(() => act(() => result.current.toggleFavorite(1))).not.toThrow();
    // L'état en mémoire de cette instance reste utilisable pour la session
    // courante même si l'écriture disque échoue silencieusement.
    expect(result.current.isFavorite(1)).toBe(true);

    Storage.prototype.getItem = originalGet;
    Storage.prototype.setItem = originalSet;
  });
});
