import { describe, expect, it } from 'vitest';
import { normalizeText } from './normalizeText';

describe('normalizeText', () => {
  it('lowercases the input', () => {
    expect(normalizeText('AINAY')).toBe('ainay');
  });

  it('strips accents (é, ô...) like the backend normalize_text', () => {
    expect(normalizeText('Préfecture / Quais')).toBe('prefecture / quais');
    expect(normalizeText('Hôtel de Ville')).toBe('hotel de ville');
  });

  it('makes an accented query match an unaccented target substring', () => {
    expect(normalizeText('Préfecture / Quais').includes(normalizeText('prefecture'))).toBe(true);
  });

  it('returns an empty string for null/undefined', () => {
    expect(normalizeText(null)).toBe('');
    expect(normalizeText(undefined)).toBe('');
  });
});
