import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('./services/api', async () => {
  const actual = await vi.importActual('./services/api');
  return {
    ...actual,
    api: {
      ...actual.api,
      getListings: vi.fn(),
      getHealth: vi.fn(),
      getQuartierStats: vi.fn(),
      getQuartierHistorique: vi.fn(),
      getAnnonces: vi.fn(),
    },
  };
});

import { api } from './services/api';
import App from './App';

// jsdom n'implémente pas matchMedia (utilisé par useIsDesktop) — polyfill
// minimal, `matches: false` sans incidence ici : la colonne rail desktop est
// toujours présente dans le DOM (visibilité purement CSS, `hidden md:flex`),
// jamais démontée selon isDesktop.
function mockMatchMedia() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
}

describe('App — scan puis vue Annonces (ORA-186)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMatchMedia();
    api.getListings.mockResolvedValue([{ ville: 'Lyon', quartier: 'Wazemmes' }]);
    api.getHealth.mockResolvedValue(null);
    api.getQuartierHistorique.mockResolvedValue(null);
    api.getAnnonces.mockResolvedValue({ items: [], total: 0, total_pages: 0 });
    api.getQuartierStats.mockResolvedValue({
      found: true,
      quartier_detecte: 'Wazemmes',
      type_filtre: 'Tout',
      count: 3,
      prix_moyen: 700,
      prix_m2_moyen: 15,
      prix_stats: { min: 500, p25: 600, mediane: 700, p75: 800, max: 900 },
      center: null,
      facteurs: [],
      cavaliers_detail: [],
      comparables: [],
    });
  });

  it('preselects the Annonces filter on the scanned quartier without clicking "Voir les annonces" (ORA-186)', async () => {
    const user = userEvent.setup();
    render(<App />);

    const quartierInput = screen.getByLabelText('Quartier à scanner');
    await user.type(quartierInput, 'Wazemmes');
    // Le rail desktop porte aussi un bouton "Scan" (navigation de vue) : on
    // cible celui du formulaire (type="submit") pour lever l'ambiguïté.
    const scanForm = quartierInput.closest('form');
    await user.click(within(scanForm).getByRole('button', { name: 'Scan' }));

    await waitFor(() => expect(api.getQuartierStats).toHaveBeenCalledWith('Wazemmes', 'Tout', 'lyon'));

    // ORA-178 : "Annonces" est une vue du rail desktop — y accéder directement
    // (sans passer par "Voir les annonces de ce quartier" du ResultCard)
    // prouve que le filtre est déjà présélectionné à l'ouverture.
    await user.click(await screen.findByRole('button', { name: /^Annonces/ }));

    // id unique (`annonces-quartier-filter`, pas `-compact`) : seule la vue
    // "Annonces" du rail l'utilise, contrairement aux aperçus compacts (vue
    // Scan, colonne mobile) qui partagent un id dupliqué entre eux.
    await waitFor(() => {
      expect(document.getElementById('annonces-quartier-filter')).toHaveValue('Wazemmes');
    });
  });
});
