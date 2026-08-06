import { describe, expect, it, beforeEach } from 'vitest';
import { loadChatHistory, saveChatHistory } from './chatHistoryStorage.js';

describe('chatHistoryStorage', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('returns null when nothing has been saved', () => {
    expect(loadChatHistory()).toBeNull();
  });

  it('round-trips a saved message list', () => {
    const messages = [
      { sender: 'oracle', text: 'Bonjour' },
      { sender: 'user', text: 'Quel prix à Gerland ?' },
    ];

    saveChatHistory(messages);

    expect(loadChatHistory()).toEqual(messages);
  });

  it('persists via the sessionStorage key (ORA-117 : vide dans un nouvel onglet, sessionStorage n\'est jamais partagé entre onglets)', () => {
    saveChatHistory([{ sender: 'user', text: 'Salut' }]);

    expect(sessionStorage.getItem('oracle-loyers:chat-history')).not.toBeNull();
  });

  it('returns null instead of throwing when the stored value is corrupted JSON', () => {
    sessionStorage.setItem('oracle-loyers:chat-history', '{not valid json');

    expect(loadChatHistory()).toBeNull();
  });
});
