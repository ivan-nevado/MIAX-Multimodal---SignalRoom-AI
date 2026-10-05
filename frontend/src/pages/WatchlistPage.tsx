import { useState } from 'react';
import { ListChecks } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states';
import { AssetSearch } from '@/components/watchlist/AssetSearch';
import { WatchlistTable } from '@/components/watchlist/WatchlistTable';
import {
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useReorderWatchlist,
  useWatchlist,
} from '@/hooks/queries';
import { useInvestigateWhy } from '@/hooks/useInvestigateWhy';

export default function WatchlistPage() {
  const { data, isLoading, error, refetch } = useWatchlist();
  const add = useAddToWatchlist();
  const remove = useRemoveFromWatchlist();
  const reorder = useReorderWatchlist();
  const why = useInvestigateWhy();
  const [message, setMessage] = useState<string | null>(null);

  const move = (symbol: string, delta: -1 | 1) => {
    if (!data) return;
    const symbols = data.map((d) => d.symbol);
    const i = symbols.indexOf(symbol);
    const j = i + delta;
    if (j < 0 || j >= symbols.length) return;
    [symbols[i], symbols[j]] = [symbols[j], symbols[i]];
    reorder.mutate(symbols);
  };

  return (
    <div>
      <PageHeader
        title="Watchlist"
        subtitle="Companies, indices, crypto and FX you want SignalRoom to monitor (max 20 in this MVP)."
      />
      <Card className="mb-6">
        <CardHeader title="Add an asset" subtitle='Try "NVIDIA", "Bitcoin", "S&P 500" or "EUR/USD".' />
        <CardBody>
          <AssetSearch
            onSelect={(m) =>
              add.mutate(m.symbol, {
                onSuccess: () => setMessage(`${m.name} added to your watchlist.`),
                onError: (e) => setMessage((e as Error).message),
              })
            }
          />
          {message && (
            <p role="status" className="mt-2 text-sm text-ink-2">
              {message}
            </p>
          )}
        </CardBody>
      </Card>
      <Card>
        <CardBody>
          {isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : error ? (
            <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
          ) : data?.length ? (
            <WatchlistTable
              items={data}
              editable
              onWhy={(i) => void why.investigate(i.symbol, i.display_name)}
              onRemove={(s) => remove.mutate(s)}
              onMove={move}
            />
          ) : (
            <EmptyState
              icon={<ListChecks className="h-5 w-5" />}
              title="Build your market"
              description="Add companies, indices and assets you want to monitor."
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
