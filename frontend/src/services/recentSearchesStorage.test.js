import { describe, expect, it, beforeEach } from 'vitest';
import { loadRecentSearches, pushRecentSearch } from './recentSearchesStorage';

describe('recentSearchesStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns an empty array when nothing has been saved', () => {
    expect(loadRecentSearches()).toEqual([]);
  });

  it('persists a pushed search and returns it on the next load', () => {
    pushRecentSearch({ quartier: 'Ainay', typeLocal: 'T2', surface: '45', ville: 'lyon' });

    expect(loadRecentSearches()).toEqual([
      { quartier: 'Ainay', typeLocal: 'T2', surface: '45', ville: 'lyon' },
    ]);
  });

  it('puts the most recent search first', () => {
    pushRecentSearch({ quartier: 'Ainay', ville: 'lyon' });
    pushRecentSearch({ quartier: 'Gerland', ville: 'lyon' });

    expect(loadRecentSearches().map((s) => s.quartier)).toEqual(['Gerland', 'Ainay']);
  });

  it('deduplicates by quartier+ville, moving the re-searched entry to the front', () => {
    pushRecentSearch({ quartier: 'Ainay', typeLocal: 'T2', ville: 'lyon' });
    pushRecentSearch({ quartier: 'Gerland', ville: 'lyon' });
    pushRecentSearch({ quartier: 'Ainay', typeLocal: 'T3', ville: 'lyon' });

    const searches = loadRecentSearches();
    expect(searches).toHaveLength(2);
    expect(searches[0]).toEqual({ quartier: 'Ainay', typeLocal: 'T3', ville: 'lyon' });
  });

  it('treats the same quartier name in a different ville as a distinct entry', () => {
    pushRecentSearch({ quartier: 'Centre', ville: 'lyon' });
    pushRecentSearch({ quartier: 'Centre', ville: 'lille' });

    expect(loadRecentSearches()).toHaveLength(2);
  });

  it('bounds the history to 5 entries, dropping the oldest', () => {
    for (let i = 0; i < 7; i++) {
      pushRecentSearch({ quartier: `Quartier ${i}`, ville: 'lyon' });
    }

    const searches = loadRecentSearches();
    expect(searches).toHaveLength(5);
    expect(searches[0].quartier).toBe('Quartier 6');
    expect(searches.map((s) => s.quartier)).not.toContain('Quartier 0');
  });

  it('ignores a push without a quartier', () => {
    pushRecentSearch({ ville: 'lyon' });
    expect(loadRecentSearches()).toEqual([]);
  });

  it('does not throw when localStorage is unavailable', () => {
    const originalSet = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error('unavailable');
    };

    expect(() => pushRecentSearch({ quartier: 'Ainay', ville: 'lyon' })).not.toThrow();

    Storage.prototype.setItem = originalSet;
  });
});
