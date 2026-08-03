import { describe, expect, it } from 'vitest';
import { getApiBaseUrl, apiFetchOptions } from './api.js';

describe('getApiBaseUrl', () => {
  it('uses VITE_API_URL when provided', () => {
    expect(getApiBaseUrl({ VITE_API_URL: 'https://backend.example.com/api' })).toBe(
      'https://backend.example.com/api',
    );
  });

  it('strips trailing slashes from VITE_API_URL', () => {
    expect(getApiBaseUrl({ VITE_API_URL: 'https://backend.example.com/api/' })).toBe(
      'https://backend.example.com/api',
    );
  });

  it('falls back to localhost when VITE_API_URL is absent on a local host', () => {
    expect(getApiBaseUrl({})).toBe('http://localhost:5000/api');
  });

  it('throws when VITE_API_URL is absent on a deployed (non-local) host', () => {
    expect(() => getApiBaseUrl({}, { hostname: 'oracle-loyers.onrender.com' })).toThrow(
      /VITE_API_URL/,
    );
  });
});

describe('apiFetchOptions', () => {
  it('builds a POST request with text/plain content-type and a JSON body', () => {
    expect(apiFetchOptions({ message: 'test' })).toEqual({
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: '{"message":"test"}',
    });
  });
});
