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
  });

  it('renders the welcome message on mount', () => {
    render(<ChatOracle />);
    expect(screen.getByText(/Immotep est en ligne/)).toBeInTheDocument();
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

  it('disables the send button while input is empty', () => {
    render(<ChatOracle />);
    expect(screen.getByRole('button', { name: /envoyer le message/i })).toBeDisabled();
  });

  it('appends the analysis message when the analysis prop changes', () => {
    const { rerender } = render(<ChatOracle analysis={null} />);
    rerender(<ChatOracle analysis="Analyse du secteur Gerland." />);
    expect(screen.getByText('Analyse du secteur Gerland.')).toBeInTheDocument();
  });
});
