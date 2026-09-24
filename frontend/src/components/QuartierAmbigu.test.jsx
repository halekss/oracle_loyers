import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import QuartierAmbigu from './QuartierAmbigu';

const ambiguous = {
  query: 'croix',
  suggestions: ['Croix-Rousse Plateau', 'Pentes Croix-Rousse'],
};

const quartierOptions = [
  { quartier: 'Croix-Rousse Plateau', count: 61, prixM2Median: 22.0 },
  { quartier: 'Pentes Croix-Rousse', count: 28, prixM2Median: 19.9 },
];

describe('QuartierAmbigu', () => {
  it('renders nothing without suggestions', () => {
    const { container } = render(<QuartierAmbigu ambiguous={null} onSelect={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the ambiguous query and every suggestion', () => {
    render(<QuartierAmbigu ambiguous={ambiguous} quartierOptions={quartierOptions} onSelect={() => {}} />);

    expect(screen.getByText(/« croix »/)).toBeInTheDocument();
    expect(screen.getByText('Croix-Rousse Plateau')).toBeInTheDocument();
    expect(screen.getByText('Pentes Croix-Rousse')).toBeInTheDocument();
  });

  it('shows the count and €/m² for each suggestion when stats are available', () => {
    render(<QuartierAmbigu ambiguous={ambiguous} quartierOptions={quartierOptions} onSelect={() => {}} />);

    expect(screen.getByText(/61 annonces · 22 €\/m²/)).toBeInTheDocument();
    expect(screen.getByText(/28 annonces · 19,9 €\/m²/)).toBeInTheDocument();
  });

  it('calls onSelect with the exact quartier name when a suggestion is clicked', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<QuartierAmbigu ambiguous={ambiguous} quartierOptions={quartierOptions} onSelect={onSelect} />);

    await user.click(screen.getByRole('button', { name: /Pentes Croix-Rousse/ }));

    expect(onSelect).toHaveBeenCalledWith('Pentes Croix-Rousse');
  });

  it('still renders a usable button without matching stats', () => {
    render(<QuartierAmbigu ambiguous={ambiguous} quartierOptions={[]} onSelect={() => {}} />);

    expect(screen.getByRole('button', { name: 'Croix-Rousse Plateau' })).toBeInTheDocument();
  });
});
