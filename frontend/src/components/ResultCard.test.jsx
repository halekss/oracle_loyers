import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import ResultCard from './ResultCard';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { exportEstimationPdf: vi.fn(), predict: vi.fn() },
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
    api.predict.mockResolvedValue({ estimated_price: 900 });
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

  describe('estimation loyer — fourchette, période, CTA surface (ORA-167)', () => {
    const prixStats = { min: 504, p25: 660, mediane: 789, p75: 880, max: 947 };
    const historique = [{ date: '2026-08-12' }, { date: '2026-08-03' }, { date: '2026-08-14' }];

    it('renders min · P25 · médiane · P75 · max from prixStats', () => {
      render(<ResultCard data={{ ...baseData, prixStats }} loading={false} />);

      const range = screen.getByTestId('price-range');
      for (const value of Object.values(prixStats)) {
        expect(range).toHaveTextContent(String(value));
      }
      expect(range).toHaveTextContent('Médiane');
    });

    it('does not render the range without prixStats', () => {
      render(<ResultCard data={baseData} loading={false} />);
      expect(screen.queryByTestId('price-range')).not.toBeInTheDocument();
    });

    it('shows the period covered by the price history', () => {
      render(<ResultCard data={{ ...baseData, prixStats }} loading={false} priceHistory={{ historique }} />);
      expect(screen.getByText('03/08 → 14/08')).toBeInTheDocument();
    });

    it('offers a "+ Surface" CTA only without a surface, and calls onAddSurface', async () => {
      const onAddSurface = vi.fn();
      const { rerender } = render(<ResultCard data={baseData} loading={false} onAddSurface={onAddSurface} />);

      await userEvent.click(screen.getByRole('button', { name: /\+ surface/i }));
      expect(onAddSurface).toHaveBeenCalledTimes(1);

      rerender(<ResultCard data={{ ...baseData, surface: 45 }} loading={false} onAddSurface={onAddSurface} />);
      expect(screen.queryByRole('button', { name: /\+ surface/i })).not.toBeInTheDocument();
    });
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

  describe('estimation personnalisée (ORA-171, surface + prédiction modèle)', () => {
    const health = {
      models: {
        Lyon: { metrics: { mae: 175, dataset_size: 890 } },
      },
    };
    const modelData = {
      estimated_price: 1001,
      stats: { prix_m2: 22.2 },
      quartier: 'Ainay',
      type: 'T2',
      surface: 45,
      confiance: 'Élevée',
      quartierPrixM2: 19.4,
      count: 12,
      facteurs: [],
      comparables: [{ type_local: 'T2', prix: 1300, surface: 45 }],
    };

    it('renders the "Estimation personnalisée" panel instead of the generic card when a real prediction was made', () => {
      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

      expect(screen.getByText('Estimation personnalisée')).toBeInTheDocument();
      expect(screen.getByText(/Ainay · T2 · 45 m²/)).toBeInTheDocument();
      expect(screen.getByText('1 001')).toBeInTheDocument();
    });

    it('shows the model error margin and dataset size from /api/health, not hardcoded', () => {
      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

      expect(screen.getByText(/± 175 € \(erreur moyenne du modèle XGBoost Lyon\)/)).toBeInTheDocument();
      expect(screen.getByText(/entraîné sur 890 annonces lyonnaises/)).toBeInTheDocument();
    });

    it('compares the model price/m² against the quartier average for the same type', () => {
      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

      expect(screen.getByText(/médiane T2 : 19,4 €/)).toBeInTheDocument();
    });

    it('falls back to the generic card when there is no surface (no real model prediction)', () => {
      render(<ResultCard data={baseData} loading={false} ville="lyon" health={health} />);

      expect(screen.queryByText('Estimation personnalisée')).not.toBeInTheDocument();
      expect(screen.getByText('Estimation Loyer')).toBeInTheDocument();
    });

    it('fetches "et si la surface change" scenarios at surface -15/=/+15 via api.predict', async () => {
      api.predict.mockImplementation(({ surface }) => Promise.resolve({ estimated_price: surface * 20 }));

      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

      await waitFor(() => {
        expect(api.predict).toHaveBeenCalledWith(
          expect.objectContaining({ surface: 30, quartier: 'Ainay', type_local: 'T2' }),
        );
        expect(api.predict).toHaveBeenCalledWith(
          expect.objectContaining({ surface: 60, quartier: 'Ainay', type_local: 'T2' }),
        );
      });
      // La surface courante (45) n'appelle pas l'API : déjà connue via `estimated_price`.
      expect(api.predict).not.toHaveBeenCalledWith(expect.objectContaining({ surface: 45 }));
      await waitFor(() => expect(screen.getByText('600 €')).toBeInTheDocument()); // 30 * 20
    });

    it('shows the écart % of each comparable against the model estimate for its surface', () => {
      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

      // 1300 vs (22.2 * 45 = 999) attendu -> ~+30 %
      expect(screen.getByText(/\+30 %/)).toBeInTheDocument();
    });

    it('still exports a PDF from the estimation personnalisée panel', async () => {
      api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = vi.fn();
      const user = userEvent.setup();

      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);
      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(api.exportEstimationPdf).toHaveBeenCalledWith(
          expect.objectContaining({ quartier: 'Ainay', estimated_price: 1001 }),
        );
      });
    });

    it('includes the surface and data freshness date in the PDF export (ORA-177)', async () => {
      api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = vi.fn();
      const user = userEvent.setup();

      render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} dataAsOf="12/08/2026" />);
      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(api.exportEstimationPdf).toHaveBeenCalledWith(
          expect.objectContaining({ surface: 45, data_as_of: '12/08/2026' }),
        );
      });
    });

    it('does not send a surface in the PDF export without a real model prediction', async () => {
      api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = vi.fn();
      const user = userEvent.setup();

      render(<ResultCard data={baseData} loading={false} />);
      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(api.exportEstimationPdf).toHaveBeenCalledWith(
          expect.objectContaining({ surface: undefined }),
        );
      });
    });

    it('caps the on-screen comparables list at 3 but sends the full list to the PDF export (ORA-177)', async () => {
      api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = vi.fn();
      const user = userEvent.setup();
      const manyComparables = Array.from({ length: 6 }, (_, i) => ({
        type_local: 'T2', prix: 1000 + i, surface: 45, site: 'Vizzit',
      }));
      const dataWithMany = { ...modelData, comparables: manyComparables };

      render(<ResultCard data={dataWithMany} loading={false} ville="lyon" health={health} />);
      expect(screen.getByText('1 000 €')).toBeInTheDocument();
      expect(screen.queryByText('1 005 €')).not.toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(api.exportEstimationPdf).toHaveBeenCalledWith(
          expect.objectContaining({ comparables: manyComparables }),
        );
      });
    });
  });
});
