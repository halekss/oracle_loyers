import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import CavalierRow from './CavalierRow';

const viceDetail = {
  categorie: 'Vice',
  total: 19,
  items: [
    { poi: 'Bar', count: 12, dist_m: 46 },
    { poi: 'Tabac', count: 3, dist_m: 158 },
    { poi: 'Cbd shop', count: 2, dist_m: 159 },
    { poi: 'Kebab', count: 2, dist_m: 54 },
  ],
  empty_message: null,
};

const superstitionDetail = {
  categorie: 'Superstition',
  total: 0,
  items: [],
  empty_message: 'Rien dans le rayon. Pompes funèbres les plus proches à 573 m.',
};

const baseProps = {
  categorie: 'Vice',
  color: '#F87171',
  shape: 'circle',
  isVisible: true,
  onToggleVisibility: vi.fn(),
  isExpanded: false,
  onToggleExpand: vi.fn(),
};

describe('CavalierRow', () => {
  it('always shows the category name as text, never relying on color alone', () => {
    render(<CavalierRow {...baseProps} detail={viceDetail} />);
    expect(screen.getByText('Vice')).toBeInTheDocument();
  });

  it('marks the shape icon as decorative (aria-hidden)', () => {
    render(<CavalierRow {...baseProps} detail={viceDetail} />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows "N lieux · dès X m" when the category has lieux in range', () => {
    render(<CavalierRow {...baseProps} detail={viceDetail} />);
    expect(screen.getByText('19 lieux · dès 46 m')).toBeInTheDocument();
  });

  it('shows "0 · le 1er à X m" when the category is empty', () => {
    render(<CavalierRow {...baseProps} categorie="Superstition" detail={superstitionDetail} />);
    expect(screen.getByText('0 · le 1er à 573 m')).toBeInTheDocument();
  });

  it('renders a real switch reflecting isVisible via aria-checked', () => {
    render(<CavalierRow {...baseProps} detail={viceDetail} isVisible={false} />);
    const switchButton = screen.getByRole('switch', { name: /vice/i });
    expect(switchButton).toHaveAttribute('aria-checked', 'false');
  });

  it('calls onToggleVisibility when the switch is clicked, without expanding the row', async () => {
    const user = userEvent.setup();
    const onToggleVisibility = vi.fn();
    const onToggleExpand = vi.fn();
    render(<CavalierRow {...baseProps} detail={viceDetail} onToggleVisibility={onToggleVisibility} onToggleExpand={onToggleExpand} />);

    await user.click(screen.getByRole('switch', { name: /vice/i }));

    expect(onToggleVisibility).toHaveBeenCalledTimes(1);
    expect(onToggleExpand).not.toHaveBeenCalled();
  });

  it('exposes the expand control as a real aria-expanded/aria-controls button', () => {
    render(<CavalierRow {...baseProps} detail={viceDetail} isExpanded={false} />);
    const expandButton = screen.getByRole('button', { name: /vice/i });
    expect(expandButton).toHaveAttribute('aria-expanded', 'false');
    expect(expandButton).toHaveAttribute('aria-controls');
  });

  it('calls onToggleExpand when the row (not the switch) is clicked', async () => {
    const user = userEvent.setup();
    const onToggleExpand = vi.fn();
    render(<CavalierRow {...baseProps} detail={viceDetail} onToggleExpand={onToggleExpand} />);

    await user.click(screen.getByRole('button', { name: /vice/i }));

    expect(onToggleExpand).toHaveBeenCalledTimes(1);
  });

  it('shows the sub-category breakdown and the humorous phrase only when expanded', () => {
    const { rerender } = render(
      <CavalierRow {...baseProps} detail={viceDetail} phrase="12 bars, le premier à 46 m." isExpanded={false} />,
    );
    expect(screen.queryByText('Bar')).not.toBeInTheDocument();
    expect(screen.queryByText('12 bars, le premier à 46 m.')).not.toBeInTheDocument();

    rerender(<CavalierRow {...baseProps} detail={viceDetail} phrase="12 bars, le premier à 46 m." isExpanded={true} />);

    expect(screen.getByText('Bar')).toBeInTheDocument();
    expect(screen.getByText('dès 46 m')).toBeInTheDocument();
    expect(screen.getByText('12 bars, le premier à 46 m.')).toBeInTheDocument();
  });

  it('renders in simplified mode (no meta, no expand control) when detail is not provided (no scan yet)', () => {
    render(<CavalierRow {...baseProps} detail={undefined} />);

    expect(screen.getByText('Vice')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /vice/i })).not.toBeInTheDocument();
    expect(screen.getByRole('switch', { name: /vice/i })).toBeInTheDocument();
  });

  it('still allows toggling visibility in simplified mode', async () => {
    const user = userEvent.setup();
    const onToggleVisibility = vi.fn();
    render(<CavalierRow {...baseProps} detail={undefined} onToggleVisibility={onToggleVisibility} />);

    await user.click(screen.getByRole('switch', { name: /vice/i }));

    expect(onToggleVisibility).toHaveBeenCalledTimes(1);
  });

  describe('rayon "Aucun" (totaux ville, sans distance)', () => {
    const villeWideDetail = {
      categorie: 'Vice',
      total: 546,
      items: [{ poi: 'Bar', count: 320 }, { poi: 'Kebab', count: 226 }],
      empty_message: null,
    };

    it('shows "N lieux à <ville>" instead of a distance when radiusM is null', () => {
      render(<CavalierRow {...baseProps} detail={villeWideDetail} radiusM={null} villeLabel="Lyon" />);

      expect(screen.getByText('546 lieux à Lyon')).toBeInTheDocument();
    });

    it('never shows a per-item distance when radiusM is null', () => {
      render(
        <CavalierRow
          {...baseProps}
          detail={villeWideDetail}
          radiusM={null}
          villeLabel="Lyon"
          isExpanded
        />,
      );

      expect(screen.getByText('Bar')).toBeInTheDocument();
      expect(screen.queryByText(/dès \d+ m/)).not.toBeInTheDocument();
    });

    it('hides the humorous phrase when radiusM is null (no phrase provided)', () => {
      render(
        <CavalierRow {...baseProps} detail={villeWideDetail} radiusM={null} villeLabel="Lyon" phrase={undefined} isExpanded />,
      );

      expect(screen.queryByText(/parfait pour un verre/i)).not.toBeInTheDocument();
    });
  });

  describe('changement de rayon en cours (isLoading)', () => {
    it('shows a skeleton placeholder instead of the meta text while loading', () => {
      render(<CavalierRow {...baseProps} detail={viceDetail} isLoading />);

      expect(screen.queryByText('19 lieux · dès 46 m')).not.toBeInTheDocument();
      expect(screen.getByTestId('cavalier-meta-skeleton')).toBeInTheDocument();
    });

    it('still shows the name, shape and switch while loading (only the meta is a skeleton)', () => {
      render(<CavalierRow {...baseProps} detail={viceDetail} isLoading />);

      expect(screen.getByText('Vice')).toBeInTheDocument();
      expect(screen.getByRole('switch', { name: /vice/i })).toBeInTheDocument();
    });

    it('does not show stale expanded detail while loading', () => {
      render(<CavalierRow {...baseProps} detail={viceDetail} phrase="12 bars." isExpanded isLoading />);

      expect(screen.queryByText('Bar')).not.toBeInTheDocument();
      expect(screen.queryByText('12 bars.')).not.toBeInTheDocument();
    });

    it('shows the real meta again once isLoading turns back to false', () => {
      const { rerender } = render(<CavalierRow {...baseProps} detail={viceDetail} isLoading />);
      expect(screen.getByTestId('cavalier-meta-skeleton')).toBeInTheDocument();

      rerender(<CavalierRow {...baseProps} detail={viceDetail} isLoading={false} />);

      expect(screen.queryByTestId('cavalier-meta-skeleton')).not.toBeInTheDocument();
      expect(screen.getByText('19 lieux · dès 46 m')).toBeInTheDocument();
    });
  });
});
