import { Link } from 'react-router-dom';
import { Change } from '@/components/ui/change';
import { ErrorState, Skeleton } from '@/components/ui/states';
import { useMarketOverview } from '@/hooks/queries';
import { formatPrice, relativeTime } from '@/lib/formatting';

export function MarketStrip() {
  const { data, isLoading, error, refetch } = useMarketOverview();
  if (isLoading) return <Skeleton className="h-20 w-full" />;
  if (error)
    return (
      <ErrorState
        title="Market overview unavailable"
        message={(error as Error).message}
        onRetry={() => void refetch()}
      />
    );
  if (!data) return null;
  return (
    <section aria-label="Market overview">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:grid-cols-8">
        {data.indices.map((q) => (
          <Link
            key={q.symbol}
            to={`/app/asset/${encodeURIComponent(q.symbol)}`}
            className="card px-3.5 py-3 transition-colors hover:border-line-strong"
          >
            <p className="truncate text-xs text-ink-3">{q.name}</p>
            <p className="tabular mt-1 text-sm font-semibold text-ink">{formatPrice(q.last_price)}</p>
            <Change value={q.move_pct} className="text-xs" />
          </Link>
        ))}
      </div>
      <p className="mt-2 text-[11px] text-ink-3">
        Updated {relativeTime(data.retrieved_at)} · {data.delayed_notice}
      </p>
    </section>
  );
}
