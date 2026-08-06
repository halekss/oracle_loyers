import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import SearchForm from './SearchForm';

describe('SearchForm', () => {
  it('renders the quartier input, surface input and filter buttons', () => {
    render(<SearchForm onScan={() => {}} isLoading={false} />);

    expect(screen.getByPlaceholderText(/entrez un quartier/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('m²')).toBeInTheDocument();
    ['Tout', 'T1', 'T2', 'T3', 'T4+'].forEach((label) => {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument();
    });
  });

  it('calls onScan with quartier, filter and surface on submit', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);

    await user.type(screen.getByPlaceholderText(/entrez un quartier/i), 'Gerland');
    await user.type(screen.getByPlaceholderText('m²'), '45');
    await user.click(screen.getByRole('button', { name: 'SCAN' }));

    expect(onScan).toHaveBeenCalledWith('Gerland', 'Tout', '45');
  });

  it('does not call onScan on submit when the quartier field is empty', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);
    await user.click(screen.getByRole('button', { name: 'SCAN' }));

    expect(onScan).not.toHaveBeenCalled();
  });

  it('re-triggers onScan immediately when a filter is clicked after typing a quartier', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);
    await user.type(screen.getByPlaceholderText(/entrez un quartier/i), 'Confluence');
    await user.click(screen.getByRole('button', { name: 'T2' }));

    expect(onScan).toHaveBeenCalledWith('Confluence', 'T2', '');
  });

  it('disables the SCAN button while loading', () => {
    render(<SearchForm onScan={() => {}} isLoading={true} />);
    expect(screen.getByRole('button', { name: '...' })).toBeDisabled();
  });

  it('does not call onScan on submit when the quartier field has a single character (ORA-111)', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);
    await user.type(screen.getByPlaceholderText(/entrez un quartier/i), 'G');
    await user.click(screen.getByRole('button', { name: 'SCAN' }));

    expect(onScan).not.toHaveBeenCalled();
  });

  it('does not re-trigger onScan on filter click when the quartier field has a single character (ORA-111)', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);
    await user.type(screen.getByPlaceholderText(/entrez un quartier/i), 'G');
    await user.click(screen.getByRole('button', { name: 'T2' }));

    expect(onScan).not.toHaveBeenCalled();
  });

  it('calls onScan on submit once the quartier field reaches two characters (ORA-111)', async () => {
    const onScan = vi.fn();
    const user = userEvent.setup();

    render(<SearchForm onScan={onScan} isLoading={false} />);
    await user.type(screen.getByPlaceholderText(/entrez un quartier/i), 'Ge');
    await user.click(screen.getByRole('button', { name: 'SCAN' }));

    expect(onScan).toHaveBeenCalledWith('Ge', 'Tout', '');
  });
});
