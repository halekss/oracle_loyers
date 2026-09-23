import { describe, expect, it } from 'vitest';
import { computeHomeStats } from './homeStats';

const listings = [
  { ville: 'Lyon', quartier: 'Ainay', code_postal: 69002, prix: 900, prix_m2: 20 },
  { ville: 'Lyon', quartier: 'Ainay', code_postal: 69002, prix: 1100, prix_m2: 22 },
  { ville: 'Lyon', quartier: 'Montchat', code_postal: 69003, prix: 700, prix_m2: 15 },
  { ville: 'Lyon', quartier: 'Montchat', code_postal: 69003, prix: 750, prix_m2: 16 },
  { ville: 'Lyon', quartier: 'Gerland', code_postal: 69007, prix: 1300, prix_m2: 28 },
  { ville: 'Lille', quartier: 'Vieux-Lille', code_postal: 59000, prix: 850, prix_m2: 19 },
];

describe('computeHomeStats', () => {
  it('filters by ville (case-insensitive)', () => {
    const stats = computeHomeStats(listings, 'lyon');
    expect(stats.annoncesCount).toBe(5);
  });

  it('computes the median loyer and prix_m2 for the ville', () => {
    const stats = computeHomeStats(listings, 'lyon');
    expect(stats.loyerMedian).toBe(900);
    expect(stats.prixM2Median).toBe(20);
  });

  it('groups Lyon by arrondissement label (69002 -> "2e", 69001 -> "1er")', () => {
    const stats = computeHomeStats(listings, 'lyon');
    const labels = stats.districts.map((d) => d.label).sort();
    expect(labels).toEqual(['2e', '3e', '7e']);
    expect(stats.districtLabel).toBe('PAR ARRONDISSEMENT');
  });

  it('sorts districts by descending median prix_m2', () => {
    const stats = computeHomeStats(listings, 'lyon');
    expect(stats.districts[0].label).toBe('7e');
    expect(stats.districts.at(-1).label).toBe('3e');
  });

  it('falls back to grouping by quartier for a ville without arrondissement codes (Lille)', () => {
    const stats = computeHomeStats(listings, 'lille');
    expect(stats.districtLabel).toBe('PAR QUARTIER');
    expect(stats.districts).toEqual([{ label: 'Vieux-Lille', prixM2Median: 19, count: 1 }]);
  });

  it('ranks the 3 cheapest and most expensive quartiers by median prix_m2', () => {
    const stats = computeHomeStats(listings, 'lyon');
    expect(stats.quartiersAbordables.map((q) => q.label)).toEqual(['Montchat', 'Ainay', 'Gerland']);
    expect(stats.quartiersChers.map((q) => q.label)).toEqual(['Gerland', 'Ainay', 'Montchat']);
  });

  it('ignores listings with a non-finite or non-positive prix/prix_m2', () => {
    const stats = computeHomeStats(
      [...listings, { ville: 'Lyon', quartier: 'Ainay', code_postal: 69002, prix: NaN, prix_m2: -1 }],
      'lyon',
    );
    expect(stats.annoncesCount).toBe(6);
    expect(stats.loyerMedian).toBe(900);
  });

  it('returns an empty-safe shape when there is no listing for the ville', () => {
    const stats = computeHomeStats([], 'lyon');
    expect(stats).toEqual({
      annoncesCount: 0,
      excludedCount: 0,
      loyerMedian: null,
      prixM2Median: null,
      districtLabel: 'PAR ARRONDISSEMENT',
      districts: [],
      quartiersAbordables: [],
      quartiersChers: [],
    });
  });

  it('excludes "<Ville> / Non localisé" listings from counts, medians and rankings (clean_immo.py bucket)', () => {
    const stats = computeHomeStats(
      [
        ...listings,
        { ville: 'Lyon', quartier: 'Lyon / Non localisé', code_postal: 69000, prix: 10000, prix_m2: 999 },
      ],
      'lyon',
    );
    expect(stats.annoncesCount).toBe(5);
    expect(stats.excludedCount).toBe(1);
    expect(stats.loyerMedian).toBe(900);
    expect(stats.quartiersAbordables.map((q) => q.label)).not.toContain('Lyon / Non localisé');
  });
});
