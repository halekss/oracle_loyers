import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('../services/api', () => ({
  api: { getCavaliers: vi.fn() },
}));

import { api } from '../services/api';
import { useCavaliersRadius } from './useCavaliersRadius';
import { CAVALIERS_RADIUS_M } from '../services/cavaliersDisplay';

const defaultDetail = [{ categorie: 'Vice', total: 5, items: [], empty_message: null }];
const defaultFacteurs = [{ categorie: 'Vice', phrase: '5 bar(s) à moins de 500m.' }];

function renderCavaliersRadius(props) {
  return renderHook((p) => useCavaliersRadius(p), { initialProps: props });
}

describe('useCavaliersRadius', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('uses the scan result directly at the default radius (500m), without calling the API', () => {
    const { result } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });

    expect(result.current.cavaliersDetail).toBe(defaultDetail);
    expect(result.current.facteurs).toBe(defaultFacteurs);
    expect(result.current.isLoading).toBe(false);
    expect(api.getCavaliers).not.toHaveBeenCalled();
  });

  it('calls the API with the right rayon_m when the radius changes away from the default', async () => {
    api.getCavaliers.mockResolvedValue({ cavaliers_detail: [{ categorie: 'Vice', total: 1 }], facteurs: [] });
    const { result, rerender } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });

    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 300, defaultDetail, defaultFacteurs,
    });

    expect(api.getCavaliers).toHaveBeenCalledWith(45.75, 4.83, 'lyon', 300);
    await waitFor(() => expect(result.current.cavaliersDetail).toBeDefined());
    expect(result.current.cavaliersDetail).toEqual([{ categorie: 'Vice', total: 1 }]);
    expect(result.current.isLoading).toBe(false);
  });

  it('sets isLoading while the request is in flight', async () => {
    let resolvePromise;
    api.getCavaliers.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve; }));
    const { result, rerender } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });

    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 1000, defaultDetail, defaultFacteurs,
    });

    await waitFor(() => expect(result.current.isLoading).toBe(true));

    resolvePromise({ cavaliers_detail: [], facteurs: [] });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });

  it('caches the result per (quartier, rayon) and avoids a second API call', async () => {
    api.getCavaliers.mockResolvedValue({ cavaliers_detail: [{ categorie: 'Vice', total: 2 }], facteurs: [] });
    const { rerender } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });

    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 300, defaultDetail, defaultFacteurs,
    });
    await waitFor(() => expect(api.getCavaliers).toHaveBeenCalledTimes(1));

    // Retour à 500m (pas d'appel, cf. premier test), puis de nouveau 300m :
    // déjà en cache, ne doit pas redéclencher d'appel réseau.
    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });
    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 300, defaultDetail, defaultFacteurs,
    });

    expect(api.getCavaliers).toHaveBeenCalledTimes(1);
  });

  it('does not flip isLoading to true for a cached radius (no flicker)', async () => {
    api.getCavaliers.mockResolvedValue({ cavaliers_detail: [{ categorie: 'Vice', total: 2 }], facteurs: [] });
    const { result, rerender } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });
    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 300, defaultDetail, defaultFacteurs,
    });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });
    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: 300, defaultDetail, defaultFacteurs,
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('calls the API with null (not the default radius) for the "Aucun" choice', async () => {
    api.getCavaliers.mockResolvedValue({
      cavaliers_detail: [{ categorie: 'Vice', total: 546, items: [{ poi: 'Bar', count: 546 }] }],
      facteurs: [],
    });
    const { result, rerender } = renderCavaliersRadius({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail, defaultFacteurs,
    });

    rerender({
      quartier: 'Ainay', center: { lat: 45.75, lng: 4.83 }, ville: 'lyon',
      radiusM: null, defaultDetail, defaultFacteurs,
    });

    expect(api.getCavaliers).toHaveBeenCalledWith(45.75, 4.83, 'lyon', null);
    await waitFor(() => expect(result.current.cavaliersDetail).toBeDefined());
    expect(result.current.cavaliersDetail[0].total).toBe(546);
    expect(result.current.facteurs).toEqual([]);
  });

  it('returns no detail when there is no scanned quartier', () => {
    const { result } = renderCavaliersRadius({
      quartier: undefined, center: undefined, ville: 'lyon',
      radiusM: CAVALIERS_RADIUS_M, defaultDetail: undefined, defaultFacteurs: undefined,
    });

    expect(result.current.cavaliersDetail).toBeUndefined();
    expect(result.current.isLoading).toBe(false);
    expect(api.getCavaliers).not.toHaveBeenCalled();
  });
});
