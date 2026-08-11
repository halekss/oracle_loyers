import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { logAnnonceClick: vi.fn() },
  };
});

import { api } from '../services/api';
import MapComponent from './MapComponent';
import mapLayersConfig from '../config/mapLayers.config.json';

describe('MapComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.logAnnonceClick.mockResolvedValue({ logged: true, views: 1 });
  });

  it('renders an iframe pointing to the static generated map', () => {
    render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    expect(iframe.getAttribute('src')).toMatch(/^\/data\/map_pings_lyon_calques\.html/);
  });

  it('shows the layer control panel open by default', () => {
    render(<MapComponent center={null} />);
    expect(screen.getByText('Contrôle des Calques')).toBeInTheDocument();
    expect(screen.getByText('Métro (Lignes & Stations)')).toBeInTheDocument();
  });

  it('closes the panel and shows the reopen button when the close button is clicked', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} />);

    // Le bouton de fermeture n'a pas de nom accessible (icône seule) : avant
    // fermeture, c'est le seul bouton présent dans le panneau de contrôle.
    const closeButton = screen.getAllByRole('button')[0];
    await user.click(closeButton);

    expect(screen.queryByText('Contrôle des Calques')).not.toBeInTheDocument();
    expect(screen.getByTitle('Ouvrir les filtres')).toBeInTheDocument();
  });

  it('toggling a layer does not throw even before the iframe has finished loading', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} />);

    // Le contentWindow de l'iframe n'est pas nécessairement prêt dans ce test ;
    // le composant doit ignorer silencieusement la commande plutôt que planter.
    await expect(user.click(screen.getByText('Vice'))).resolves.not.toThrow();
  });

  it('does not attempt to fly to a center when none is provided', () => {
    expect(() => render(<MapComponent center={null} />)).not.toThrow();
  });

  it('sends FLY_TO to the page origin instead of any origin (ORA-125)', () => {
    const { rerender } = render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    rerender(<MapComponent center={[45.75, 4.85, 15]} />);

    expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'FLY_TO' }),
      window.location.origin,
    );
  });

  it('sends TOGGLE_LAYER to the page origin instead of any origin (ORA-125)', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    await user.click(screen.getByText('Vice'));

    expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'TOGGLE_LAYER' }),
      window.location.origin,
    );
  });

  it('sends FLY_TO_BOUNDS to the page origin when bounds are provided (ORA-105)', () => {
    const { rerender } = render(<MapComponent center={null} bounds={undefined} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    const bounds = [
      [45.72, 4.83],
      [45.74, 4.86],
    ];
    rerender(<MapComponent center={null} bounds={bounds} />);

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'FLY_TO_BOUNDS', bounds },
      window.location.origin,
    );
  });

  it('falls back to a FLY_TO on the city center when bounds is explicitly empty (ORA-105)', () => {
    const { rerender } = render(<MapComponent center={null} bounds={undefined} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    rerender(<MapComponent center={null} bounds={null} />);

    expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'FLY_TO' }),
      window.location.origin,
    );
  });

  it('does not send any bounds-related message while bounds has not been computed yet (ORA-105)', () => {
    render(<MapComponent center={null} bounds={undefined} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    expect(postMessage).not.toHaveBeenCalled();
  });

  it('shows a Quartiers toggle', () => {
    render(<MapComponent center={null} />);
    expect(screen.getByText('Quartiers')).toBeInTheDocument();
  });

  it('collapses the layer control panel when the chat opens (ORA-116)', () => {
    const { rerender } = render(<MapComponent center={null} chatOpen={false} />);
    expect(screen.getByText('Contrôle des Calques')).toBeInTheDocument();

    rerender(<MapComponent center={null} chatOpen={true} />);

    expect(screen.queryByText('Contrôle des Calques')).not.toBeInTheDocument();
  });

  it('does not offer to reopen the layer panel while the chat is open (ORA-116)', () => {
    render(<MapComponent center={null} chatOpen={true} />);

    expect(screen.queryByTitle('Ouvrir les filtres')).not.toBeInTheDocument();
  });

  it('offers to reopen the layer panel again once the chat is closed (ORA-116)', () => {
    const { rerender } = render(<MapComponent center={null} chatOpen={true} />);

    rerender(<MapComponent center={null} chatOpen={false} />);

    expect(screen.getByTitle('Ouvrir les filtres')).toBeInTheDocument();
  });

  it('syncs Quartiers as off by default when the iframe loads (ORA-104)', () => {
    render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    iframe.dispatchEvent(new Event('load'));

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'TOGGLE_LAYER', name: 'Quartiers', show: false },
      window.location.origin,
    );
  });

  it('toggling Quartiers sends TOGGLE_LAYER with name Quartiers (ORA-104)', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    await user.click(screen.getByText('Quartiers'));

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'TOGGLE_LAYER', name: 'Quartiers', show: true },
      window.location.origin,
    );
  });

  it('logs the click when the iframe reports an ANNONCE_CLICK from the same origin (ORA-107)', () => {
    render(<MapComponent center={null} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'ANNONCE_CLICK', id: 42 },
      origin: window.location.origin,
    }));

    expect(api.logAnnonceClick).toHaveBeenCalledWith(42);
  });

  it('ignores an ANNONCE_CLICK message from a different origin (ORA-107)', () => {
    render(<MapComponent center={null} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'ANNONCE_CLICK', id: 42 },
      origin: 'https://attacker.example.com',
    }));

    expect(api.logAnnonceClick).not.toHaveBeenCalled();
  });

  it('renders one toggle per layer declared in the shared mapLayers.config.json (ORA-130)', () => {
    render(<MapComponent center={null} />);

    // La liste des calques (nom, libellé, visibilité par défaut) vient d'un
    // seul JSON partagé avec generate_map.py (ORA-130) : chaque entrée doit
    // se retrouver dans le panneau, sans qu'il faille l'y recopier à la main.
    for (const layer of mapLayersConfig) {
      expect(screen.getByText(layer.label)).toBeInTheDocument();
    }
  });

  it('sends TOGGLE_LAYER using the Folium layer name from the shared config, not the internal key (ORA-130)', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    const gentrification = mapLayersConfig.find((layer) => layer.key === 'Gentrification');
    await user.click(screen.getByText(gentrification.label));

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'TOGGLE_LAYER', name: gentrification.name, show: true },
      window.location.origin,
    );
  });

  it('ignores unrelated message events', () => {
    render(<MapComponent center={null} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'SOME_OTHER_MESSAGE' },
      origin: window.location.origin,
    }));

    expect(api.logAnnonceClick).not.toHaveBeenCalled();
  });
});
