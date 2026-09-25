import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

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
import { LAYER_MAPPING, defaultLayerVisibility } from '../services/mapLayers';

const noop = () => {};

// ORA-178 : MapComponent est désormais un composant CONTRÔLÉ — App porte
// l'état `layers` et la fonction `toggleLayer` (remontés, persistés en
// localStorage). Ce petit harnais reproduit ce contrat côté test (état local
// + `onToggleLayer` qui le met à jour) pour vérifier un clic bout-en-bout
// jusqu'au postMessage TOGGLE_LAYER, sans dupliquer la logique d'App dans le
// composant lui-même.
function ControlledMapComponent(props) {
  const [layers, setLayers] = useState(() => props.layers ?? defaultLayerVisibility());
  const toggleLayer = (key) => setLayers((prev) => ({ ...prev, [key]: !prev[key] }));
  return <MapComponent {...props} layers={layers} onToggleLayer={toggleLayer} />;
}

describe('MapComponent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.logAnnonceClick.mockResolvedValue({ logged: true, views: 1 });
  });

  it('renders an iframe pointing to the static generated map', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    const iframe = screen.getByTitle('Carte Oracle');
    expect(iframe.getAttribute('src')).toMatch(/^\/data\/map_pings_lyon_calques\.html/);
  });

  it('points to the lille static map when ville=lille (ORA-71 POC)', () => {
    render(<MapComponent center={null} ville="lille" layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    const iframe = screen.getByTitle('Carte Oracle');
    expect(iframe.getAttribute('src')).toMatch(/^\/data\/map_pings_lille_calques\.html/);
  });

  it('reloads the iframe src when ville changes after mount', () => {
    const { rerender } = render(<MapComponent center={null} ville="lyon" layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    expect(screen.getByTitle('Carte Oracle').getAttribute('src')).toMatch(/map_pings_lyon_calques\.html/);

    rerender(<MapComponent center={null} ville="lille" layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(screen.getByTitle('Carte Oracle').getAttribute('src')).toMatch(/map_pings_lille_calques\.html/);
  });

  it('shows the layer control panel open by default', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    expect(screen.getByText('Contrôle des Calques')).toBeInTheDocument();
    expect(screen.getByText('Métro (Lignes & Stations)')).toBeInTheDocument();
  });

  it('closes the panel and shows the reopen button when the close button is clicked', async () => {
    const user = userEvent.setup();
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    // Le bouton de fermeture n'a pas de nom accessible (icône seule) : avant
    // fermeture, c'est le seul bouton présent dans le panneau de contrôle.
    const closeButton = screen.getAllByRole('button')[0];
    await user.click(closeButton);

    expect(screen.queryByText('Contrôle des Calques')).not.toBeInTheDocument();
    expect(screen.getByTitle('Ouvrir les filtres')).toBeInTheDocument();
  });

  it('toggling a layer does not throw even before the iframe has finished loading', async () => {
    const user = userEvent.setup();
    render(<ControlledMapComponent center={null} />);

    // Le contentWindow de l'iframe n'est pas nécessairement prêt dans ce test ;
    // le composant doit ignorer silencieusement la commande plutôt que planter.
    await expect(user.click(screen.getByText('Vice'))).resolves.not.toThrow();
  });

  it('does not attempt to fly to a center when none is provided', () => {
    expect(() => render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />)).not.toThrow();
  });

  it('sends FLY_TO to the page origin instead of any origin (ORA-125)', () => {
    const { rerender } = render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    rerender(<MapComponent center={[45.75, 4.85, 15]} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'FLY_TO' }),
      window.location.origin,
    );
  });

  describe('fond de carte via le proxy du backend (SET_TILE_URL)', () => {
    it('sends the backend tile proxy URL to the page origin when the iframe loads, never a key', () => {
      render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
      const iframe = screen.getByTitle('Carte Oracle');
      const postMessage = vi.fn();
      Object.defineProperty(iframe, 'contentWindow', { value: { postMessage }, configurable: true });

      fireEvent.load(iframe);

      expect(postMessage).toHaveBeenCalledWith(
        { type: 'SET_TILE_URL', url: 'http://localhost:5000/api/tiles/{z}/{x}/{y}{r}.png' },
        window.location.origin,
      );
      const tileMessages = postMessage.mock.calls.map(([message]) => message).filter((m) => m.type === 'SET_TILE_URL');
      expect(JSON.stringify(tileMessages)).not.toMatch(/key/i);
    });
  });

  it('sends TOGGLE_LAYER to the page origin instead of any origin (ORA-125)', async () => {
    const user = userEvent.setup();
    render(<ControlledMapComponent center={null} />);
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
    const { rerender } = render(<MapComponent center={null} bounds={undefined} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
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
    rerender(<MapComponent center={null} bounds={bounds} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(postMessage).toHaveBeenCalledWith(
      { type: 'FLY_TO_BOUNDS', bounds },
      window.location.origin,
    );
  });

  it('falls back to a FLY_TO on the city center when bounds is explicitly empty (ORA-105)', () => {
    const { rerender } = render(<MapComponent center={null} bounds={undefined} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    rerender(<MapComponent center={null} bounds={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'FLY_TO' }),
      window.location.origin,
    );
  });

  it('does not send any bounds-related message while bounds has not been computed yet (ORA-105)', () => {
    render(<MapComponent center={null} bounds={undefined} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    const iframe = screen.getByTitle('Carte Oracle');
    const postMessage = vi.fn();
    Object.defineProperty(iframe, 'contentWindow', {
      value: { postMessage },
      configurable: true,
    });

    expect(postMessage).not.toHaveBeenCalled();
  });

  it('shows a Quartiers toggle', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    expect(screen.getByText('Quartiers')).toBeInTheDocument();
  });

  it('collapses the layer control panel when the chat opens (ORA-116)', () => {
    const { rerender } = render(<MapComponent center={null} chatOpen={false} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
    expect(screen.getByText('Contrôle des Calques')).toBeInTheDocument();

    rerender(<MapComponent center={null} chatOpen={true} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(screen.queryByText('Contrôle des Calques')).not.toBeInTheDocument();
  });

  it('does not offer to reopen the layer panel while the chat is open (ORA-116)', () => {
    render(<MapComponent center={null} chatOpen={true} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(screen.queryByTitle('Ouvrir les filtres')).not.toBeInTheDocument();
  });

  it('offers to reopen the layer panel again once the chat is closed (ORA-116)', () => {
    const { rerender } = render(<MapComponent center={null} chatOpen={true} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    rerender(<MapComponent center={null} chatOpen={false} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    expect(screen.getByTitle('Ouvrir les filtres')).toBeInTheDocument();
  });

  it('syncs Quartiers as off by default when the iframe loads (ORA-104)', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
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
    render(<ControlledMapComponent center={null} />);
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
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'ANNONCE_CLICK', id: 42 },
      origin: window.location.origin,
    }));

    expect(api.logAnnonceClick).toHaveBeenCalledWith(42);
  });

  it('ignores an ANNONCE_CLICK message from a different origin (ORA-107)', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'ANNONCE_CLICK', id: 42 },
      origin: 'https://attacker.example.com',
    }));

    expect(api.logAnnonceClick).not.toHaveBeenCalled();
  });

  it('renders one toggle per layer declared in the shared mapLayers.config.json (ORA-130)', () => {
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    // La liste des calques (nom, libellé, visibilité par défaut) vient d'un
    // seul JSON partagé avec generate_map.py (ORA-130) : chaque entrée doit
    // se retrouver dans le panneau, sans qu'il faille l'y recopier à la main.
    for (const layer of mapLayersConfig) {
      expect(screen.getByText(layer.label)).toBeInTheDocument();
    }
  });

  it('sends TOGGLE_LAYER using the Folium layer name from the shared config, not the internal key (ORA-130)', async () => {
    const user = userEvent.setup();
    render(<ControlledMapComponent center={null} />);
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
    render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

    window.dispatchEvent(new MessageEvent('message', {
      data: { type: 'SOME_OTHER_MESSAGE' },
      origin: window.location.origin,
    }));

    expect(api.logAnnonceClick).not.toHaveBeenCalled();
  });

  describe('panneau "Les 4 Cavaliers" et compteurs (ORA-172)', () => {
    const originalFetch = globalThis.fetch;

    afterEach(() => {
      globalThis.fetch = originalFetch;
    });

    it('renames the old generic "Contexte" group to "Les 4 Cavaliers" (maquette 04), always expanded', () => {
      render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      expect(screen.getByText('Les 4 Cavaliers')).toBeInTheDocument();
      expect(screen.queryByText('Contexte')).not.toBeInTheDocument();
      expect(screen.getByText('Vice')).toBeInTheDocument();
    });

    it('fetches layer counts from the ville-scoped static map metadata', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ layer_counts: {} }) });

      render(<MapComponent center={null} ville="lille" layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringMatching(/^\/data\/map_metadata_lille\.json/));
    });

    it('shows the count next to a layer once map_metadata layer_counts resolves', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ layer_counts: { Vice: 526, T2: 300 } }),
      });

      render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      expect(await screen.findByText('526')).toBeInTheDocument();
      expect(screen.getByText('300')).toBeInTheDocument();
    });

    it('does not throw and shows no count when the metadata fetch fails', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error('network down'));

      render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      await new Promise((r) => setTimeout(r, 0));
      expect(screen.queryByText('526')).not.toBeInTheDocument();
    });
  });

  describe('pilotage externe des calques (ORA-178, vue "Calques" du rail)', () => {
    it('hides the floating layer panel and reopen button when hidePanel is true', () => {
      render(<MapComponent center={null} hidePanel layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      expect(screen.queryByText('Contrôle des Calques')).not.toBeInTheDocument();
      expect(screen.queryByTitle('Ouvrir les filtres')).not.toBeInTheDocument();
    });

    it('applies the `layers` prop supplied by the parent, never an internal default (composant contrôlé — App est l\'unique source de vérité)', () => {
      // Vice est visible par défaut dans mapLayers.config.json : si ce
      // composant retombait sur un état interne plutôt que sur la prop, ce
      // test resterait vert par erreur (les deux vaudraient `true`).
      const layers = { ...defaultLayerVisibility(), Vice: false };
      render(<MapComponent center={null} layers={layers} onToggleLayer={noop} />);
      const iframe = screen.getByTitle('Carte Oracle');
      const postMessage = vi.fn();
      Object.defineProperty(iframe, 'contentWindow', { value: { postMessage }, configurable: true });

      iframe.dispatchEvent(new Event('load'));

      expect(postMessage).toHaveBeenCalledWith(
        { type: 'TOGGLE_LAYER', name: LAYER_MAPPING.Vice, show: false },
        window.location.origin,
      );
    });

    it('sends TOGGLE_LAYER as soon as the `layers` prop changes, even without any click (App pilote la vue "Calques" à distance)', () => {
      const layers = defaultLayerVisibility();
      const { rerender } = render(<MapComponent center={null} layers={layers} onToggleLayer={noop} />);
      const iframe = screen.getByTitle('Carte Oracle');
      const postMessage = vi.fn();
      Object.defineProperty(iframe, 'contentWindow', { value: { postMessage }, configurable: true });

      rerender(<MapComponent center={null} layers={{ ...layers, Vice: !layers.Vice }} onToggleLayer={noop} />);

      expect(postMessage).toHaveBeenCalledWith(
        { type: 'TOGGLE_LAYER', name: LAYER_MAPPING.Vice, show: !layers.Vice },
        window.location.origin,
      );
    });

    it('calls onAnnonceClick when the iframe reports an ANNONCE_CLICK, in addition to tracking it', () => {
      const onAnnonceClick = vi.fn();
      render(<MapComponent center={null} onAnnonceClick={onAnnonceClick} layers={defaultLayerVisibility()} onToggleLayer={noop} />);

      window.dispatchEvent(new MessageEvent('message', {
        data: { type: 'ANNONCE_CLICK', id: 42 },
        origin: window.location.origin,
      }));

      expect(onAnnonceClick).toHaveBeenCalledWith(42);
    });
  });

  describe('cercle de rayon des cavaliers (vue "Calques", ORA-178)', () => {
    it('sends SHOW_RADIUS_CIRCLE when a radiusCircle prop is provided', () => {
      const { rerender } = render(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} />);
      const iframe = screen.getByTitle('Carte Oracle');
      const postMessage = vi.fn();
      Object.defineProperty(iframe, 'contentWindow', { value: { postMessage }, configurable: true });

      rerender(
        <MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} radiusCircle={{ lat: 45.75, lng: 4.83, radius: 500 }} />,
      );

      expect(postMessage).toHaveBeenCalledWith(
        { type: 'SHOW_RADIUS_CIRCLE', lat: 45.75, lng: 4.83, radius: 500, color: '#A78BFA' },
        window.location.origin,
      );
    });

    it('sends HIDE_RADIUS_CIRCLE when radiusCircle goes back to null', () => {
      const { rerender } = render(
        <MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} radiusCircle={{ lat: 45.75, lng: 4.83, radius: 500 }} />,
      );
      const iframe = screen.getByTitle('Carte Oracle');
      const postMessage = vi.fn();
      Object.defineProperty(iframe, 'contentWindow', { value: { postMessage }, configurable: true });

      rerender(<MapComponent center={null} layers={defaultLayerVisibility()} onToggleLayer={noop} radiusCircle={null} />);

      expect(postMessage).toHaveBeenCalledWith({ type: 'HIDE_RADIUS_CIRCLE' }, window.location.origin);
    });
  });

  describe('légende "Cavaliers affichés" (remplace le panneau flottant, ORA-178)', () => {
    it('lists only the cavalier layers that are currently active', () => {
      const layers = { ...defaultLayerVisibility(), Vice: true, Gentrification: false, Nuisance: true, Superstition: false };
      render(<MapComponent center={null} hidePanel layers={layers} onToggleLayer={noop} />);

      expect(screen.getByText('Cavaliers affichés')).toBeInTheDocument();
      expect(screen.getByText('Vice')).toBeInTheDocument();
      expect(screen.getByText('Nuisance')).toBeInTheDocument();
      expect(screen.queryByText('Gentrification')).not.toBeInTheDocument();
      expect(screen.queryByText('Superstition')).not.toBeInTheDocument();
    });

    it('shows the radius alongside the legend when a radiusCircle is provided', () => {
      const layers = { ...defaultLayerVisibility(), Vice: true };
      render(
        <MapComponent center={null} hidePanel layers={layers} onToggleLayer={noop} radiusCircle={{ lat: 45.75, lng: 4.83, radius: 500 }} />,
      );

      expect(screen.getByText(/500 m/)).toBeInTheDocument();
    });

    it('is not shown when no cavalier layer is active', () => {
      const layers = { ...defaultLayerVisibility(), Vice: false, Gentrification: false, Nuisance: false, Superstition: false };
      render(<MapComponent center={null} hidePanel layers={layers} onToggleLayer={noop} />);

      expect(screen.queryByText('Cavaliers affichés')).not.toBeInTheDocument();
    });

    it('does not replace the mobile floating panel (hidePanel=false) with this legend', () => {
      const layers = { ...defaultLayerVisibility(), Vice: true };
      render(<MapComponent center={null} layers={layers} onToggleLayer={noop} />);

      expect(screen.queryByText('Cavaliers affichés')).not.toBeInTheDocument();
    });
  });
});
