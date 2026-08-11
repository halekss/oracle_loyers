import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import AnnoncesList from './AnnoncesList';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { getAnnonces: vi.fn(), logAnnonceClick: vi.fn(), getListings: vi.fn() },
  };
});

import { api } from '../services/api';

const makeAnnonce = (id) => ({
  id,
  titre: `Annonce ${id}`,
  prix: 800 + id,
  surface: 40,
  ville: 'Lyon',
  quartier: 'Gerland',
  url: `https://example.com/${id}`,
});

describe('AnnoncesList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getListings.mockResolvedValue([
      { quartier: 'Gerland' },
      { quartier: 'Confluence' },
      { quartier: 'Gerland' },
      { quartier: 'Vieux Lyon' },
    ]);
  });

  it('renders a loading skeleton while fetching', () => {
    api.getAnnonces.mockReturnValue(new Promise(() => {}));
    const { container } = render(<AnnoncesList />);
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('renders the fetched annonces', async () => {
    api.getAnnonces.mockResolvedValue({
      items: [makeAnnonce(1), makeAnnonce(2)],
      page: 1,
      total_pages: 1,
    });

    render(<AnnoncesList />);

    await waitFor(() => {
      expect(screen.getByText('Annonce 1')).toBeInTheDocument();
    });
    expect(screen.getByText('Annonce 2')).toBeInTheDocument();
  });

  it('shows an empty state message when there are no annonces', async () => {
    api.getAnnonces.mockResolvedValue({ items: [], page: 1, total_pages: 0 });

    render(<AnnoncesList />);

    await waitFor(() => {
      expect(screen.getByText(/aucune annonce disponible/i)).toBeInTheDocument();
    });
  });

  it('shows an error message when the fetch fails', async () => {
    api.getAnnonces.mockRejectedValue(new Error('boom'));

    render(<AnnoncesList />);

    await waitFor(() => {
      expect(screen.getByText(/une erreur inattendue est survenue/i)).toBeInTheDocument();
    });
  });

  it('paginates to the next page on click', async () => {
    api.getAnnonces.mockImplementation(({ page }) =>
      Promise.resolve({
        items: [makeAnnonce(page)],
        page,
        total_pages: 2,
      })
    );
    const user = userEvent.setup();

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByText('Annonce 1')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /suivant/i }));

    await waitFor(() => expect(screen.getByText('Annonce 2')).toBeInTheDocument());
    expect(api.getAnnonces).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 })
    );
  });

  it('reports the fetched items via onItemsChange (ORA-105)', async () => {
    api.getAnnonces.mockResolvedValue({
      items: [makeAnnonce(1), makeAnnonce(2)],
      page: 1,
      total_pages: 1,
    });
    const onItemsChange = vi.fn();

    render(<AnnoncesList onItemsChange={onItemsChange} />);

    await waitFor(() => {
      expect(onItemsChange).toHaveBeenCalledWith([makeAnnonce(1), makeAnnonce(2)]);
    });
  });

  it('offers a quartier filter with the distinct quartiers from /api/listings (ORA-115)', async () => {
    api.getAnnonces.mockResolvedValue({ items: [makeAnnonce(1)], page: 1, total_pages: 1 });

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByLabelText(/quartier/i)).toBeInTheDocument());
    const select = screen.getByLabelText(/quartier/i);
    const optionLabels = Array.from(select.querySelectorAll('option')).map((o) => o.textContent);
    expect(optionLabels).toEqual(['Tous les quartiers', 'Confluence', 'Gerland', 'Vieux Lyon']);
  });

  it('refetches with the selected quartier and resets to page 1 (ORA-115)', async () => {
    api.getAnnonces.mockResolvedValue({ items: [makeAnnonce(1)], page: 1, total_pages: 1 });
    const user = userEvent.setup();

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByLabelText(/quartier/i)).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(/quartier/i), 'Gerland');

    await waitFor(() => {
      expect(api.getAnnonces).toHaveBeenLastCalledWith(
        expect.objectContaining({ quartier: 'Gerland', page: 1 })
      );
    });
  });

  it('keeps the filter usable when the filtered result is empty (ORA-115)', async () => {
    api.getAnnonces.mockResolvedValue({ items: [], page: 1, total_pages: 0 });

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByText(/aucune annonce disponible/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/quartier/i)).toBeInTheDocument();
  });

  it('changes the displayed order when a sort option is selected (ORA-127)', async () => {
    api.getAnnonces.mockImplementation(({ sort, order }) => {
      const items = sort === 'prix' && order === 'asc'
        ? [makeAnnonce(2), makeAnnonce(1)]
        : [makeAnnonce(1), makeAnnonce(2)];
      return Promise.resolve({ items, page: 1, total_pages: 1 });
    });
    const user = userEvent.setup();

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByText('Annonce 1')).toBeInTheDocument());
    const titlesBefore = screen.getAllByText(/^Annonce \d$/).map((el) => el.textContent);
    expect(titlesBefore).toEqual(['Annonce 1', 'Annonce 2']);

    await user.selectOptions(screen.getByLabelText(/trier/i), 'prix-asc');

    await waitFor(() => {
      expect(api.getAnnonces).toHaveBeenLastCalledWith(
        expect.objectContaining({ sort: 'prix', order: 'asc', page: 1 })
      );
    });
    const titlesAfter = screen.getAllByText(/^Annonce \d$/).map((el) => el.textContent);
    expect(titlesAfter).toEqual(['Annonce 2', 'Annonce 1']);
  });

  it('resets to page 1 when the sort option changes (ORA-127)', async () => {
    api.getAnnonces.mockImplementation(({ page }) =>
      Promise.resolve({ items: [makeAnnonce(page)], page, total_pages: 2 })
    );
    const user = userEvent.setup();

    render(<AnnoncesList />);

    await waitFor(() => expect(screen.getByText('Annonce 1')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /suivant/i }));
    await waitFor(() => expect(screen.getByText('Annonce 2')).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText(/trier/i), 'surface-desc');

    await waitFor(() => {
      expect(api.getAnnonces).toHaveBeenLastCalledWith(
        expect.objectContaining({ sort: 'surface', order: 'desc', page: 1 })
      );
    });
  });

  it('jumps to the scanned quartier annonces when focusedQuartier is set (ORA-127)', async () => {
    api.getAnnonces.mockResolvedValue({ items: [makeAnnonce(1)], page: 1, total_pages: 1 });

    const { rerender } = render(<AnnoncesList />);
    await waitFor(() => expect(screen.getByLabelText(/quartier/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/quartier/i).value).toBe('');

    rerender(<AnnoncesList focusedQuartier={{ quartier: 'Gerland', token: 1 }} />);

    await waitFor(() => {
      expect(api.getAnnonces).toHaveBeenLastCalledWith(
        expect.objectContaining({ quartier: 'Gerland', page: 1 })
      );
    });
    expect(screen.getByLabelText(/quartier/i).value).toBe('Gerland');
  });

  it('re-jumps to the same quartier when focusedQuartier token changes again (ORA-127)', async () => {
    api.getAnnonces.mockResolvedValue({ items: [makeAnnonce(1)], page: 1, total_pages: 1 });
    const user = userEvent.setup();

    const { rerender } = render(<AnnoncesList focusedQuartier={{ quartier: 'Gerland', token: 1 }} />);
    await waitFor(() => expect(screen.getByLabelText(/quartier/i).value).toBe('Gerland'));

    // L'utilisateur change le filtre manuellement...
    await user.selectOptions(screen.getByLabelText(/quartier/i), 'Confluence');
    await waitFor(() => expect(screen.getByLabelText(/quartier/i).value).toBe('Confluence'));

    // ...puis re-scanne le même quartier (nouveau token) : le lien doit à
    // nouveau imposer le filtre, même si `quartier` est identique.
    rerender(<AnnoncesList focusedQuartier={{ quartier: 'Gerland', token: 2 }} />);

    await waitFor(() => expect(screen.getByLabelText(/quartier/i).value).toBe('Gerland'));
  });
});
