import { describe, expect, it } from 'vitest';
import { computeBoundsForQuartiers } from './mapBounds.js';

describe('computeBoundsForQuartiers', () => {
  const listings = [
    { quartier: 'Gerland', latitude: 45.72, longitude: 4.83 },
    { quartier: 'Gerland', latitude: 45.73, longitude: 4.84 },
    { quartier: 'Confluence', latitude: 45.74, longitude: 4.82 },
    { quartier: 'Vieux Lyon', latitude: 45.76, longitude: 4.83 },
  ];

  it('returns the bounding box of listings whose quartier is requested', () => {
    const bounds = computeBoundsForQuartiers(listings, ['Gerland']);

    expect(bounds).toEqual([
      [45.72, 4.83],
      [45.73, 4.84],
    ]);
  });

  it('spans across multiple matching quartiers', () => {
    const bounds = computeBoundsForQuartiers(listings, ['Gerland', 'Confluence']);

    expect(bounds).toEqual([
      [45.72, 4.82],
      [45.74, 4.84],
    ]);
  });

  it('ignores listings without exploitable coordinates', () => {
    const withMissingCoords = [
      ...listings,
      { quartier: 'Gerland', latitude: '', longitude: '' },
    ];

    const bounds = computeBoundsForQuartiers(withMissingCoords, ['Gerland']);

    expect(bounds).toEqual([
      [45.72, 4.83],
      [45.73, 4.84],
    ]);
  });

  it('returns null when no listing matches the requested quartiers', () => {
    expect(computeBoundsForQuartiers(listings, ['Quartier Inconnu'])).toBeNull();
  });

  it('returns null for an empty quartiers list', () => {
    expect(computeBoundsForQuartiers(listings, [])).toBeNull();
  });

  it('returns null when listings is empty or missing', () => {
    expect(computeBoundsForQuartiers([], ['Gerland'])).toBeNull();
    expect(computeBoundsForQuartiers(undefined, ['Gerland'])).toBeNull();
  });
});
