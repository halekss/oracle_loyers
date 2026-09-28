import { describe, expect, it } from 'vitest';
import { computeVilleMedianPrice } from './estimationChart';

const listings = [
  { ville: 'Lyon', type_local: 'T2', prix: 700 },
  { ville: 'Lyon', type_local: 'T2', prix: 900 },
  { ville: 'Lyon', type_local: 'T2', prix: 1100 },
  { ville: 'Lyon', type_local: 'Studio/T1', prix: 500 },
  { ville: 'Lille', type_local: 'T2', prix: 600 },
];

describe('computeVilleMedianPrice', () => {
  it('computes the median price for the given ville and type', () => {
    expect(computeVilleMedianPrice(listings, 'lyon', 'T2')).toBe(900);
  });

  it('is case-insensitive on ville', () => {
    expect(computeVilleMedianPrice(listings, 'Lyon', 'T2')).toBe(900);
  });

  it('excludes other types and other villes', () => {
    expect(computeVilleMedianPrice(listings, 'lyon', 'Studio/T1')).toBe(500);
    expect(computeVilleMedianPrice(listings, 'lille', 'T2')).toBe(600);
  });

  it('ignores non-finite or non-positive prices', () => {
    const dirty = [
      { ville: 'Lyon', type_local: 'T2', prix: 800 },
      { ville: 'Lyon', type_local: 'T2', prix: 0 },
      { ville: 'Lyon', type_local: 'T2', prix: NaN },
      { ville: 'Lyon', type_local: 'T2', prix: null },
    ];
    expect(computeVilleMedianPrice(dirty, 'lyon', 'T2')).toBe(800);
  });

  it('returns null when there is no matching listing', () => {
    expect(computeVilleMedianPrice(listings, 'lyon', 'Grand (T4+)')).toBeNull();
  });

  it('returns null for an empty or missing listings array', () => {
    expect(computeVilleMedianPrice([], 'lyon', 'T2')).toBeNull();
    expect(computeVilleMedianPrice(undefined, 'lyon', 'T2')).toBeNull();
  });
});
