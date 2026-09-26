import { describe, expect, it } from 'vitest';
import { cavalierMeta, defaultExpandedCategory } from './cavaliersDisplay.js';

describe('cavalierMeta', () => {
  it('returns the total and the minimum distance among items when the category has lieux', () => {
    const cat = {
      categorie: 'Vice',
      total: 19,
      items: [
        { poi: 'Bar', count: 12, dist_m: 46 },
        { poi: 'Tabac', count: 3, dist_m: 158 },
        { poi: 'Cbd shop', count: 2, dist_m: 159 },
        { poi: 'Kebab', count: 2, dist_m: 54 },
      ],
      empty_message: null,
    };

    expect(cavalierMeta(cat)).toEqual({ count: 19, distM: 46 });
  });

  it('ignores items without a distance when computing the minimum', () => {
    const cat = {
      categorie: 'Vice',
      total: 5,
      items: [
        { poi: 'Bar', count: 5, dist_m: null },
        { poi: 'Tabac', count: 3, dist_m: 200 },
      ],
      empty_message: null,
    };

    expect(cavalierMeta(cat)).toEqual({ count: 5, distM: 200 });
  });

  it('parses the closest distance out of empty_message when the category is empty', () => {
    const cat = {
      categorie: 'Superstition',
      total: 0,
      items: [],
      empty_message: 'Rien dans le rayon. Pompes funèbres les plus proches à 573 m.',
    };

    expect(cavalierMeta(cat)).toEqual({ count: 0, distM: 573 });
  });

  it('returns a null distance when empty_message carries no distance at all', () => {
    const cat = { categorie: 'Superstition', total: 0, items: [], empty_message: 'Rien dans le rayon.' };

    expect(cavalierMeta(cat)).toEqual({ count: 0, distM: null });
  });

  it('returns null for a missing category', () => {
    expect(cavalierMeta(null)).toBeNull();
    expect(cavalierMeta(undefined)).toBeNull();
  });
});

describe('defaultExpandedCategory', () => {
  it('picks the category with the most lieux', () => {
    const detail = [
      { categorie: 'Vice', total: 19 },
      { categorie: 'Gentrification', total: 24 },
      { categorie: 'Nuisance', total: 21 },
      { categorie: 'Superstition', total: 0 },
    ];

    expect(defaultExpandedCategory(detail)).toBe('Gentrification');
  });

  it('returns null when there is no detail (no scan yet)', () => {
    expect(defaultExpandedCategory(null)).toBeNull();
    expect(defaultExpandedCategory([])).toBeNull();
  });

  it('returns the only category when there is a single one', () => {
    expect(defaultExpandedCategory([{ categorie: 'Vice', total: 3 }])).toBe('Vice');
  });
});
