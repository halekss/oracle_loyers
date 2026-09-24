import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import SearchForm from './SearchForm';

const quartierOptions = [
  { quartier: 'Ainay', count: 31, prixM2Median: 19.6, arrondissement: 'Lyon 2e' },
  { quartier: 'Croix-Rousse Plateau', count: 61, prixM2Median: 22.0, arrondissement: 'Lyon 4e' },
  { quartier: 'Pentes Croix-Rousse', count: 28, prixM2Median: 19.9, arrondissement: 'Lyon 1er' },
  { quartier: 'Préfecture / Quais', count: 22, prixM2Median: 19.9, arrondissement: 'Lyon 6e' },
];

describe('SearchForm', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('scans on submit with the typed quartier, selected type and surface', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} autoFocus={false} />);
    await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
    await user.click(screen.getByRole('button', { name: 'T2' }));
    await user.click(screen.getByRole('button', { name: 'Scan' }));

    expect(onScan).toHaveBeenCalledWith('Ainay', 'T2', '');
  });

  it('switches ville via onVilleChange', async () => {
    const onVilleChange = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm ville="lyon" onVilleChange={onVilleChange} onScan={() => {}} isLoading={false} autoFocus={false} />);
    await user.click(screen.getByRole('button', { name: 'lille' }));

    expect(onVilleChange).toHaveBeenCalledWith('lille');
  });

  it('does not render a combobox/palette when quartierOptions is not provided (backward compatible)', () => {
    render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} autoFocus={false} />);
    expect(screen.getByLabelText('Quartier à scanner')).not.toHaveAttribute('role', 'combobox');
  });

  describe('accessibilité des contrôles segmentés', () => {
    it('marks Ville as a group of aria-pressed buttons', () => {
      render(<SearchForm ville="lille" onVilleChange={() => {}} onScan={() => {}} isLoading={false} autoFocus={false} />);

      expect(screen.getByRole('group', { name: 'Ville' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'lille' })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('button', { name: 'lyon' })).toHaveAttribute('aria-pressed', 'false');
    });

    it('marks Type de bien as a group of aria-pressed buttons, Tout selected by default', () => {
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} autoFocus={false} />);

      expect(screen.getByRole('group', { name: 'Type de bien' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Tout' })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByRole('button', { name: 'T2' })).toHaveAttribute('aria-pressed', 'false');
    });
  });

  describe('pré-remplissage (ORA-179, lien "Modifier")', () => {
    it('seeds the quartier/type/surface fields from the initial* props', () => {
      render(
        <SearchForm
          ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} autoFocus={false}
          initialQuartier="Ainay" initialTypeLocal="T2" initialSurface={45}
        />,
      );

      expect(screen.getByLabelText('Quartier à scanner')).toHaveValue('Ainay');
      expect(screen.getByRole('button', { name: 'T2' })).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByLabelText(/Surface en m²/)).toHaveValue(45);
    });
  });

  describe('palette de recherche', () => {
    it('filters quartiers as the user types, tolerant to accents/case', async () => {
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'PREFECTURE');

      expect(await screen.findByRole('option', { name: /Préfecture \/ Quais/ })).toBeInTheDocument();
      expect(screen.queryByRole('option', { name: /Ainay/ })).not.toBeInTheDocument();
    });

    it('shows both ambiguous matches for a partial query ("croix")', async () => {
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'croix');

      expect(await screen.findByRole('option', { name: /Croix-Rousse Plateau/ })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /Pentes Croix-Rousse/ })).toBeInTheDocument();
    });

    it('shows the arrondissement, annonce count and €/m² for each option', async () => {
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');

      expect(await screen.findByText(/Lyon 2e/)).toBeInTheDocument();
      expect(screen.getByText(/31 annonces/)).toBeInTheDocument();
      expect(screen.getByText(/19,6 €\/m²/)).toBeInTheDocument();
    });

    it('fills the quartier field when a suggestion is clicked, without scanning immediately (ORA-179 fix)', async () => {
      // Avant cette correction, cliquer une suggestion lançait le scan tout
      // de suite avec Type/Surface encore à leur valeur par défaut — sans
      // laisser le temps de les renseigner, et le menu ouvert recouvrait de
      // toute façon les boutons "Type de bien" en dessous (clic intercepté).
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await user.click(await screen.findByRole('option', { name: /Ainay/ }));

      expect(screen.getByLabelText('Quartier à scanner')).toHaveValue('Ainay');
      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      expect(onScan).not.toHaveBeenCalled();
    });

    it('lets the user pick a type and surface after selecting a suggestion, then scans on Scan click', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await user.click(await screen.findByRole('option', { name: /Ainay/ }));
      await user.click(screen.getByRole('button', { name: 'T2' }));
      await user.type(screen.getByLabelText(/Surface en m²/), '45');
      await user.click(screen.getByRole('button', { name: 'Scan' }));

      expect(onScan).toHaveBeenCalledWith('Ainay', 'T2', '45');
    });

    it('navigates with ArrowDown/ArrowUp and fills the highlighted option on Enter, without scanning immediately', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      const input = screen.getByLabelText('Quartier à scanner');
      await user.type(input, 'croix');
      await user.keyboard('{ArrowDown}{ArrowDown}{Enter}');

      // 2e option de la liste filtrée ("croix") = Pentes Croix-Rousse
      expect(input).toHaveValue('Pentes Croix-Rousse');
      expect(onScan).not.toHaveBeenCalled();
    });

    it('scans immediately when a recent search is clicked from the palette (distinct from a plain suggestion)', async () => {
      localStorage.setItem(
        'oracle-loyers:recent-searches',
        JSON.stringify([{ quartier: 'Ainay', typeLocal: 'T2', surface: '45', ville: 'lyon' }]),
      );
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.click(screen.getByLabelText('Quartier à scanner'));
      await user.click(await screen.findByRole('option', { name: /Ainay.*T2.*45 m²/ }));

      expect(onScan).toHaveBeenCalledWith('Ainay', 'T2', '45');
    });

    it('closes the palette on Escape without submitting', async () => {
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

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
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.click(screen.getByLabelText('Quartier à scanner'));

      expect(await screen.findAllByText('Recherches récentes')).toHaveLength(2); // palette + section dédiée
      expect(screen.getByRole('option', { name: /Ainay.*T2.*45 m²/ })).toBeInTheDocument();
    });

    it('records a new search in the recent searches history after scanning', async () => {
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');
      await user.keyboard('{Enter}');

      const stored = JSON.parse(localStorage.getItem('oracle-loyers:recent-searches'));
      expect(stored[0]).toMatchObject({ quartier: 'Ainay', ville: 'lyon' });
    });

    it('shows the keyboard hint footer', async () => {
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} quartierOptions={quartierOptions} autoFocus={false} />);

      await user.type(screen.getByLabelText('Quartier à scanner'), 'Ainay');

      expect(await screen.findByText(/naviguer.*Entrée valider.*Échap fermer/)).toBeInTheDocument();
    });
  });

  describe('recherches récentes (section dédiée, ORA-179)', () => {
    it('shows at most the 3 most recent searches, clickable to rescan', async () => {
      localStorage.setItem(
        'oracle-loyers:recent-searches',
        JSON.stringify([
          { quartier: 'Ainay', typeLocal: 'T2', surface: '45', ville: 'lyon' },
          { quartier: 'Gerland', typeLocal: 'T3', ville: 'lyon' },
          { quartier: 'Confluence', ville: 'lyon' },
          { quartier: 'Vaise', ville: 'lyon' },
          { quartier: 'Part-Dieu', ville: 'lyon' },
        ]),
      );
      const onScan = vi.fn();
      const user = userEvent.setup();
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={onScan} isLoading={false} autoFocus={false} />);

      const recentButtons = screen.getAllByRole('button', { name: /Scanner$/ });
      expect(recentButtons).toHaveLength(3);
      expect(screen.getByText(/Ainay.*T2.*45 m²/)).toBeInTheDocument();
      expect(screen.queryByText('Vaise')).not.toBeInTheDocument();

      await user.click(recentButtons[1]);
      expect(onScan).toHaveBeenCalledWith('Gerland', 'T3', '');
    });

    it('does not render the section when there is no recent search', () => {
      render(<SearchForm ville="lyon" onVilleChange={() => {}} onScan={() => {}} isLoading={false} autoFocus={false} />);
      expect(screen.queryByText('Recherches récentes')).not.toBeInTheDocument();
    });
  });
});
