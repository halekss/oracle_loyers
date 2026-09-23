import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import AnnonceCard from './AnnonceCard';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { logAnnonceClick: vi.fn(), getAnnonceDetail: vi.fn() },
  };
});

import { api } from '../services/api';

const baseAnnonce = {
  id: 42,
  titre: 'T2 Gerland',
  prix: 850,
  surface: 45,
  ville: 'Lyon',
  quartier: 'Gerland',
  url: 'https://example.com/annonce-42',
};

describe('AnnonceCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.logAnnonceClick.mockResolvedValue({ logged: true, views: 1 });
    localStorage.clear();
  });

  it('renders nothing when no annonce is given', () => {
    const { container } = render(<AnnonceCard annonce={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the price, surface, ville and quartier', () => {
    render(<AnnonceCard annonce={baseAnnonce} />);

    expect(screen.getByText('T2 Gerland')).toBeInTheDocument();
    expect(screen.getByText('850 €')).toBeInTheDocument();
    expect(screen.getByText('45 m²')).toBeInTheDocument();
    expect(screen.getByText('Lyon')).toBeInTheDocument();
    expect(screen.getByText('Gerland')).toBeInTheDocument();
  });

  it('falls back to a default title when missing', () => {
    render(<AnnonceCard annonce={{ ...baseAnnonce, titre: null }} />);
    expect(screen.getByText('Annonce sans titre')).toBeInTheDocument();
  });

  it('logs the click and opens the source url on click', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceCard annonce={baseAnnonce} />);
    await user.click(screen.getByRole('button', { name: /voir l'annonce : t2 gerland/i }));

    expect(api.logAnnonceClick).toHaveBeenCalledWith(42);
    expect(openSpy).toHaveBeenCalledWith('https://example.com/annonce-42', '_blank', 'noopener,noreferrer');
    openSpy.mockRestore();
  });

  it('opens the source url on Enter key press', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceCard annonce={baseAnnonce} />);
    screen.getByRole('button', { name: /voir l'annonce : t2 gerland/i }).focus();
    await user.keyboard('{Enter}');

    expect(openSpy).toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('does not fail when tracking the click errors out', async () => {
    api.logAnnonceClick.mockRejectedValue(new Error('network down'));
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceCard annonce={baseAnnonce} />);
    await user.click(screen.getByRole('button', { name: /voir l'annonce : t2 gerland/i }));

    expect(openSpy).toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('renders a generic illustration instead of any image (ORA-133 : pas de photo tierce)', () => {
    const { container } = render(<AnnonceCard annonce={baseAnnonce} />);

    expect(container.querySelector('img')).not.toBeInTheDocument();
    expect(container.querySelector('svg')).toBeInTheDocument();
  });

  it('does not open a javascript: url on click (ORA-126)', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    const user = userEvent.setup();

    render(<AnnonceCard annonce={{ ...baseAnnonce, url: 'javascript:alert(1)' }} />);
    await user.click(screen.getByRole('button', { name: /voir l'annonce : t2 gerland/i }));

    expect(openSpy).not.toHaveBeenCalled();
    openSpy.mockRestore();
  });

  it('opens the detail view on "Détails" click without triggering the external redirect (ORA-131)', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
    api.getAnnonceDetail = vi.fn().mockResolvedValue(baseAnnonce);
    const user = userEvent.setup();

    render(<AnnonceCard annonce={baseAnnonce} />);
    await user.click(screen.getByRole('button', { name: /détails/i }));

    expect(openSpy).not.toHaveBeenCalled();
    expect(api.getAnnonceDetail).toHaveBeenCalledWith(42);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    openSpy.mockRestore();
  });

  it.each([
    [20, 'Studio/T1'],
    [45, 'T2'],
    [65, 'T3'],
    [90, 'Grand (T4+)'],
  ])('falls back to a surface-derived label (%s m² -> %s) when the titre has no known category prefix', (surface, expectedLabel) => {
    render(<AnnonceCard annonce={{ ...baseAnnonce, titre: 'Sans préfixe connu', surface }} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  it('prefers the category parsed from the titre over the surface-derived one', () => {
    // 54 m² tomberait dans le seuil T2 par surface, mais le titre dit T3
    // (classification texte, plus fiable) : le titre doit gagner.
    render(<AnnonceCard annonce={{ ...baseAnnonce, titre: 'T3 — Monplaisir / Bachut', surface: 54 }} />);
    expect(screen.getByText('T3')).toBeInTheDocument();
    expect(screen.queryByText('T2')).not.toBeInTheDocument();
  });

  describe('favoris (ORA-132)', () => {
    it('renders an unfavorited toggle by default', () => {
      render(<AnnonceCard annonce={baseAnnonce} />);
      expect(screen.getByRole('button', { name: /ajouter aux favoris/i })).toBeInTheDocument();
    });

    it('toggles favorite state on click, persists to localStorage, and does not trigger the external redirect', async () => {
      const openSpy = vi.spyOn(window, 'open').mockImplementation(() => {});
      const user = userEvent.setup();

      render(<AnnonceCard annonce={baseAnnonce} />);
      await user.click(screen.getByRole('button', { name: /ajouter aux favoris/i }));

      expect(screen.getByRole('button', { name: /retirer des favoris/i })).toBeInTheDocument();
      expect(JSON.parse(localStorage.getItem('oracle-loyers:favorites'))).toEqual([42]);
      expect(openSpy).not.toHaveBeenCalled();

      await user.click(screen.getByRole('button', { name: /retirer des favoris/i }));
      expect(screen.getByRole('button', { name: /ajouter aux favoris/i })).toBeInTheDocument();
      expect(JSON.parse(localStorage.getItem('oracle-loyers:favorites'))).toEqual([]);

      openSpy.mockRestore();
    });

    it('persists the favorite across a re-mount (simulated reload)', async () => {
      const user = userEvent.setup();
      const { unmount } = render(<AnnonceCard annonce={baseAnnonce} />);

      await user.click(screen.getByRole('button', { name: /ajouter aux favoris/i }));
      unmount();

      render(<AnnonceCard annonce={baseAnnonce} />);
      expect(screen.getByRole('button', { name: /retirer des favoris/i })).toBeInTheDocument();
    });

    it('does not render a favorite toggle when the annonce has no id', () => {
      render(<AnnonceCard annonce={{ ...baseAnnonce, id: null }} />);
      expect(screen.queryByRole('button', { name: /favoris/i })).not.toBeInTheDocument();
    });

    it('does not throw when localStorage is unavailable (private browsing / quota)', async () => {
      const originalSet = Storage.prototype.setItem;
      Storage.prototype.setItem = () => {
        throw new Error('unavailable');
      };
      const user = userEvent.setup();

      render(<AnnonceCard annonce={baseAnnonce} />);
      await expect(
        user.click(screen.getByRole('button', { name: /ajouter aux favoris/i }))
      ).resolves.not.toThrow();

      // Le bascule reste utilisable en mémoire pour la session courante,
      // même si l'écriture disque échoue silencieusement.
      expect(screen.getByRole('button', { name: /retirer des favoris/i })).toBeInTheDocument();

      Storage.prototype.setItem = originalSet;
    });
  });
});
