import { describe, expect, it } from 'vitest';
import config from './vite.config.js';

const host = 'oracle-loyers.onrender.com';

describe('vite.config.js', () => {
  it('allows the production host for the dev server', () => {
    expect(config.server?.allowedHosts).toContain(host);
  });

  it('allows the production host for the preview server', () => {
    expect(config.preview?.allowedHosts).toContain(host);
  });
});
