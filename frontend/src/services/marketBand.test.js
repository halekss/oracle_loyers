import { describe, expect, it } from 'vitest';

import { ecartPct, marketBand } from './marketBand';

describe('marketBand — seuils ±5 % (ORA-165/168)', () => {
  it.each([
    [-30, 'below'],
    [-5.1, 'below'],
    [-5, 'within'],
    [0, 'within'],
    [5, 'within'],
    [5.1, 'above'],
    [40, 'above'],
  ])('%s %% -> %s', (pct, band) => {
    expect(marketBand(pct)).toBe(band);
  });
});

describe('ecartPct', () => {
  it('computes the rounded percentage gap to the reference', () => {
    expect(ecartPct(21, 20)).toBe(5);
    expect(ecartPct(19, 20)).toBe(-5);
  });

  it('returns null when a value or the reference is unusable', () => {
    expect(ecartPct(null, 20)).toBeNull();
    expect(ecartPct(20, 0)).toBeNull();
    expect(ecartPct(20, undefined)).toBeNull();
  });
});
