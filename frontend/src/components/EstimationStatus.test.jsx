import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import EstimationStatus from './EstimationStatus';

// ORA-198 : un état visuel explicite par code d'échec de /api/predict, au
// lieu d'un message générique unique ou d'un repli silencieux sur la moyenne.
describe('EstimationStatus', () => {
  it('renders nothing for an unrecognized or absent code', () => {
    const { container: withNull } = render(<EstimationStatus code={null} />);
    const { container: withBogus } = render(<EstimationStatus code="BOGUS" />);

    expect(withNull.firstChild).toBeNull();
    expect(withBogus.firstChild).toBeNull();
  });

  it('shows the "surface manquante" message and an action to go fill it in', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<EstimationStatus code="NO_SURFACE" onAction={onAction} />);

    expect(screen.getByText(/ajoute une surface/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /recherche/i }));
    expect(onAction).toHaveBeenCalled();
  });

  it('shows the "quartier inconnu du modèle" message with the real median, labeled as such', () => {
    render(<EstimationStatus code="UNKNOWN_QUARTIER" medianPrice={850} medianPriceM2={21} />);

    expect(screen.getByText(/le modèle ne connaît pas encore ce quartier/i)).toBeInTheDocument();
    expect(screen.getByText(/Médiane réelle\s*:/)).toBeInTheDocument();
    expect(screen.getByText(/850/)).toBeInTheDocument();
    expect(screen.getByText(/21/)).toBeInTheDocument();
  });

  it('does not show a median line when none is available', () => {
    render(<EstimationStatus code="UNKNOWN_QUARTIER" />);

    expect(screen.queryByText(/Médiane réelle\s*:/)).not.toBeInTheDocument();
  });

  it('shows the "estimation impossible" message with a "modifier les critères" action', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<EstimationStatus code="IMPLAUSIBLE" onAction={onAction} />);

    expect(screen.getByText(/estimation impossible pour ces critères/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /modifier les critères/i }));
    expect(onAction).toHaveBeenCalled();
  });

  it('shows the "oracle indisponible" message with a "réessayer" action', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<EstimationStatus code="MODEL_UNAVAILABLE" onAction={onAction} />);

    expect(screen.getByText(/momentanément indisponible/i)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /réessayer/i }));
    expect(onAction).toHaveBeenCalled();
  });

  it('exposes the message as an accessible status region', () => {
    render(<EstimationStatus code="MODEL_UNAVAILABLE" />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
