import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import Topbar from './Topbar';

// ORA-179 : la barre supérieure ne porte plus la recherche (déménagée dans
// SearchForm, cf. SearchForm.test.jsx pour cette couverture) — ne reste que
// le logo et le badge de fraîcheur des données.
describe('Topbar', () => {
  it('renders the logo', () => {
    render(<Topbar />);
    expect(screen.getByText('ORACLE')).toBeInTheDocument();
    expect(screen.getByText('DES LOYERS')).toBeInTheDocument();
  });

  it('shows the "Données au" badge only when provided', () => {
    const { rerender } = render(<Topbar />);
    expect(screen.queryByText('Données au')).not.toBeInTheDocument();

    rerender(<Topbar dataAsOf="12/08/2026" />);
    expect(screen.getByText('12/08/2026')).toBeInTheDocument();
  });

  it('no longer exposes any search control (moved to SearchForm)', () => {
    render(<Topbar dataAsOf="12/08/2026" />);
    expect(screen.queryByLabelText('Quartier à scanner')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Scan' })).not.toBeInTheDocument();
  });
});
