import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import MapLegend from './MapLegend';
import { defaultLayerVisibility } from '../services/mapLayers';

const ALL_OFF = Object.fromEntries(Object.keys(defaultLayerVisibility()).map((key) => [key, false]));

describe('MapLegend', () => {
  it('renders nothing when no layer is active and there is no focus', () => {
    const { container } = render(<MapLegend layers={ALL_OFF} focus={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows a single green "Annonces" line listing the active types', () => {
    render(<MapLegend layers={{ ...ALL_OFF, Studio: true, T2: true, T3: true }} focus={null} />);

    expect(screen.getByText('Annonces')).toBeInTheDocument();
    expect(screen.getByText('T1 · T2 · T3')).toBeInTheDocument();
  });

  it('omits the Annonces section when no immo layer is active', () => {
    render(<MapLegend layers={{ ...ALL_OFF, Vice: true }} focus={null} />);

    expect(screen.queryByText('Annonces')).not.toBeInTheDocument();
  });

  it('shows the Métro section only when a transport layer is active', () => {
    const { rerender } = render(<MapLegend layers={{ ...ALL_OFF, Vice: true }} focus={null} />);
    expect(screen.queryByText('Métro')).not.toBeInTheDocument();

    rerender(<MapLegend layers={{ ...ALL_OFF, Metro: true }} focus={null} />);
    expect(screen.getByText('Métro')).toBeInTheDocument();
  });

  it('shows the Cavaliers section (shape + color) only for active cavaliers', () => {
    render(<MapLegend layers={{ ...ALL_OFF, Vice: true, Gentrification: true }} focus={null} />);

    expect(screen.getByText('Cavaliers')).toBeInTheDocument();
    expect(screen.getByText('Vice')).toBeInTheDocument();
    expect(screen.getByText('Gentrification')).toBeInTheDocument();
    expect(screen.queryByText('Nuisance')).not.toBeInTheDocument();
  });

  it('shows the Rayon section only when a focus is provided', () => {
    const { rerender } = render(<MapLegend layers={{ ...ALL_OFF, Vice: true }} focus={null} />);
    expect(screen.queryByText('Rayon')).not.toBeInTheDocument();

    rerender(<MapLegend layers={{ ...ALL_OFF, Vice: true }} focus={{ lat: 45.75, lng: 4.83, radiusM: 300 }} />);
    expect(screen.getByText('Rayon')).toBeInTheDocument();
    expect(screen.getByText('300 m')).toBeInTheDocument();
  });

  it('is collapsible via a "Légende" button', async () => {
    const user = userEvent.setup();
    render(<MapLegend layers={{ ...ALL_OFF, Vice: true }} focus={null} />);

    expect(screen.getByText('Vice')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /légende/i }));
    expect(screen.queryByText('Vice')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /légende/i }));
    expect(screen.getByText('Vice')).toBeInTheDocument();
  });
});
