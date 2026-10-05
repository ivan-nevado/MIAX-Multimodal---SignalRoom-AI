import { Link } from 'react-router-dom';
import { ArrowDown, ArrowUp, Sparkles, Trash2 } from 'lucide-react';
import type { WatchlistItem } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Change } from '@/components/ui/change';
import { Badge } from '@/components/ui/badge';
import { formatPrice, priceCurrency, titleCase } from '@/lib/formatting';

interface Props {
  items: WatchlistItem[];
  onWhy: (item: WatchlistItem) => void;
  editable?: boolean;
  onRemove?: (symbol: string) => void;
  onMove?: (symbol: string, delta: -1 | 1) => void;
}

/** Watchlist with prominent "Why?" actions. */
export function WatchlistTable({ items, onWhy, editable, onRemove, onMove }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-sm">
        <thead>
          <tr className="text-left text-[11px] tracking-wide text-ink-3 uppercase">
            <th className="pb-2 font-medium">Asset</th>
            <th className="pb-2 text-right font-medium">Price</th>
            <th className="pb-2 text-right font-medium">Change</th>
            <th className="pb-2 text-right font-medium">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.symbol} className="border-t border-line/70">
              <td className="py-3 pr-3">
                <Link
                  to={`/app/asset/${encodeURIComponent(item.symbol)}`}
                  className="group flex items-center gap-3"
                >
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-elevated font-display text-[11px] font-semibold text-ink-2">
                    {item.symbol.replace('^', '').replace('=X', '').slice(0, 4)}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink group-hover:text-primary-soft">
                      {item.quote?.name ?? item.display_name}
                    </span>
                    <span className="flex items-center gap-1.5 text-xs text-ink-3">
                      {item.symbol}
                      <Badge className="px-1.5 py-0 text-[10px]">{titleCase(item.asset_type)}</Badge>
                    </span>
                  </span>
                </Link>
              </td>
              <td className="tabular py-3 text-right text-ink">
                {formatPrice(item.quote?.last_price, priceCurrency(item.asset_type, item.quote?.currency))}
              </td>
              <td className="py-3 text-right">
                <Change value={item.quote?.move_pct} />
              </td>
              <td className="py-3 pl-3 text-right">
                <div className="flex items-center justify-end gap-1">
                  {editable && (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Move ${item.symbol} up`}
                        disabled={idx === 0}
                        onClick={() => onMove?.(item.symbol, -1)}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Move ${item.symbol} down`}
                        disabled={idx === items.length - 1}
                        onClick={() => onMove?.(item.symbol, 1)}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Remove ${item.symbol}`}
                        onClick={() => onRemove?.(item.symbol)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => onWhy(item)}
                    aria-label={`Why did ${item.display_name} move?`}
                  >
                    <Sparkles className="h-3.5 w-3.5 text-primary-soft" aria-hidden /> Why?
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
