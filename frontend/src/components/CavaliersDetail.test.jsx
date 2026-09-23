import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import CavaliersDetail from './CavaliersDetail';

const detail = [
  {
    categorie: 'Vice',
    total: 14,
    empty_message: null,
    items: [
      { poi: 'Bar', count: 12, dist_m: 46 },
      { poi: 'Kebab', count: 2, dist_m: 54 },
    ],
  },
  {
    categorie: 'Gentrification',
    total: 7,
    empty_message: null,
    items: [{ poi: 'Épicerie fine', count: 7, dist_m: 76 }],
  },
  {
    categorie: 'Nuisance',
    total: 21,
    empty_message: null,
    items: [{ poi: 'École', count: 21, dist_m: 157 }],
  },
  {
    categorie: 'Superstition',
    total: 0,
    empty_message: 'Rien dans le rayon. Pompes funèbres les plus proches à 573 m.',
    items: [],
  },
];

describe('CavaliersDetail', () => {
  it('renders nothing when there is no detail', () => {
    const { container } = render(<CavaliersDetail detail={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders one card per category with its total lieux count', () => {
    render(<CavaliersDetail detail={detail} quartier="Ainay" />);

    expect(screen.getByText(/Ainay · Les 4 Cavaliers/)).toBeInTheDocument();
    expect(screen.getByText('Vice')).toBeInTheDocument();
    expect(screen.getByText('14 lieux')).toBeInTheDocument();
  });

  it('lists every sub-type with its count and minimum distance', () => {
    render(<CavaliersDetail detail={detail} />);

    expect(screen.getByText('Bar')).toBeInTheDocument();
    expect(screen.getByText('dès 46 m')).toBeInTheDocument();
    expect(screen.getByText('Kebab')).toBeInTheDocument();
    expect(screen.getByText('dès 54 m')).toBeInTheDocument();
  });

  it('shows the empty message for a category with no notable sub-type', () => {
    render(<CavaliersDetail detail={detail} />);

    expect(screen.getByText(/Rien dans le rayon\. Pompes funèbres les plus proches à 573 m\./)).toBeInTheDocument();
  });
});
