import {
  Clapperboard,
  ExternalLink,
  FileText,
  Headphones,
  Image as ImageIcon,
  Landmark,
  LineChart,
  Newspaper,
  Scale,
} from 'lucide-react';
import type { Source } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { formatDate, relativeTime, titleCase } from '@/lib/formatting';
import { cn } from '@/lib/utils';

export const SOURCE_ICONS = {
  news: Newspaper,
  market_data: LineChart,
  sec_filing: Landmark,
  financial_data: Scale,
  macro: LineChart,
  document: FileText,
  image: ImageIcon,
  audio: Headphones,
  video: Clapperboard,
} as const;

export function SourceCard({
  source,
  compact,
  tags = [],
  className,
}: {
  source: Source;
  compact?: boolean;
  tags?: string[];
  className?: string;
}) {
  const Icon = SOURCE_ICONS[source.source_type] ?? Newspaper;
  const body = (
    <>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 rounded-lg bg-elevated p-2 text-primary-soft">
          <Icon className="h-4 w-4" aria-hidden />
        </div>
        <div className="min-w-0 flex-1">
          <p className={cn('font-medium text-ink', compact ? 'line-clamp-2 text-[13px]' : 'text-sm')}>
            {source.title}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-3">
            <span className="text-ink-2">{source.publisher ?? 'Unknown publisher'}</span>
            {source.published_at && (
              <span title={`Published ${formatDate(source.published_at, true)}`}>
                Published {relativeTime(source.published_at)}
              </span>
            )}
            <span title={`Retrieved ${formatDate(source.retrieved_at, true)}`}>
              · Retrieved {relativeTime(source.retrieved_at)}
            </span>
          </p>
          {!compact && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge>{titleCase(source.source_type)}</Badge>
              <Badge tone="primary">Relevance {Math.round(source.relevance * 100)}%</Badge>
              {tags.map((t) => (
                <Badge key={t} tone="accent">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </div>
        {source.url && <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 text-ink-3" aria-hidden />}
      </div>
    </>
  );
  const cls = cn(
    'block rounded-xl border border-line bg-surface p-3.5 transition-colors',
    source.url && 'hover:border-line-strong hover:bg-elevated/40',
    className,
  );
  return source.url ? (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cls}
      aria-label={`${source.title} — ${source.publisher ?? ''} (opens in a new tab)`}
    >
      {body}
    </a>
  ) : (
    <div className={cls}>{body}</div>
  );
}
