import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { WatchlistTable } from '@/components/watchlist/WatchlistTable';
import type { WatchlistItem } from '@/types/api';

const items: WatchlistItem[] = [
  {
    symbol: 'NVDA',
    display_name: 'NVIDIA',
    asset_type: 'equity',
    position: 0,
    added_at: '',
    quote: {
      symbol: 'NVDA',
      name: 'NVIDIA Corporation',
      asset_type: 'equity',
      currency: 'USD',
      last_price: 180.5,
      previous_close: 192.4,
      move_pct: -6.2,
      retrieved_at: '',
      delayed_notice: '',
    },
  },
  {
    symbol: 'BTC-USD',
    display_name: 'Bitcoin',
    asset_type: 'crypto',
    position: 1,
    added_at: '',
    quote: null,
  },
];

describe('WatchlistTable', () => {
  it('shows prices, direction text (not colour only) and a Why? action', async () => {
    const onWhy = vi.fn();
    render(
      <MemoryRouter>
        <WatchlistTable items={items} onWhy={onWhy} />
      </MemoryRouter>,
    );
    expect(screen.getByText('NVIDIA Corporation')).toBeInTheDocument();
    expect(screen.getByText('$180.50')).toBeInTheDocument();
    expect(screen.getByText('-6.20%')).toBeInTheDocument();
    expect(screen.getByText('down')).toBeInTheDocument(); // screen-reader direction
    await userEvent.click(screen.getByRole('button', { name: 'Why did NVIDIA move?' }));
    expect(onWhy).toHaveBeenCalledWith(items[0]);
  });

  it('supports reorder and removal when editable', async () => {
    const onMove = vi.fn();
    const onRemove = vi.fn();
    render(
      <MemoryRouter>
        <WatchlistTable items={items} onWhy={vi.fn()} editable onMove={onMove} onRemove={onRemove} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: 'Move NVDA up' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Move NVDA down' }));
    expect(onMove).toHaveBeenCalledWith('NVDA', 1);
    await userEvent.click(screen.getByRole('button', { name: 'Remove BTC-USD' }));
    await waitFor(() => expect(onRemove).toHaveBeenCalledWith('BTC-USD'));
  });
});
