import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import MapComponent from './MapComponent';

describe('MapComponent', () => {
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
});
