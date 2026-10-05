import { useEffect, useId, useState } from 'react';
import { Search } from 'lucide-react';
import type { AssetMatch } from '@/types/api';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAssetSearch } from '@/hooks/queries';
import { titleCase } from '@/lib/formatting';

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Entity resolution UI: "NVIDIA" → NVDA, "S&P 500" → ^GSPC, "EUR/USD" → EURUSD=X. */
export function AssetSearch({
  onSelect,
  placeholder = 'Search company, index, crypto or FX…',
  autoFocus,
}: {
  onSelect: (m: AssetMatch) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  const [q, setQ] = useState('');
  const debounced = useDebounced(q);
  const { data, isFetching } = useAssetSearch(debounced);
  const listId = useId();
  const show = q.trim().length > 0;
  return (
    <div className="relative">
      <Search
        className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-3"
        aria-hidden
      />
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={placeholder}
        className="pl-9"
        aria-label="Search assets"
        aria-controls={listId}
        autoFocus={autoFocus}
        role="combobox"
        aria-expanded={show}
      />
      {show && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-72 w-full overflow-y-auto rounded-xl border border-line bg-elevated p-1 shadow-2xl"
        >
          {isFetching && !data && <li className="px-3 py-2 text-sm text-ink-3">Searching…</li>}
          {data?.length === 0 && <li className="px-3 py-2 text-sm text-ink-3">No matching asset.</li>}
          {data?.map((m) => (
            <li key={m.symbol} role="option" aria-selected={false}>
              <button
                type="button"
                className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left hover:bg-surface"
                onClick={() => {
                  onSelect(m);
                  setQ('');
                }}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm text-ink">{m.name}</span>
                  <span className="text-xs text-ink-3">
                    {m.symbol}
                    {m.exchange ? ` · ${m.exchange}` : ''}
                  </span>
                </span>
                <Badge>{titleCase(m.asset_type)}</Badge>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
