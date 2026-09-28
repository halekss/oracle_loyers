import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

  it('displays the representative annonces as compact cards when present (ORA-128/168)', () => {
    const dataWithComparables = {
      ...baseData,
      comparables: [
        { type_local: 'T2', prix: 780, surface: 45 },
        { type_local: 'T2', prix: 810, surface: 48 },
      ],
    };

    render(<ResultCard data={dataWithComparables} loading={false} />);

    expect(screen.getByText('Annonces représentatives')).toBeInTheDocument();
    expect(screen.getByText(/780/)).toBeInTheDocument();
    expect(screen.getByText(/45 m²/)).toBeInTheDocument();
    expect(screen.getByText(/810/)).toBeInTheDocument();
  });

  describe('badge écart et lien « Voir les N » (ORA-168)', () => {
    // référence : baseData.stats.prix_m2 (21 €/m²)
    const comparables = [
      { type_local: 'T2', prix: 600, surface: 40 }, // 15 €/m² -> -29 % : sous le marché
      { type_local: 'T2', prix: 840, surface: 40 }, // 21 €/m² -> 0 % : dans le marché
      { type_local: 'T2', prix: 1200, surface: 40 }, // 30 €/m² -> +43 % : au-dessus
    ];

    it('colors each écart badge by market band (±5 %)', () => {
      render(<ResultCard data={{ ...baseData, comparables }} loading={false} />);

      expect(screen.getByText('-29 %').className).toMatch(/text-market-below/);
      expect(screen.getByText('0 %').className).toMatch(/text-market-within/);
      expect(screen.getByText('+43 %').className).toMatch(/text-market-above/);
    });

    it('links "Voir les N →" to the quartier annonces', async () => {
      const onViewAnnonces = vi.fn();
      render(<ResultCard data={{ ...baseData, comparables, count: 12 }} loading={false} onViewAnnonces={onViewAnnonces} />);

      await userEvent.click(screen.getByRole('button', { name: /voir les 12/i }));

      expect(onViewAnnonces).toHaveBeenCalledWith('Gerland');
    });
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

    describe('slider de surface + bar chart (ORA-190)', () => {
      // Debounce réel (SLIDER_DEBOUNCE_MS = 300ms, ResultCard.jsx) : timers
      // réels + `waitFor`/pauses courtes plutôt que des fake timers — plus
      // simple et plus fiable ici que de synchroniser fake timers, promesses
      // mockées et `act()` à la main pour un debounce aussi court.
      const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

      it('shows a keyboard-accessible slider bounded 10-150 m², initialized on the scanned surface', () => {
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

        const slider = screen.getByLabelText(/simuler une autre surface/i);
        expect(slider).toHaveAttribute('type', 'range');
        expect(slider).toHaveAttribute('min', '10');
        expect(slider).toHaveAttribute('max', '150');
        expect(slider).toHaveValue('45');
      });

      it('does not call api.predict for the surface already known from the scan', async () => {
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

        fireEvent.change(screen.getByLabelText(/simuler une autre surface/i), { target: { value: '45' } });
        await wait(350);

        expect(api.predict).not.toHaveBeenCalled();
      });

      it('calls api.predict once, after a debounce, when the slider moves to a new surface', async () => {
        api.predict.mockResolvedValue({ estimated_price: 1200 });
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

        fireEvent.change(screen.getByLabelText(/simuler une autre surface/i), { target: { value: '60' } });
        expect(api.predict).not.toHaveBeenCalled();

        await waitFor(() => expect(api.predict).toHaveBeenCalledTimes(1), { timeout: 1000 });
        expect(api.predict).toHaveBeenCalledWith({ surface: 60, quartier: 'Ainay', type_local: 'T2' });
        await waitFor(() => expect(screen.getByText('1 200')).toBeInTheDocument());
      });

      it('collapses several rapid slider moves into a single api.predict call (at most 1 call per pause)', async () => {
        api.predict.mockResolvedValue({ estimated_price: 1200 });
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);
        const slider = screen.getByLabelText(/simuler une autre surface/i);

        fireEvent.change(slider, { target: { value: '50' } });
        await wait(100);
        fireEvent.change(slider, { target: { value: '55' } });
        await wait(100);
        fireEvent.change(slider, { target: { value: '60' } });

        await waitFor(() => expect(api.predict).toHaveBeenCalledTimes(1), { timeout: 1000 });
        expect(api.predict).toHaveBeenCalledWith(expect.objectContaining({ surface: 60 }));
      });

      it('shows an error message instead of a phantom bar when the prediction fails', async () => {
        api.predict.mockRejectedValue(new Error('boom'));
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

        fireEvent.change(screen.getByLabelText(/simuler une autre surface/i), { target: { value: '80' } });

        await waitFor(
          () => expect(screen.getByText(/estimation indisponible pour cette surface/i)).toBeInTheDocument(),
          { timeout: 1000 },
        );
        // Rien à comparer sans estimation connue : pas de section fantôme.
        expect(screen.queryByText('Estimation vs marché')).not.toBeInTheDocument();
      });

      it('renders a bar chart comparing the model estimate, the quartier median and the ville median', () => {
        render(
          <ResultCard
            data={{ ...modelData, prixStats: { min: 700, p25: 850, mediane: 950, p75: 1050, max: 1200 } }}
            loading={false}
            ville="lyon"
            health={health}
            listings={[
              { ville: 'Lyon', type_local: 'T2', prix: 800 },
              { ville: 'Lyon', type_local: 'T2', prix: 1000 },
              { ville: 'Lyon', type_local: 'T2', prix: 1200 },
            ]}
          />,
        );

        expect(screen.getByText('Estimation vs marché')).toBeInTheDocument();
        expect(screen.getByText('Estimation modèle')).toBeInTheDocument();
        expect(screen.getByText('Médiane T2 · Ainay')).toBeInTheDocument();
        expect(screen.getByText('Médiane T2 · Lyon')).toBeInTheDocument();
        // 1001 (estimation), 950 (médiane quartier), 1000 (médiane ville).
        expect(screen.getByText('1 001 €')).toBeInTheDocument();
        expect(screen.getByText('950 €')).toBeInTheDocument();
        expect(screen.getByText('1 000 €')).toBeInTheDocument();
      });

      it('omits a bar rather than showing a phantom one when its reference value is unknown', () => {
        // Ni prixStats ni listings fournis : seule l'estimation du modèle est connue.
        render(<ResultCard data={modelData} loading={false} ville="lyon" health={health} />);

        expect(screen.getByText('Estimation modèle')).toBeInTheDocument();
        expect(screen.queryByText(/Médiane T2/)).not.toBeInTheDocument();
      });
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
