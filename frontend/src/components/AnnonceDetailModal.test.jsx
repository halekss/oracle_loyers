import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import AnnonceDetailModal from './AnnonceDetailModal';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { getAnnonceDetail: vi.fn(), logAnnonceClick: vi.fn() },
  };
});

import { api } from '../services/api';

const detail = {
  id: 42,
  titre: 'T2 Gerland',
  prix: 850,
  surface: 45,
  ville: 'Lyon',
  quartier: 'Gerland',
  url: 'https://example.com/annonce-42',
  date_scraping: '2026-08-01T10:00:00+00:00',
};

describe('AnnonceDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.logAnnonceClick.mockResolvedValue({ logged: true, views: 3 });
  });

  it('renders nothing when annonceId is null', () => {
    const { container } = render(<AnnonceDetailModal annonceId={null} onClose={() => {}} />);
    expect(container).toBeEmptyDOMElement();
    expect(api.getAnnonceDetail).not.toHaveBeenCalled();
  });

  it('fetches and displays the annonce detail', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

    expect(api.getAnnonceDetail).toHaveBeenCalledWith(42);
    await waitFor(() => expect(screen.getByText('T2 Gerland')).toBeInTheDocument());
    expect(screen.getByText('850 €')).toBeInTheDocument();
    expect(screen.getByText('45 m²')).toBeInTheDocument();
    expect(screen.getByText('Gerland')).toBeInTheDocument();
    expect(screen.getByText('Lyon')).toBeInTheDocument();
  });

  it('shows an error message when the fetch fails', async () => {
    api.getAnnonceDetail.mockRejectedValue(new Error('boom'));

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/une erreur inattendue est survenue/i)).toBeInTheDocument();
    });
  });

  it('calls onClose when the close button is clicked', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={onClose} />);
    await waitFor(() => expect(screen.getByText('T2 Gerland')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /fermer/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('logs the click and opens the source url when "Voir l\'annonce" is clicked', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('T2 Gerland')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /voir l'annonce/i }));

    expect(api.logAnnonceClick).toHaveBeenCalledWith(42);
    expect(openSpy).toHaveBeenCalledWith('https://example.com/annonce-42', '_blank', 'noopener,noreferrer');
    openSpy.mockRestore();
  });

  it('does not open a javascript: url when "Voir l\'annonce" is clicked (ORA-126)', async () => {
    api.getAnnonceDetail.mockResolvedValue({ ...detail, url: 'javascript:alert(1)' });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('T2 Gerland')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /voir l'annonce/i }));

    expect(openSpy).not.toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('does not render an image, only text fields (ORA-133 : pas de photo tierce)', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const { container } = render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('T2 Gerland')).toBeInTheDocument());

    expect(container.querySelector('img')).not.toBeInTheDocument();
  });
});
