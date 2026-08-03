import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ResultCard from './ResultCard';

const baseData = {
  estimated_price: 950,
  stats: { prix_m2: 21 },
  quartier: 'Gerland',
  confiance: 'Élevée',
  facteurs: [
    { categorie: 'Vice', phrase: '2 bar(s) à moins de 500m — parfait pour un verre, moins pour dormir.' },
    { categorie: 'Gentrification', phrase: 'Une salle de sport à 338m — la gentrification muscle aussi les mollets.' },
  ],
};

describe('ResultCard', () => {
  it('shows a loading skeleton while loading', () => {
    const { container } = render(<ResultCard data={null} loading={true} />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders the estimated price and price per m²', () => {
    render(<ResultCard data={baseData} loading={false} />);

    expect(screen.getByText('950')).toBeInTheDocument();
    expect(screen.getByText('21')).toBeInTheDocument();
    expect(screen.getByText(/Confiance IA : Élevée/)).toBeInTheDocument();
  });

  it('includes the estimation in the printable report for PDF export', () => {
    render(<ResultCard data={baseData} loading={false} />);

    const report = document.getElementById('printable-report');
    expect(report).not.toBeNull();
    expect(report.textContent).toContain('950');
    expect(report.textContent).toContain('Gerland');
  });

  it('renders the cavaliers factors when present', () => {
    // Le rapport imprimable (#printable-report) répète les mêmes phrases pour
    // l'export PDF : on s'attend à 2 occurrences (affichage écran + rapport).
    render(<ResultCard data={baseData} loading={false} />);

    expect(screen.getAllByText(/parfait pour un verre/)).toHaveLength(2);
    expect(screen.getAllByText(/muscle aussi les mollets/)).toHaveLength(2);
  });

  it('does not render a factors section when there are none', () => {
    render(<ResultCard data={{ ...baseData, facteurs: [] }} loading={false} />);

    expect(screen.queryByText('Les 4 Cavaliers')).not.toBeInTheDocument();
  });

  it('does not render the export button or factors when there is no data', () => {
    render(<ResultCard data={null} loading={false} />);

    expect(screen.queryByRole('button', { name: /exporter en pdf/i })).not.toBeInTheDocument();
  });

  it('triggers window.print when the export button is clicked', async () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<ResultCard data={baseData} loading={false} />);
    await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

    expect(printSpy).toHaveBeenCalledTimes(1);
    printSpy.mockRestore();
  });
});
