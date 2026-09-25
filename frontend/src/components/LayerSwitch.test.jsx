import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import LayerSwitch from './LayerSwitch';

describe('LayerSwitch', () => {
  it('is a real switch reflecting `checked` via aria-checked', () => {
    render(<LayerSwitch checked label="Métro & stations" onChange={() => {}} />);
    expect(screen.getByRole('switch', { name: 'Métro & stations' })).toHaveAttribute('aria-checked', 'true');
  });

  it('reflects an off state', () => {
    render(<LayerSwitch checked={false} label="Métro & stations" onChange={() => {}} />);
    expect(screen.getByRole('switch', { name: 'Métro & stations' })).toHaveAttribute('aria-checked', 'false');
  });

  it('calls onChange when clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LayerSwitch checked label="Métro & stations" onChange={onChange} />);

    await user.click(screen.getByRole('switch', { name: 'Métro & stations' }));

    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('is reachable and activable from the keyboard alone (Tab, then Enter/Space)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<LayerSwitch checked label="Métro & stations" onChange={onChange} />);

    await user.tab();
    expect(screen.getByRole('switch', { name: 'Métro & stations' })).toHaveFocus();
    await user.keyboard('{Enter}');

    expect(onChange).toHaveBeenCalledTimes(1);
  });
});
