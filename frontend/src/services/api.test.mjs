import assert from 'node:assert/strict';
import { getApiBaseUrl, apiFetchOptions } from './api.js';

assert.equal(
  getApiBaseUrl({ VITE_API_URL: 'https://backend.example.com/api' }),
  'https://backend.example.com/api',
);

assert.equal(
  getApiBaseUrl({ VITE_API_URL: 'https://backend.example.com/api/' }),
  'https://backend.example.com/api',
);

assert.equal(
  getApiBaseUrl({}),
  'http://localhost:5000/api',
);

assert.throws(
  () => getApiBaseUrl({}, { hostname: 'oracle-loyers.onrender.com' }),
  /VITE_API_URL/,
);

assert.deepEqual(
  apiFetchOptions({ message: 'test' }),
  {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain' },
    body: '{"message":"test"}',
  },
);
