import { describe, expect, it } from 'vitest';
import { sanitizeListingUrl } from './sanitizeUrl.js';

describe('sanitizeListingUrl', () => {
  it('accepts an http url', () => {
    expect(sanitizeListingUrl('http://example.com/annonce-1')).toBe('http://example.com/annonce-1');
  });

  it('accepts an https url and strips whitespace', () => {
    expect(sanitizeListingUrl('  https://example.com/annonce-2  ')).toBe('https://example.com/annonce-2');
  });

  it('rejects the javascript: scheme', () => {
    expect(sanitizeListingUrl('javascript:alert(1)')).toBeNull();
  });

  it('rejects the data: scheme', () => {
    expect(sanitizeListingUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
  });

  it('rejects non-string values', () => {
    expect(sanitizeListingUrl(null)).toBeNull();
    expect(sanitizeListingUrl(undefined)).toBeNull();
    expect(sanitizeListingUrl(42)).toBeNull();
  });

  it('rejects an empty or blank string', () => {
    expect(sanitizeListingUrl('')).toBeNull();
    expect(sanitizeListingUrl('   ')).toBeNull();
  });
});
