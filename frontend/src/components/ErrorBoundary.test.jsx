import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import ErrorBoundary from './ErrorBoundary';

function Boom() {
  throw new Error('boom');
}

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <p>Tout va bien</p>
      </ErrorBoundary>,
    );

    expect(screen.getByText('Tout va bien')).toBeInTheDocument();
  });

  it('renders the default full-screen fallback when a child throws and no custom fallback is given', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );

    expect(screen.getByText(/problème d'affichage inattendu/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /recharger la page/i })).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('renders a custom compact fallback instead of the default one when provided (ORA-123)', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<p>Ce panneau a rencontré une erreur.</p>}>
        <Boom />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Ce panneau a rencontré une erreur.')).toBeInTheDocument();
    expect(screen.queryByText(/problème d'affichage inattendu/i)).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('isolates failures : one boundary catching an error does not affect a sibling boundary (ORA-123)', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <div>
        <ErrorBoundary fallback={<p>Panneau A en erreur</p>}>
          <Boom />
        </ErrorBoundary>
        <ErrorBoundary fallback={<p>Panneau B en erreur</p>}>
          <p>Panneau B intact</p>
        </ErrorBoundary>
      </div>,
    );

    expect(screen.getByText('Panneau A en erreur')).toBeInTheDocument();
    expect(screen.getByText('Panneau B intact')).toBeInTheDocument();
    expect(screen.queryByText('Panneau B en erreur')).not.toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('allows retrying without a full page reload when a custom fallback is a render function (ORA-123)', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const user = userEvent.setup();
    let shouldThrow = true;
    function MaybeBoom() {
      if (shouldThrow) throw new Error('boom');
      return <p>Rétabli</p>;
    }

    render(
      <ErrorBoundary fallback={(reset) => <button onClick={reset}>Réessayer</button>}>
        <MaybeBoom />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument();
    shouldThrow = false;
    await user.click(screen.getByRole('button', { name: 'Réessayer' }));

    expect(screen.getByText('Rétabli')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
