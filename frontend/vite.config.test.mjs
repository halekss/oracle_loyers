import assert from 'node:assert/strict';
import config from './vite.config.js';

const host = 'oracle-loyers.onrender.com';

assert.ok(config.server?.allowedHosts?.includes(host));
assert.ok(config.preview?.allowedHosts?.includes(host));
