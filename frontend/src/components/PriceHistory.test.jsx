import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import PriceHistory from './PriceHistory';

describe('PriceHistory', () => {
  it('renders nothing before any scan has been performed', () => {
    const { container } = render(<PriceHistory status={undefined} message={undefined} historique={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the honest "not enough history" message rather than a fake trend', () => {
    render(
      <PriceHistory
        status="insufficient_history"
        message="Pas encore assez d'historique de données pour observer une tendance (un seul snapshot enregistré à ce jour)."
        historique={[]}
      />
    );

    expect(screen.getByText(/pas encore assez d'historique/i)).toBeInTheDocument();
  });

  it('surfaces the expected update cadence when history is insufficient (ORA-129)', () => {
    render(
      <PriceHistory
        status="insufficient_history"
        message="Pas encore assez d'historique de données pour observer une tendance (un seul snapshot enregistré à ce jour). De nouvelles données sont généralement ajoutées chaque semaine."
        historique={[]}
      />
    );

    expect(screen.getByText(/généralement ajoutées chaque semaine/i)).toBeInTheDocument();
  });

  // ORA-199 : le tableau devient une courbe ; 0/1/N points sont 3 cas distincts.
  describe('status "ok" (ORA-199)', () => {
    it('hides the block entirely with zero point (quartier sans historique, pas "insuffisant")', () => {
      const { container } = render(<PriceHistory status="ok" historique={[]} />);

      expect(container).toBeEmptyDOMElement();
    });

    it('shows the single value with an honest "not enough for a trend" note with exactly one point', () => {
      render(<PriceHistory status="ok" historique={[{ date: '2026-01-01', prix_m2_moyen: 20, count: 42 }]} />);

      expect(screen.getByText('20 €/m²')).toBeInTheDocument();
      expect(screen.getByText(/pas encore assez d'historique pour une tendance/i)).toBeInTheDocument();
    });

    it('renders an accessible chart (role=img) with two or more points', () => {
      render(
        <PriceHistory
          status="ok"
          historique={[
            { date: '2026-01-01', prix_m2_moyen: 20, count: 42 },
            { date: '2026-01-08', prix_m2_moyen: 21, count: 45 },
          ]}
        />
      );

      expect(screen.getByRole('img')).toBeInTheDocument();
    });

    it('summarizes the trend (first -> last value) in the aria-label, not just "chart"', () => {
      render(
        <PriceHistory
          status="ok"
          historique={[
            { date: '2026-01-01', prix_m2_moyen: 20, count: 42 },
            { date: '2026-01-08', prix_m2_moyen: 24, count: 45 },
          ]}
        />
      );

      const label = screen.getByRole('img').getAttribute('aria-label');
      expect(label).toMatch(/20/);
      expect(label).toMatch(/24/);
    });

    it('includes a visually-hidden table with the same values, for screen readers', () => {
      render(
        <PriceHistory
          status="ok"
          historique={[
            { date: '2026-01-01', prix_m2_moyen: 20, count: 42 },
            { date: '2026-01-08', prix_m2_moyen: 21, count: 45 },
          ]}
        />
      );

      const table = screen.getByRole('table', { hidden: true });
      expect(table.className).toMatch(/sr-only/);
      expect(within(table).getByText('42')).toBeInTheDocument();
      expect(within(table).getByText('45')).toBeInTheDocument();
    });

    it('shows a tooltip with the date, price and count on hovering a point', async () => {
      const user = userEvent.setup();
      render(
        <PriceHistory
          status="ok"
          historique={[
            { date: '2026-01-01', prix_m2_moyen: 20, count: 42 },
            { date: '2026-01-08', prix_m2_moyen: 21, count: 45 },
          ]}
        />
      );

      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();

      const [firstPoint] = screen.getAllByTestId('price-history-point');
      await user.hover(firstPoint);

      const tooltip = screen.getByRole('tooltip');
      expect(tooltip).toHaveTextContent('20');
      expect(tooltip).toHaveTextContent('42');
    });
  });
});
