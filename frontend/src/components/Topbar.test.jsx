import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import Topbar from './Topbar';

const quartierOptions = [
  { quartier: 'Ainay', count: 31, prixM2Median: 19.6 },
  { quartier: 'Croix-Rousse Plateau', count: 61, prixM2Median: 22.0 },
  { quartier: 'Pentes Croix-Rousse', count: 28, prixM2Median: 19.9 },
  { quartier: 'Préfecture / Quais', count: 22, prixM2Median: 19.9 },
];

describe('Topbar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('scans on submit with the typed quartier, active type filter and surface', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} />);
    await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
    await user.click(screen.getByRole('button', { name: 'T2' }));

    expect(onScan).toHaveBeenLastCalledWith('Ainay', 'T2', '');
  });

  it('switches ville via onVilleChange', async () => {
    const onVilleChange = vi.fn();
    const user = userEvent.setup();

    render(<Topbar ville="lyon" onVilleChange={onVilleChange} onScan={() => {}} isLoading={false} />);
    await user.click(screen.getByRole('button', { name: 'lille' }));

    expect(onVilleChange).toHaveBeenCalledWith('lille');
  });

  it('shows the "Données au" badge only when provided', () => {
    const { rerender } = render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} />);
    expect(screen.queryByText('Données au')).not.toBeInTheDocument();

    rerender(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} dataAsOf="12/08/2026" />);
    expect(screen.getByText('12/08/2026')).toBeInTheDocument();
  });

  it('does not render a combobox/palette when quartierOptions is not provided (backward compatible)', () => {
    render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} />);
    expect(screen.getByLabelText('Quartier à scanner')).not.toHaveAttribute('role', 'combobox');
  });

  describe('palette de recherche (ORA-176)', () => {
    it('marks the input as a combobox when quartierOptions is provided', () => {
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);
      expect(screen.getByLabelText('Quartier à scanner')).toHaveAttribute('role', 'combobox');
    });

    it('filters quartiers as the user types, tolerant to accents/case', async () => {
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'PREFECTURE');

      expect(await screen.findByRole('option', { name: /Préfecture \/ Quais/ })).toBeInTheDocument();
      expect(screen.queryByRole('option', { name: /Ainay/ })).not.toBeInTheDocument();
    });

    it('shows both ambiguous matches for a partial query ("croix")', async () => {
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'croix');

      expect(await screen.findByRole('option', { name: /Croix-Rousse Plateau/ })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Pentes Croix-Rousse/ })).toBeInTheDocument();
    });

    it('shows the annonce count and €/m² for each option', async () => {
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');

      expect(await screen.findByText(/31 annonces/)).toBeInTheDocument();
      expect(screen.getByText(/19,6 €\/m²/)).toBeInTheDocument();
    });

    it('scans immediately when an option is clicked', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await user.click(await screen.findByRole('option', { name: /Ainay/ }));

      expect(onScan).toHaveBeenCalledWith('Ainay', 'Tout', '');
    });

    it('navigates with ArrowDown/ArrowUp and selects the highlighted option on Enter', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} />);

      const input = screen.getByLabelText('Quartier à scanner');
      await user.type(input, 'croix');
      await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

      // 2e option de la liste filtrée ("croix") = Pentes Croix-Rousse
      expect(onScan).toHaveBeenCalledWith('Pentes Croix-Rousse', 'Tout', '');
    });

    it('closes the palette on Escape without submitting', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await screen.findByRole('listbox');
      await user.keyboard('{Escape}');

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      expect(onScan).not.toHaveBeenCalled();
    });

    it('shows recent searches when the field is empty and focused', async () => {
      localStorage.setItem(
        'oracle-loyers:recent-searches',
        JSON.stringify([{ quartier: 'Ainay', typeLocal: 'T2', surface: '45', ville: 'lyon' }]),
      );
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.click(screen.getByLabelText('Quartier à scanner'));

      expect(await screen.findByText('Recherches récentes')).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Ainay.*T2.*45 m²/ })).toBeInTheDocument();
    });

    it('records a new search in the recent searches history after scanning', async () => {
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await user.keyboard('{Enter}');

      const stored = JSON.parse(localStorage.getItem('oracle-loyers:recent-searches'));
      expect(stored[0]).toMatchObject({ quartier: 'Ainay', ville: 'lyon' });
    });

    it('shows the keyboard hint footer', async () => {
      const user = userEvent.setup();
      render(<Topbar ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');

      expect(await screen.findByText(/naviguer.*Entrée valider.*Échap fermer/)).toBeInTheDocument();
    });
  });
});
