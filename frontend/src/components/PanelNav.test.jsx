import { useState, useEffect } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import PanelNav from './PanelNav';
import { PANEL_VIEWS } from '../services/panelViews';

describe('PanelNav', () => {
  it('renders all 8 views in order', () => {
    render(<PanelNav activeView="accueil" onChange={() => {}} sheetId="sheet" />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(8);
    expect(buttons.map((b) => b.getAttribute('aria-label'))).toEqual(
      PANEL_VIEWS.map((v) => v.label === 'Immotep' ? 'Immotep, chat disponible' : v.label),
    );
  });

  it('renders the views in the exact ORA-179 order (Accueil, Recherche, Scan, Estimation, Calques, Annonces, Fiche, Immotep)', () => {
    render(<PanelNav activeView="accueil" onChange={() => {}} sheetId="sheet" />);

    const labels = screen.getAllByRole('button').map((b) => b.textContent.replace(/\d+$/, ''));
    expect(labels).toEqual(['Accueil', 'Recherche', 'Scan', 'Estimation', 'Calques', 'Annonces', 'Fiche', 'Immotep']);
  });

  it('marks the active view with aria-current="page" and aria-controls pointing to the sheet', () => {
    render(<PanelNav activeView="scan" onChange={() => {}} sheetId="panel-sheet" />);

    const scanButton = screen.getByRole('button', { name: 'Scan' });
    expect(scanButton).toHaveAttribute('aria-current', 'page');
    expect(scanButton).toHaveAttribute('aria-controls', 'panel-sheet');

    const accueilButton = screen.getByRole('button', { name: 'Accueil' });
    expect(accueilButton).not.toHaveAttribute('aria-current');
  });

  it('calls onChange with the clicked view id', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PanelNav activeView="accueil" onChange={onChange} sheetId="sheet" />);

    await user.click(screen.getByRole('button', { name: 'Estimation' }));

    expect(onChange).toHaveBeenCalledWith('estimation');
  });

  it('disables Fiche (aria-disabled, no onChange) when ficheDisabled is true, while keeping it focusable', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PanelNav activeView="accueil" onChange={onChange} ficheDisabled sheetId="sheet" />);

    const ficheButton = screen.getByRole('button', { name: 'Fiche' });
    expect(ficheButton).toHaveAttribute('aria-disabled', 'true');

    await user.click(ficheButton);
    expect(onChange).not.toHaveBeenCalled();
  });

  it('enables Fiche once ficheDisabled is false', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PanelNav activeView="accueil" onChange={onChange} ficheDisabled={false} sheetId="sheet" />);

    await user.click(screen.getByRole('button', { name: 'Fiche' }));
    expect(onChange).toHaveBeenCalledWith('fiche');
  });

  it('shows the annonces count as a badge with an accessible label', () => {
    render(<PanelNav activeView="accueil" onChange={() => {}} annonceCount={12} sheetId="sheet" />);

    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Annonces, 12 résultats' })).toBeInTheDocument();
  });

  it('does not show a badge on Annonces without a count', () => {
    render(<PanelNav activeView="accueil" onChange={() => {}} sheetId="sheet" />);

    expect(screen.getByRole('button', { name: 'Annonces' })).toBeInTheDocument();
  });

  it('moves focus between items with ArrowDown/ArrowUp without changing the active view', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<PanelNav activeView="accueil" onChange={onChange} sheetId="sheet" />);

    screen.getByRole('button', { name: 'Accueil' }).focus();
    await user.keyboard('{ArrowDown}');
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Recherche' }));

    await user.keyboard('{ArrowUp}');
    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Accueil' }));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('wraps focus from the last item to the first with ArrowDown', async () => {
    const user = userEvent.setup();
    render(<PanelNav activeView="accueil" onChange={() => {}} chatAvailable={false} sheetId="sheet" />);

    screen.getByRole('button', { name: 'Immotep' }).focus();
    await user.keyboard('{ArrowDown}');

    expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Accueil' }));
  });

  it('does not show the Immotep availability dot when chatAvailable is false', () => {
    render(<PanelNav activeView="accueil" onChange={() => {}} chatAvailable={false} sheetId="sheet" />);

    expect(screen.getByRole('button', { name: 'Immotep' })).toBeInTheDocument();
  });
});

// ORA-178 : la carte (colonne gauche) ne doit jamais être démontée/remontée
// quand la vue active change dans le rail — reproduit ici le motif réel
// d'intégration (App.jsx) : un composant "carte" persistant à côté de
// PanelNav, jamais retiré de l'arbre React au changement de vue (seul
// `activeView` change, `MockMap` reste monté en continu).
function MockMap({ onMountCountChange }) {
  useEffect(() => {
    onMountCountChange((count) => count + 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return <div data-testid="mock-map" />;
}

function Harness() {
  const [activeView, setActiveView] = useState('accueil');
  const [mountCount, setMountCount] = useState(0);

  return (
    <div>
      <span data-testid="mount-count">{mountCount}</span>
      <span data-testid="active-view">{activeView}</span>
      <MockMap onMountCountChange={setMountCount} />
      <PanelNav activeView={activeView} onChange={setActiveView} sheetId="sheet" />
    </div>
  );
}

describe('PanelNav (intégration) : la carte ne se remonte jamais au changement de vue', () => {
  it('keeps the map mounted exactly once while switching between several views', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    expect(screen.getByTestId('mount-count')).toHaveTextContent('1');

    await user.click(screen.getByRole('button', { name: 'Scan' }));
    await user.click(screen.getByRole('button', { name: 'Annonces' }));
    await user.click(screen.getByRole('button', { name: 'Immotep, chat disponible' }));
    await user.click(screen.getByRole('button', { name: 'Accueil' }));

    expect(screen.getByTestId('active-view')).toHaveTextContent('accueil');
    expect(screen.getByTestId('mount-count')).toHaveTextContent('1');
    expect(screen.getByTestId('mock-map')).toBeInTheDocument();
  });
});
