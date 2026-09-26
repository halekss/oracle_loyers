import { describe, expect, it, beforeEach } from 'vitest';
import { loadCavaliersRadiusM, saveCavaliersRadiusM } from './cavaliersRadiusStorage.js';

const DEFAULT_RADIUS_M = 500;

describe('cavaliersRadiusStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns the given default when nothing has been saved', () => {
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(DEFAULT_RADIUS_M);
  });

  it('round-trips a saved numeric radius', () => {
    saveCavaliersRadiusM(300);
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(300);
  });

  it('round-trips the "Aucun" choice (null)', () => {
    saveCavaliersRadiusM(null);
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBeNull();
  });

  it('persists via the localStorage key (survives across "reloads")', () => {
    saveCavaliersRadiusM(1000);
    expect(localStorage.getItem('oracle-loyers:cavaliersRadiusM')).not.toBeNull();
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(1000);
  });

  it('returns the default instead of throwing when the stored value is corrupted JSON', () => {
    localStorage.setItem('oracle-loyers:cavaliersRadiusM', '{not valid json');
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(DEFAULT_RADIUS_M);
  });

  it('returns the default when the stored value is not a number nor null', () => {
    localStorage.setItem('oracle-loyers:cavaliersRadiusM', JSON.stringify('300'));
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(DEFAULT_RADIUS_M);
  });

  it('does not throw when localStorage.getItem throws (private browsing / unavailable storage)', () => {
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = () => {
      throw new Error('localStorage unavailable');
    };

    expect(() => loadCavaliersRadiusM(DEFAULT_RADIUS_M)).not.toThrow();
    expect(loadCavaliersRadiusM(DEFAULT_RADIUS_M)).toBe(DEFAULT_RADIUS_M);

    Storage.prototype.getItem = original;
  });

  it('does not throw when localStorage.setItem throws (quota exceeded / unavailable storage)', () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => {
      throw new Error('QuotaExceededError');
    };

    expect(() => saveCavaliersRadiusM(500)).not.toThrow();

    Storage.prototype.setItem = original;
  });
});
