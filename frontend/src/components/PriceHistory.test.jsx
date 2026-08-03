import { render, screen } from '@testing-library/react';
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

  it('renders a table row per historical data point when history is available', () => {
    render(
      <PriceHistory
        status="ok"
        historique={[
          { date: '2026-01-01T00:00:00+00:00', prix_m2_moyen: 20, count: 42 },
          { date: '2026-01-08T00:00:00+00:00', prix_m2_moyen: 21, count: 45 },
        ]}
      />
    );

    expect(screen.getByText('20 €')).toBeInTheDocument();
    expect(screen.getByText('21 €')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('45')).toBeInTheDocument();
  });
});
