import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import ResultCard from './ResultCard';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { exportEstimationPdf: vi.fn() },
  };
});

import { api } from '../services/api';

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
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it('explains the confidence using the comparables count (ORA-128)', () => {
    render(<ResultCard data={{ ...baseData, count: 12 }} loading={false} />);

    expect(screen.getByText(/12 bien/i)).toBeInTheDocument();
  });

  it('does not show a confidence explanation without a count', () => {
    render(<ResultCard data={{ ...baseData, count: undefined }} loading={false} />);

    expect(screen.queryByText(/bien\(s\) comparable/i)).not.toBeInTheDocument();
  });

  it('displays the comparables list when present (ORA-128)', () => {
    const dataWithComparables = {
      ...baseData,
      comparables: [
        { type_local: 'T2', prix: 780, surface: 45 },
        { type_local: 'T2', prix: 810, surface: 48 },
      ],
    };

    render(<ResultCard data={dataWithComparables} loading={false} />);

    expect(screen.getByText('Biens comparables')).toBeInTheDocument();
    expect(screen.getByText(/780/)).toBeInTheDocument();
    expect(screen.getByText(/45/)).toBeInTheDocument();
    expect(screen.getByText(/810/)).toBeInTheDocument();
  });

  it('does not show a comparables section when there are none', () => {
    render(<ResultCard data={baseData} loading={false} />);

    expect(screen.queryByText('Biens comparables')).not.toBeInTheDocument();
  });

  it('does not render the export button when there is no data', () => {
    render(<ResultCard data={null} loading={false} />);

    expect(screen.queryByRole('button', { name: /exporter en pdf/i })).not.toBeInTheDocument();
  });

  it('requests a PDF report with the displayed estimation when the export button is clicked (ORA-121)', async () => {
    api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
    const user = userEvent.setup();

    render(<ResultCard data={baseData} loading={false} />);
    await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

    await waitFor(() => {
      expect(api.exportEstimationPdf).toHaveBeenCalledWith(
        expect.objectContaining({
          quartier: 'Gerland',
          estimated_price: 950,
          prix_m2: 21,
          confiance: 'Élevée',
          facteurs: baseData.facteurs,
        }),
      );
    });

    clickSpy.mockRestore();
  });

  it('includes the price history and comparables when exporting the PDF (ORA-122)', async () => {
    api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
    const user = userEvent.setup();
    const historique = [{ date: '2026-01-01T00:00:00+00:00', prix_m2_moyen: 20, count: 12 }];
    const dataWithComparables = {
      ...baseData,
      comparables: [{ type_local: 'T2', prix: 780, surface: 45 }],
    };

    render(<ResultCard data={dataWithComparables} loading={false} priceHistory={{ historique }} />);
    await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

    await waitFor(() => {
      expect(api.exportEstimationPdf).toHaveBeenCalledWith(
        expect.objectContaining({
          historique,
          comparables: dataWithComparables.comparables,
        }),
      );
    });

    clickSpy.mockRestore();
  });

  it('triggers a direct download instead of the system print dialog (ORA-121)', async () => {
    api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {});
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    URL.createObjectURL = vi.fn(() => 'blob:mock-url');
    URL.revokeObjectURL = vi.fn();
    const user = userEvent.setup();

    render(<ResultCard data={baseData} loading={false} />);
    await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

    await waitFor(() => expect(clickSpy).toHaveBeenCalledTimes(1));
    expect(printSpy).not.toHaveBeenCalled();

    printSpy.mockRestore();
    clickSpy.mockRestore();
  });

  it('shows an error message when the PDF export fails', async () => {
    api.exportEstimationPdf.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();

    render(<ResultCard data={baseData} loading={false} />);
    await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

    await waitFor(() => {
      expect(screen.getByText(/erreur/i)).toBeInTheDocument();
    });
  });

  it('offers a direct link to the scanned quartier annonces when onViewAnnonces is provided (ORA-127)', async () => {
    const onViewAnnonces = vi.fn();
    const user = userEvent.setup();

    render(<ResultCard data={baseData} loading={false} onViewAnnonces={onViewAnnonces} />);
    await user.click(screen.getByRole('button', { name: /voir les annonces de gerland/i }));

    expect(onViewAnnonces).toHaveBeenCalledWith('Gerland');
  });

  it('does not show the annonces link when onViewAnnonces is not provided', () => {
    render(<ResultCard data={baseData} loading={false} />);

    expect(screen.queryByRole('button', { name: /voir les annonces/i })).not.toBeInTheDocument();
  });
});
