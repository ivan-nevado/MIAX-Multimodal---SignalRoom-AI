import { Link } from 'react-router-dom';
import { ChevronRight, FlaskConical, LoaderCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Change } from '@/components/ui/change';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states';
import { useInvestigations } from '@/hooks/queries';
import { relativeTime } from '@/lib/formatting';

export function RecentInvestigations({ limit = 6 }: { limit?: number }) {
  const { data, isLoading, error, refetch } = useInvestigations(limit);
  if (isLoading) return <Skeleton className="h-40 w-full" />;
  if (error) return <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />;
  if (!data?.length)
    return (
      <EmptyState
        icon={<FlaskConical className="h-5 w-5" />}
        title="Ask SignalRoom what is happening in your market."
        description="Your investigations will appear here."
      />
    );
  return (
    <ul className="divide-y divide-line">
      {data.map((inv) => (
        <li key={inv.investigation_id}>
          <Link
            to={`/app/investigation/${inv.investigation_id}`}
            className="group flex items-center gap-3 py-3"
          >
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-sm font-medium text-ink">
                {inv.symbol && <Badge tone="primary">{inv.symbol}</Badge>}
                <span className="truncate">{inv.question}</span>
              </p>
              <p className="mt-0.5 line-clamp-1 text-xs text-ink-3">
                {inv.summary ??
                  (inv.status === 'failed' ? 'Could not complete — open to retry.' : 'In progress…')}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {inv.status === 'completed' ? (
                inv.move_pct !== null && <Change value={inv.move_pct} />
              ) : inv.status === 'failed' ? (
                <Badge tone="negative">Failed</Badge>
              ) : (
                <span className="flex items-center gap-1 text-xs text-primary-soft">
                  <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden /> {inv.progress}%
                </span>
              )}
              <span className="hidden text-xs text-ink-3 sm:inline">{relativeTime(inv.created_at)}</span>
              <ChevronRight className="h-4 w-4 text-ink-3 group-hover:text-ink" aria-hidden />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
