import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import AnnonceDetailModal from './AnnonceDetailModal';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { getAnnonceDetail: vi.fn(), logAnnonceClick: vi.fn(), exportEstimationPdf: vi.fn() },
  };
});

import { api } from '../services/api';

// ORA-174 : forme enrichie renvoyée par /api/annonces/:id depuis la refonte
// maquette 06 (services/annonce_detail.py) — coordonnées/type_local/
// quartier_prix_m2_moyen/cavaliers_detail en plus des champs annonces.db.
const detail = {
  id: 42,
  titre: 'T2 Gerland',
  prix: 850,
  surface: 45,
  ville: 'Lyon',
  quartier: 'Gerland',
  url: 'https://example.com/annonce-42',
  date_scraping: '2026-08-01T10:00:00+00:00',
  type_local: 'T2',
  prix_m2: 18.9,
  quartier_prix_m2_moyen: 20.0,
  cavaliers_detail: [
    { categorie: 'Vice', total: 12, empty_message: null, items: [{ poi: 'Bar', count: 12, dist_m: 46 }] },
    { categorie: 'Gentrification', total: 0, empty_message: 'Rien dans le rayon.', items: [] },
    { categorie: 'Nuisance', total: 5, empty_message: null, items: [{ poi: 'École', count: 5, dist_m: 157 }] },
    { categorie: 'Superstition', total: 0, empty_message: 'Rien dans le rayon. Cimetière les plus proches à 573 m.', items: [] },
  ],
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

  it('fetches and displays the annonce detail (maquette 06)', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

    expect(api.getAnnonceDetail).toHaveBeenCalledWith(42);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    expect(screen.getByText('T2 · Gerland')).toBeInTheDocument();
    expect(screen.getByText('45 m²')).toBeInTheDocument();
    expect(screen.getByText(/Appartement · Lyon · Gerland/)).toBeInTheDocument();
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
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /fermer/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes on Escape (ORA-174, a11y modale)', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={onClose} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    await user.keyboard('{Escape}');

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('traps Tab focus within the dialog (ORA-174, a11y modale)', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());

    const closeButton = screen.getByRole('button', { name: /fermer/i });
    const buttons = screen.getAllByRole('button');
    const lastButton = buttons[buttons.length - 1];

    lastButton.focus();
    await user.tab();
    expect(document.activeElement).toBe(closeButton);
  });

  it('restores focus to the previously focused element on close', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();

    const { unmount } = render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    unmount();

    expect(document.activeElement).toBe(opener);
    document.body.removeChild(opener);
  });

  it('logs the click and opens the sanitized source url when the CTA is clicked', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /voir l'annonce/i }));

    expect(api.logAnnonceClick).toHaveBeenCalledWith(42);
    expect(openSpy).toHaveBeenCalledWith('https://example.com/annonce-42', '_blank', 'noopener,noreferrer');
    openSpy.mockRestore();
  });

  it('labels the CTA with the derived source when recognized', async () => {
    api.getAnnonceDetail.mockResolvedValue({ ...detail, url: 'https://www.vizzit.fr/fr/property/abc' });

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());

    expect(screen.getByRole('button', { name: /voir sur vizzit/i })).toBeInTheDocument();
  });

  it('does not open a javascript: url when the CTA is clicked (ORA-126)', async () => {
    api.getAnnonceDetail.mockResolvedValue({ ...detail, url: 'javascript:alert(1)' });
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: /voir l'annonce/i }));

    expect(openSpy).not.toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('does not render an image, only a generic pictogram (ORA-133 : pas de photo tierce)', async () => {
    api.getAnnonceDetail.mockResolvedValue(detail);
    const { container } = render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
    await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());

    expect(container.querySelector('img')).not.toBeInTheDocument();
    expect(screen.getByText("Photo de l'annonce")).toBeInTheDocument();
  });

  describe('écart vs médiane et cavaliers autour (ORA-174)', () => {
    it('shows the écart % vs the quartier/type average', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

      // 18,9 vs 20,0 -> -6 %
      expect(await screen.findByText(/-6 % vs médiane du quartier/)).toBeInTheDocument();
    });

    it('shows one card per cavalier category with its total and closest distance', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

      await waitFor(() => expect(screen.getByText('Vice')).toBeInTheDocument());
      expect(screen.getByText('le plus proche 46 m')).toBeInTheDocument();
      expect(screen.getByText('Nuisance')).toBeInTheDocument();
      expect(screen.getByText('le plus proche 157 m')).toBeInTheDocument();
    });

    it('handles an empty cavalier category cleanly (no items, no closest distance)', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

      await waitFor(() => expect(screen.getByText('Superstition')).toBeInTheDocument());
      const supersitionCard = screen.getByText('Superstition').closest('div');
      expect(supersitionCard).toHaveTextContent('0');
    });

    it('does not show the cavaliers block when cavaliers_detail is absent (dataset row not matched)', async () => {
      api.getAnnonceDetail.mockResolvedValue({ ...detail, cavaliers_detail: undefined });
      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);

      await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
      expect(screen.queryByText(/Autour de l'appartement/)).not.toBeInTheDocument();
    });
  });

  describe('favori et export PDF (ORA-174)', () => {
    it('toggles the favorite state from the modal', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      const user = userEvent.setup();

      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
      await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());

      const favButton = screen.getByRole('button', { name: /ajouter aux favoris/i });
      await user.click(favButton);

      expect(screen.getByRole('button', { name: /retirer des favoris/i })).toBeInTheDocument();
    });

    it('exports a PDF built from the annonce and its cavaliers', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      api.exportEstimationPdf.mockResolvedValue(new Blob(['%PDF-1.4'], { type: 'application/pdf' }));
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
      URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      URL.revokeObjectURL = vi.fn();
      const user = userEvent.setup();

      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
      await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(api.exportEstimationPdf).toHaveBeenCalledWith(
          expect.objectContaining({ quartier: 'Gerland', estimated_price: 850, prix_m2: 18.9, type_local: 'T2' }),
        );
      });
    });

    it('shows an error message when the PDF export fails', async () => {
      api.getAnnonceDetail.mockResolvedValue(detail);
      api.exportEstimationPdf.mockRejectedValue(new Error('boom'));
      const user = userEvent.setup();

      render(<AnnonceDetailModal annonceId={42} onClose={() => {}} />);
      await waitFor(() => expect(screen.getByText('850 €')).toBeInTheDocument());
      await user.click(screen.getByRole('button', { name: /exporter en pdf/i }));

      await waitFor(() => {
        expect(screen.getByText(/erreur lors de l'export pdf/i)).toBeInTheDocument();
      });
    });
  });
});
