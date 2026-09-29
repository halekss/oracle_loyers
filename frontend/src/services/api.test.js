import { afterEach, describe, expect, it, vi } from 'vitest';
import { getApiBaseUrl, apiFetchOptions, parseRateLimitHeaders, api, ApiError } from './api.js';

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

describe('parseRateLimitHeaders', () => {
  it('extracts limit and remaining from response headers (ORA-118)', () => {
    const headers = new Headers({ 'X-RateLimit-Limit': '15', 'X-RateLimit-Remaining': '12' });

    expect(parseRateLimitHeaders(headers)).toEqual({ limit: 15, remaining: 12 });
  });

  it('returns null when the headers are absent (rate limiting disabled or not exposed)', () => {
    expect(parseRateLimitHeaders(new Headers())).toBeNull();
  });
});

describe('api.predict error classification (ORA-198)', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('attaches the backend `code` and `details` to the thrown ApiError on a 400', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: 'Payload invalide', code: 'NO_SURFACE', details: ['surface est requise'] }), {
        status: 400,
      }),
    ));

    await expect(api.predict({ quartier: 'Gerland', type_local: 'T2' })).rejects.toMatchObject({
      code: 'NO_SURFACE',
      details: ['surface est requise'],
    });
  });

  it('attaches the backend `code` on a 500', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: 'incohérent', code: 'IMPLAUSIBLE' }), { status: 500 }),
    ));

    await expect(api.predict({ surface: 45, quartier: 'Gerland', type_local: 'T2' })).rejects.toMatchObject({
      code: 'IMPLAUSIBLE',
    });
  });

  it('leaves `code` null when the error body has none (unexpected server error shape)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('not json', { status: 500 })));

    await expect(api.predict({ surface: 45, quartier: 'Gerland', type_local: 'T2' })).rejects.toMatchObject({
      code: null,
    });
  });

  it('still throws a network-type ApiError (no code) when fetch itself fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const error = await api.predict({ surface: 45, quartier: 'Gerland', type_local: 'T2' }).catch((e) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error.type).toBe('network');
    expect(error.code).toBeNull();
  });
});
