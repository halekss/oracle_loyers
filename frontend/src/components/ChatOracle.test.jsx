import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import ChatOracle from './ChatOracle';
import { ApiError } from '../services/api';

vi.mock('../services/api', async () => {
  const actual = await vi.importActual('../services/api');
  return {
    ...actual,
    api: { sendChatMessage: vi.fn() },
  };
});

import { api } from '../services/api';

describe('ChatOracle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('renders the welcome message on mount', () => {
    render(<ChatOracle />);
    expect(screen.getByText(/Immotep est en ligne/)).toBeInTheDocument();
  });

  it('restores a previously saved conversation from sessionStorage on mount (ORA-117)', () => {
    sessionStorage.setItem(
      'oracle-loyers:chat-history',
      JSON.stringify([
        { sender: 'oracle', text: "**Immotep est en ligne.**" },
        { sender: 'user', text: 'Un T2 à Gerland ?' },
        { sender: 'oracle', text: 'Ça tourne autour de 780 EUR.' },
      ]),
    );

    render(<ChatOracle />);

    expect(screen.getByText('Un T2 à Gerland ?')).toBeInTheDocument();
    expect(screen.getByText('Ça tourne autour de 780 EUR.')).toBeInTheDocument();
  });

  it('persists new messages to sessionStorage so a page refresh keeps them (ORA-117)', async () => {
    api.sendChatMessage.mockResolvedValue({ response: 'Gerland tourne autour de 780 EUR pour un T2.' });
    const user = userEvent.setup();

    render(<ChatOracle />);
    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      const stored = JSON.parse(sessionStorage.getItem('oracle-loyers:chat-history'));
      expect(stored.some((m) => m.text === 'Quel prix a Gerland ?')).toBe(true);
      expect(stored.some((m) => m.text.includes('780 EUR pour un T2'))).toBe(true);
    });
  });

  it('sends a message and displays the oracle response', async () => {
    api.sendChatMessage.mockResolvedValue({ response: 'Gerland tourne autour de 780 EUR pour un T2.' });
    const user = userEvent.setup();

    render(<ChatOracle />);

    const input = screen.getByPlaceholderText('Prix, surface, quartier...');
    await user.type(input, 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    expect(screen.getByText('Quel prix a Gerland ?')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/780 EUR pour un T2/)).toBeInTheDocument();
    });
    expect(api.sendChatMessage).toHaveBeenCalledWith('Quel prix a Gerland ?', expect.anything());
  });

  it('shows a themed message when the request is rate-limited', async () => {
    api.sendChatMessage.mockRejectedValue(new ApiError('Trop de requêtes (429)', { type: 'rate_limit' }));
    const user = userEvent.setup();

    render(<ChatOracle />);

    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Salut');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByText(/Doucement/)).toBeInTheDocument();
    });
  });

  it('shows a themed message on network failure', async () => {
    api.sendChatMessage.mockRejectedValue(new ApiError('Impossible de contacter le serveur', { type: 'network' }));
    const user = userEvent.setup();

    render(<ChatOracle />);

    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Salut');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByText(/Connexion perdue/)).toBeInTheDocument();
    });
  });

  it('shows a retry button on the failed user message after a send error (ORA-120)', async () => {
    api.sendChatMessage.mockRejectedValue(new ApiError('Erreur serveur (500)', { type: 'server' }));
    const user = userEvent.setup();

    render(<ChatOracle />);

    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    });
    // Le message original reste affiché, non effacé par l'échec
    expect(screen.getByText('Quel prix a Gerland ?')).toBeInTheDocument();
  });

  it('does not show a retry button after a successful send', async () => {
    api.sendChatMessage.mockResolvedValue({ response: 'Ça tourne autour de 780 EUR.' });
    const user = userEvent.setup();

    render(<ChatOracle />);

    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByText(/780 EUR/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
  });

  it('resends the same message content when the retry button is clicked, without retyping it (ORA-120)', async () => {
    api.sendChatMessage
      .mockRejectedValueOnce(new ApiError('Erreur serveur (500)', { type: 'server' }))
      .mockResolvedValueOnce({ response: 'Ça tourne autour de 780 EUR.' });
    const user = userEvent.setup();

    render(<ChatOracle />);

    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByTestId('retry-button')).toBeInTheDocument();
    });

    // L'input est vide : le renvoi doit se faire sans ressaisie
    expect(screen.getByPlaceholderText('Prix, surface, quartier...')).toHaveValue('');

    await user.click(screen.getByTestId('retry-button'));

    await waitFor(() => {
      expect(screen.getByText(/780 EUR/)).toBeInTheDocument();
    });

    expect(api.sendChatMessage).toHaveBeenCalledTimes(2);
    expect(api.sendChatMessage).toHaveBeenNthCalledWith(2, 'Quel prix a Gerland ?', expect.anything());
    // Une seule bulle utilisateur : le message n'a pas été dupliqué
    expect(screen.getAllByText('Quel prix a Gerland ?')).toHaveLength(1);
    expect(screen.queryByTestId('retry-button')).not.toBeInTheDocument();
  });

  it('disables the send button while input is empty', () => {
    render(<ChatOracle />);
    expect(screen.getByRole('button', { name: /envoyer le message/i })).toBeDisabled();
  });

  it('shows the remaining chat quota after a successful response (ORA-118)', async () => {
    api.sendChatMessage.mockResolvedValue({
      response: 'Gerland tourne autour de 780 EUR pour un T2.',
      rateLimit: { limit: 15, remaining: 12 },
    });
    const user = userEvent.setup();

    render(<ChatOracle />);
    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Quel prix a Gerland ?');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => {
      expect(screen.getByTestId('chat-quota')).toHaveTextContent(/12\s*\/\s*15/);
    });
  });

  it('does not show a quota indicator when the backend does not expose it', async () => {
    api.sendChatMessage.mockResolvedValue({ response: 'Réponse simple.' });
    const user = userEvent.setup();

    render(<ChatOracle />);
    await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Salut');
    await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

    await waitFor(() => expect(screen.getByText('Réponse simple.')).toBeInTheDocument());
    expect(screen.queryByTestId('chat-quota')).not.toBeInTheDocument();
  });

  it('appends the analysis message when the analysis prop changes', () => {
    const { rerender } = render(<ChatOracle analysis={null} />);
    rerender(<ChatOracle analysis="Analyse du secteur Gerland." />);
    expect(screen.getByText('Analyse du secteur Gerland.')).toBeInTheDocument();
  });

  describe('résultats riches, "Lister les N annonces" et suggestions (ORA-175)', () => {
    const structuredResponse = {
      response: 'Voici ce que je trouve.',
      recommendations: [
        { quartier: 'Guillotière / Jean Macé', type_local: 'T2', surface: 38, prix: 570 },
        { quartier: 'Montchat', type_local: 'T2', surface: 40, prix: 612 },
      ],
      matched_count: 67,
      parsed: { type_local: 'T2' },
    };

    it('shows the recommended listings as cards inside the oracle bubble', async () => {
      api.sendChatMessage.mockResolvedValue(structuredResponse);
      const user = userEvent.setup();

      render(<ChatOracle />);
      await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Un T2 sous 1000€');
      await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

      expect(await screen.findByText(/Guillotière \/ Jean Macé · T2 · 38 m²/)).toBeInTheDocument();
      expect(screen.getByText('570 €')).toBeInTheDocument();
    });

    it('shows "Lister les N annonces" when matched_count exceeds the shown recommendations', async () => {
      api.sendChatMessage.mockResolvedValue(structuredResponse);
      const onListAnnonces = vi.fn();
      const user = userEvent.setup();

      render(<ChatOracle onListAnnonces={onListAnnonces} />);
      await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Un T2 sous 1000€');
      await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

      const listButton = await screen.findByRole('button', { name: /lister les 67 annonces/i });
      await user.click(listButton);

      expect(onListAnnonces).toHaveBeenCalledWith('Guillotière / Jean Macé');
    });

    it('does not show the "Lister" CTA when all matches are already shown', async () => {
      api.sendChatMessage.mockResolvedValue({ ...structuredResponse, matched_count: 2 });
      const user = userEvent.setup();

      render(<ChatOracle />);
      await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Un T2 sous 1000€');
      await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

      await screen.findByText(/Guillotière/);
      expect(screen.queryByRole('button', { name: /lister les/i })).not.toBeInTheDocument();
    });

    it('offers a type suggestion chip and sends it as a new message when clicked', async () => {
      api.sendChatMessage
        .mockResolvedValueOnce(structuredResponse)
        .mockResolvedValueOnce({ response: 'Et voici pour un T3.' });
      const user = userEvent.setup();

      render(<ChatOracle />);
      await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Un T2 sous 1000€');
      await user.click(screen.getByRole('button', { name: /envoyer le message/i }));
      await screen.findByText(/Voici ce que je trouve/);

      const chip = screen.getByRole('button', { name: 'Et en T3 ?' });
      await user.click(chip);

      await waitFor(() => expect(screen.getByText('Et voici pour un T3.')).toBeInTheDocument());
      expect(api.sendChatMessage).toHaveBeenLastCalledWith('Et en T3 ?', expect.anything());
    });

    it('does not show a suggestion chip when the response has no specific type', async () => {
      api.sendChatMessage.mockResolvedValue({ response: 'Réponse générale.', parsed: {} });
      const user = userEvent.setup();

      render(<ChatOracle />);
      await user.type(screen.getByPlaceholderText('Prix, surface, quartier...'), 'Salut');
      await user.click(screen.getByRole('button', { name: /envoyer le message/i }));

      await screen.findByText('Réponse générale.');
      expect(screen.queryByRole('button', { name: /^Et en /i })).not.toBeInTheDocument();
    });
  });
});
