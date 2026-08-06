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
});
