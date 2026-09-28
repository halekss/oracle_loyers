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
      getAnnonceDetail: vi.fn(),
      logAnnonceClick: vi.fn(),
    },
  };
});

import { api } from './services/api';
import App from './App';

// jsdom n'implémente pas matchMedia (utilisé par useIsDesktop) — polyfill
// minimal, `matches: false` sans incidence ici : la colonne rail desktop est
// toujours présente dans le DOM (visibilité purement CSS, `hidden md:flex`),
// jamais démontée selon isDesktop.
function mockMatchMedia(matches = false) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches,
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

describe('App — sélection d\'une annonce et navigation de la Fiche (ORA-196)', () => {
  const annonceSummary = {
    id: 7, titre: 'T2 Wazemmes', prix: 780, surface: 42, ville: 'Lyon', quartier: 'Wazemmes',
    url: 'https://example.com/annonce-7', images: [],
  };
  const annonceDetail = { ...annonceSummary, type_local: 'T2', prix_m2: 18.6, cavaliers_detail: [] };

  beforeEach(() => {
    vi.clearAllMocks();
    // Desktop (matches: true) : nécessaire pour que la carte (iframe) soit
    // montée (`shouldMountMap = isDesktop || activeTab === 'carte'`,
    // App.jsx) — la dernière annonce de ce bloc envoie LISTING_SELECTED
    // depuis cette iframe.
    mockMatchMedia(true);
    api.getListings.mockResolvedValue([]);
    api.getHealth.mockResolvedValue(null);
    api.getQuartierHistorique.mockResolvedValue(null);
    api.getAnnonces.mockResolvedValue({ items: [annonceSummary], total: 1, total_pages: 1 });
    api.getAnnonceDetail.mockResolvedValue(annonceDetail);
    api.logAnnonceClick.mockResolvedValue({ logged: true, views: 1 });
  });

  // Le rail ("Annonces") et l'aperçu compact d'autres vues (Scan, colonne
  // mobile) sont tous montés en permanence (CSS hidden, cf. MapComponent/
  // App) : le même item mocké s'y affiche donc plusieurs fois. `getAllBy*`
  // plutôt que `getBy*`, cliquer le premier suffit (même annonce, même id).
  const openAnnoncesView = async (user) => {
    await user.click(screen.getByRole('button', { name: /^Annonces/ }));
    await screen.findAllByText('T2 Wazemmes');
  };

  const clickFirstDetailsButton = async (user) => {
    const [button] = await screen.findAllByRole('button', { name: /détails/i });
    await user.click(button);
  };

  it('disables the Fiche tab until an annonce is selected', async () => {
    render(<App />);

    expect(screen.getByRole('button', { name: 'Fiche' })).toHaveAttribute('aria-disabled', 'true');
  });

  it('selecting "Détails" in the Annonces list opens the Fiche with that annonce, and enables the tab', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openAnnoncesView(user);
    await clickFirstDetailsButton(user);

    expect(await screen.findByText('Fiche annonce')).toBeInTheDocument();
    await waitFor(() => expect(api.getAnnonceDetail).toHaveBeenCalledWith(7));
    // Le prix apparaît aussi dans la colonne Oracle mobile (AnnoncesList
    // toujours montée, cachée en CSS) : on scope à la feuille du rail
    // (#panel-sheet) où vit la Fiche pour lever l'ambiguïté.
    const panelSheet = document.getElementById('panel-sheet');
    expect(await within(panelSheet).findByText(/780/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Fiche' })).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('"← Retour" returns to the view the Fiche was opened from', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openAnnoncesView(user);
    await clickFirstDetailsButton(user);
    await screen.findByText('Fiche annonce');

    await user.click(screen.getByRole('button', { name: /retour/i }));

    expect(await screen.findAllByText('T2 Wazemmes')).not.toHaveLength(0);
    expect(screen.queryByText('Fiche annonce')).not.toBeInTheDocument();
  });

  it('Escape returns to the view the Fiche was opened from', async () => {
    const user = userEvent.setup();
    render(<App />);

    await openAnnoncesView(user);
    await clickFirstDetailsButton(user);
    await screen.findByText('Fiche annonce');

    await user.keyboard('{Escape}');

    expect(await screen.findAllByText('T2 Wazemmes')).not.toHaveLength(0);
    expect(screen.queryByText('Fiche annonce')).not.toBeInTheDocument();
  });

  it('a LISTING_SELECTED message from the map opens the Fiche with the same mechanism as the list', async () => {
    render(<App />);
    const iframe = screen.getByTitle('Carte Oracle');

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'LISTING_SELECTED', id: 7 },
      origin: window.location.origin,
      source: iframe.contentWindow,
    }));

    expect(await screen.findByText('Fiche annonce')).toBeInTheDocument();
    await waitFor(() => expect(api.getAnnonceDetail).toHaveBeenCalledWith(7));
  });
});
