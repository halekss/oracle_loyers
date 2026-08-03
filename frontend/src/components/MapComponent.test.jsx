import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

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
});
