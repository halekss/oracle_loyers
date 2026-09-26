import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { useLayerCounts } from './useLayerCounts';

function Probe({ ville }) {
  const counts = useLayerCounts(ville);
  return <span>{JSON.stringify(counts)}</span>;
}

describe('useLayerCounts', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('fetches layer counts from the ville-scoped static map metadata', () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ layer_counts: {} }) });

    render(<Probe ville="lille" />);

    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringMatching(/^\/data\/map_metadata_lille\.json/));
  });

  it('resolves layer_counts from the fetched metadata', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ layer_counts: { Vice: 526, T2: 300 } }),
    });

    render(<Probe ville="lyon" />);

    expect(await screen.findByText(JSON.stringify({ Vice: 526, T2: 300 }))).toBeInTheDocument();
  });

  it('does not throw and resolves an empty object when the metadata fetch fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'));

    render(<Probe ville="lyon" />);

    expect(await screen.findByText('{}')).toBeInTheDocument();
  });
});
