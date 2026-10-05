import type { ReactNode } from 'react';
import { ChartLine } from 'lucide-react';
import { ErrorState, Skeleton } from '@/components/ui/states';
import { cn } from '@/lib/utils';

/** Shared loading / empty / error handling for every chart. */
export function ChartFrame({
  loading,
  error,
  empty,
  emptyLabel = 'No data available for this period.',
  height = 260,
  className,
  children,
  label,
}: {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyLabel?: string;
  height?: number;
  className?: string;
  children: ReactNode;
  label: string;
}) {
  if (loading) return <Skeleton height={height} className={cn('w-full', className)} />;
  if (error) return <ErrorState title="Chart unavailable" message={error} className={className} />;
  if (empty)
    return (
      <div
        style={{ height }}
        className={cn(
          'flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-line text-sm text-ink-3',
          className,
        )}
      >
        <ChartLine className="h-5 w-5" aria-hidden />
        {emptyLabel}
      </div>
    );
  return (
    <figure
      aria-label={label}
      style={{ minHeight: height }}
      className={cn('w-full overflow-x-auto', className)}
    >
      {children}
    </figure>
  );
}
