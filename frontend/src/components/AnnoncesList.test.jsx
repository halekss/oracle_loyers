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
});
