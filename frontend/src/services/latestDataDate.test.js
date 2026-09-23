import { describe, expect, it } from 'vitest';
import { computeLatestDataDate } from './latestDataDate';

describe('computeLatestDataDate', () => {
  it('formats the most recent date_dernier_scan for the ville as DD/MM/YYYY', () => {
    const listings = [
      { ville: 'Lille', date_dernier_scan: '2026-08-01' },
      { ville: 'Lille', date_dernier_scan: '2026-08-12' },
      { ville: 'Lille', date_dernier_scan: '2026-07-30' },
    ];
    expect(computeLatestDataDate(listings, 'lille')).toBe('12/08/2026');
  });

  it('filters by ville (case-insensitive)', () => {
    const listings = [
      { ville: 'Lille', date_dernier_scan: '2026-08-12' },
      { ville: 'Lyon', date_dernier_scan: '2026-09-01' },
    ];
    expect(computeLatestDataDate(listings, 'lille')).toBe('12/08/2026');
  });

  it('returns null when the ville has no date_dernier_scan at all (Lyon, older pipeline)', () => {
    const listings = [
      { ville: 'Lille', date_dernier_scan: '2026-08-12' },
      { ville: 'Lyon', date_dernier_scan: '' },
      { ville: 'Lyon' },
    ];
    expect(computeLatestDataDate(listings, 'lyon')).toBeNull();
  });

  it('returns null for an empty listings array', () => {
    expect(computeLatestDataDate([], 'lyon')).toBeNull();
  });
});
