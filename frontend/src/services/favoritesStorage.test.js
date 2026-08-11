import { describe, expect, it, beforeEach } from 'vitest';
import { loadFavoriteIds, saveFavoriteIds } from './favoritesStorage.js';

describe('favoritesStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns an empty array when nothing has been saved', () => {
    expect(loadFavoriteIds()).toEqual([]);
  });

  it('round-trips a saved list of favorite ids', () => {
    saveFavoriteIds([1, 2, 3]);
    expect(loadFavoriteIds()).toEqual([1, 2, 3]);
  });

  it('persists via the localStorage key (survives across "reloads")', () => {
    saveFavoriteIds([42]);
    expect(localStorage.getItem('oracle-loyers:favorites')).not.toBeNull();
    // Simule un reload : relire depuis le localStorage plutôt que depuis
    // un état en mémoire.
    expect(loadFavoriteIds()).toEqual([42]);
  });

  it('returns an empty array instead of throwing when the stored value is corrupted JSON', () => {
    localStorage.setItem('oracle-loyers:favorites', '{not valid json');
    expect(loadFavoriteIds()).toEqual([]);
  });

  it('returns an empty array when the stored value is not an array', () => {
    localStorage.setItem('oracle-loyers:favorites', JSON.stringify({ not: 'an array' }));
    expect(loadFavoriteIds()).toEqual([]);
  });

  it('does not throw when localStorage.getItem throws (private browsing / unavailable storage)', () => {
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error('localStorage unavailable');
    };

    expect(() => loadFavoriteIds()).not.toThrow();
    expect(loadFavoriteIds()).toEqual([]);

    Storage.prototype.getItem = original;
  });

  it('does not throw when localStorage.setItem throws (quota exceeded / unavailable storage)', () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error('QuotaExceededError');
    };

    expect(() => saveFavoriteIds([1, 2])).not.toThrow();

    Storage.prototype.setItem = original;
  });
});
