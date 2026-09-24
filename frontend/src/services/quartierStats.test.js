import { describe, expect, it } from 'vitest';
import { computeQuartierOptions } from './quartierStats';

const listings = [
  { ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.6 },
  { ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.2 },
  { ville: 'Lyon', quartier: 'Croix-Rousse Plateau', prix_m2: 22.0 },
  { ville: 'Lyon', quartier: 'Pentes Croix-Rousse', prix_m2: 19.9 },
  { ville: 'Lyon', quartier: 'Lyon / Non localisé', prix_m2: 99 },
  { ville: 'Lille', quartier: 'Vieux-Lille', prix_m2: 18.3 },
];

describe('computeQuartierOptions', () => {
  it('groups by quartier for the given ville, counting all located listings', () => {
    const options = computeQuartierOptions(listings, 'lyon');
    const ainay = options.find((o) => o.quartier === 'Ainay');
    expect(ainay.count).toBe(2);
    expect(ainay.prixM2Median).toBe(19.4);
  });

  it('excludes the "<Ville> / Non localisé" bucket', () => {
    const options = computeQuartierOptions(listings, 'lyon');
    expect(options.some((o) => o.quartier.includes('Non localisé'))).toBe(false);
  });

  it('filters by ville (case-insensitive)', () => {
    const options = computeQuartierOptions(listings, 'lille');
    expect(options).toEqual([{ quartier: 'Vieux-Lille', count: 1, prixM2Median: 18.3, arrondissement: 'Lille' }]);
  });

  it('sorts alphabetically (locale-aware, accents included)', () => {
    const options = computeQuartierOptions(listings, 'lyon');
    expect(options.map((o) => o.quartier)).toEqual(['Ainay', 'Croix-Rousse Plateau', 'Pentes Croix-Rousse']);
  });

  it('returns an empty array when nothing matches', () => {
    expect(computeQuartierOptions([], 'lyon')).toEqual([]);
    expect(computeQuartierOptions(listings, 'paris')).toEqual([]);
  });

  it('counts a listing without a usable prix_m2 without letting it skew the median', () => {
    const options = computeQuartierOptions(
      [...listings, { ville: 'Lyon', quartier: 'Ainay', prix_m2: null }],
      'lyon',
    );
    const ainay = options.find((o) => o.quartier === 'Ainay');
    expect(ainay.count).toBe(3);
    expect(ainay.prixM2Median).toBe(19.4);
  });

  describe('arrondissement (ORA-179, sous-titre des suggestions de recherche)', () => {
    it('derives "Lyon <N>e" from the most frequent code_postal of the quartier', () => {
      const options = computeQuartierOptions(
        [
          { ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.6, code_postal: 69002 },
          { ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.2, code_postal: 69002 },
          { ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.9, code_postal: 69001 },
        ],
        'lyon',
      );
      expect(options.find((o) => o.quartier === 'Ainay').arrondissement).toBe('Lyon 2e');
    });

    it('falls back to the ville name alone without a usable code_postal', () => {
      const options = computeQuartierOptions(
        [{ ville: 'Lyon', quartier: 'Ainay', prix_m2: 19.6 }],
        'lyon',
      );
      expect(options.find((o) => o.quartier === 'Ainay').arrondissement).toBe('Lyon');
    });

    it('never derives an arrondissement for Lille (no such découpage)', () => {
      const options = computeQuartierOptions(
        [{ ville: 'Lille', quartier: 'Vieux-Lille', prix_m2: 18.3, code_postal: 59000 }],
        'lille',
      );
      expect(options.find((o) => o.quartier === 'Vieux-Lille').arrondissement).toBe('Lille');
    });
  });
});
