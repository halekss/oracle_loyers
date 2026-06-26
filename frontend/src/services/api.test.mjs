import assert from 'node:assert/strict';
import { getApiBaseUrl } from './api.js';

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
