import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import CalquesView from './CalquesView';
import { defaultLayerVisibility } from '../services/mapLayers';

const cavaliersDetail = [
  {
    categorie: 'Vice',
    total: 19,
    items: [
      { poi: 'Bar', count: 12, dist_m: 46 },
      { poi: 'Tabac', count: 3, dist_m: 158 },
    ],
    empty_message: null,
  },
  {
    categorie: 'Gentrification',
    total: 24,
    items: [{ poi: 'Salle sport', count: 24, dist_m: 54 }],
    empty_message: null,
  },
  {
    categorie: 'Nuisance',
    total: 21,
    items: [{ poi: 'École', count: 21, dist_m: 140 }],
    empty_message: null,
  },
  {
    categorie: 'Superstition',
    total: 0,
    items: [],
    empty_message: 'Rien dans le rayon. Pompes funèbres les plus proches à 573 m.',
  },
];

const facteurs = [
  { categorie: 'Vice', phrase: '12 bars, le premier à 46 m : parfait pour un verre, moins pour dormir.' },
  { categorie: 'Gentrification', phrase: 'Une salle de sport à 54m.' },
  { categorie: 'Nuisance', phrase: 'Une école à 140m.' },
  { categorie: 'Superstition', phrase: 'Rien à signaler.' },
];

function renderView(props = {}) {
  return render(
    <CalquesView
      layers={defaultLayerVisibility()}
      onToggleLayer={vi.fn()}
      zonesCount={9}
      ville="lyon"
      onGoToRecherche={vi.fn()}
      {...props}
    />,
  );
}

describe('CalquesView', () => {
  it('shows the empty state and lets the user jump to Recherche when nothing has been scanned', async () => {
    const user = userEvent.setup();
    const onGoToRecherche = vi.fn();
    renderView({ cavaliersDetail: undefined, facteurs: undefined, onGoToRecherche });

    expect(screen.getByText(/lance un scan/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /recherche/i }));

    expect(onGoToRecherche).toHaveBeenCalledTimes(1);
  });

  it('keeps the cavalier visibility switches usable even without a scan', async () => {
    const user = userEvent.setup();
    const onToggleLayer = vi.fn();
    renderView({ cavaliersDetail: undefined, facteurs: undefined, onToggleLayer });

    await user.click(screen.getByRole('switch', { name: /vice/i }));

    expect(onToggleLayer).toHaveBeenCalledWith('Vice');
  });

  it('calls onToggleLayer with the right key for a "Fonds de carte" switch', async () => {
    const user = userEvent.setup();
    const onToggleLayer = vi.fn();
    renderView({ onToggleLayer });

    await user.click(screen.getByRole('switch', { name: /€\/m²/i }));

    expect(onToggleLayer).toHaveBeenCalledWith('Quartiers');
  });

  it('calls onToggleLayer with the right key for a cavalier switch', async () => {
    const user = userEvent.setup();
    const onToggleLayer = vi.fn();
    renderView({ cavaliersDetail, facteurs, onToggleLayer });

    await user.click(screen.getByRole('switch', { name: /gentrification/i }));

    expect(onToggleLayer).toHaveBeenCalledWith('Gentrification');
  });

  it('expands the category with the most lieux by default', () => {
    renderView({ cavaliersDetail, facteurs });

    // Gentrification (24 lieux, le maximum) doit être dépliée d'entrée.
    expect(screen.getByRole('button', { name: /gentrification/i })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: /^vice/i })).toHaveAttribute('aria-expanded', 'false');
  });

  it('only ever expands one cavalier row at a time', async () => {
    const user = userEvent.setup();
    renderView({ cavaliersDetail, facteurs });

    await user.click(screen.getByRole('button', { name: /^vice/i }));

    expect(screen.getByRole('button', { name: /^vice/i })).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('button', { name: /gentrification/i })).toHaveAttribute('aria-expanded', 'false');
  });

  it('collapses the row when its own expand button is clicked again', async () => {
    const user = userEvent.setup();
    renderView({ cavaliersDetail, facteurs });

    await user.click(screen.getByRole('button', { name: /gentrification/i }));

    expect(screen.getByRole('button', { name: /gentrification/i })).toHaveAttribute('aria-expanded', 'false');
  });

  it('shows the humorous phrase from cavaliers_factors inside the expanded row', () => {
    renderView({ cavaliersDetail, facteurs });

    expect(screen.queryByText(/parfait pour un verre/i)).not.toBeInTheDocument(); // Vice replié par défaut
    expect(screen.getByText('Une salle de sport à 54m.')).toBeInTheDocument(); // Gentrification dépliée
  });
});
