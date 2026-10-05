import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ExternalLink, Newspaper, Sparkles } from 'lucide-react';
import { CandlestickChart, VolumeChart } from '@/components/charts';
import { FinancialKpis } from '@/components/investigations/FinancialPanel';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader, Stat } from '@/components/ui/card';
import { Change } from '@/components/ui/change';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states';
import { useAsset } from '@/hooks/queries';
import { useInvestigateWhy } from '@/hooks/useInvestigateWhy';
import type { HistoryRange } from '@/lib/api';
import { formatPct, formatPrice, priceCurrency, relativeTime, titleCase } from '@/lib/formatting';
import { cn } from '@/lib/utils';

const RANGES: { label: string; value: HistoryRange }[] = [
  { label: '1D', value: '1d' },
  { label: '1W', value: '5d' },
  { label: '1M', value: '1mo' },
  { label: '1Y', value: '1y' },
];

export default function AssetPage() {
  const { symbol = '' } = useParams();
  const [range, setRange] = useState<HistoryRange>('1mo');
  const { data, isLoading, error, refetch } = useAsset(decodeURIComponent(symbol), range);
  const why = useInvestigateWhy();

  if (error)
    return (
      <ErrorState
        title="Asset unavailable"
        message={(error as Error).message}
        onRetry={() => void refetch()}
      />
    );
  const q = data?.quote;
  const m = data?.metrics;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={q && <Badge>{titleCase(q.asset_type)}</Badge>}
        title={q ? q.name : decodeURIComponent(symbol)}
        subtitle={
          q ? (
            <span className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <span className="tabular font-display text-3xl font-semibold text-ink">
                {formatPrice(q.last_price, priceCurrency(q.asset_type, q.currency))}
              </span>
              <Change value={q.move_pct} size="lg" />
              <span className="text-xs text-ink-3">
                {q.symbol} · Updated {relativeTime(q.retrieved_at)} · {q.delayed_notice}
              </span>
            </span>
          ) : undefined
        }
        actions={
          <Button
            variant="gradient"
            size="lg"
            onClick={() => q && void why.investigate(q.symbol, q.name)}
            loading={why.pending}
            disabled={!q}
          >
            <Sparkles className="h-4 w-4" /> Investigate why
          </Button>
        }
      />

      <Card>
        <CardHeader
          title="Price & volume"
          action={
            <div role="group" aria-label="Chart range" className="flex rounded-lg border border-line p-0.5">
              {RANGES.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  onClick={() => setRange(r.value)}
                  aria-pressed={range === r.value}
                  className={cn(
                    'rounded-md px-3 py-1 text-xs font-medium',
                    range === r.value ? 'bg-elevated text-ink' : 'text-ink-3 hover:text-ink',
                  )}
                >
                  {r.label}
                </button>
              ))}
            </div>
          }
        />
        <CardBody>
          <CandlestickChart
            data={data?.history ?? []}
            loading={isLoading}
            height={360}
            label={`${symbol} price chart`}
            showVolume={false}
          />
          <div className="mt-4">{data && <VolumeChart data={data.history} />}</div>
        </CardBody>
      </Card>

      {isLoading ? (
        <Skeleton className="h-28 w-full" />
      ) : (
        m && (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="5-day return" value={formatPct(m.return_5d_pct)} />
            <Stat label="1-month return" value={formatPct(m.return_1m_pct)} />
            <Stat
              label="Volatility (20d)"
              value={m.volatility_20d !== null ? `${(m.volatility_20d * 100).toFixed(1)}%` : '—'}
              hint="annualised"
            />
            <Stat
              label="Volume vs 20d avg"
              value={formatPct(m.volume_change_pct, 0)}
              hint={m.unusual_move ? 'Unusual session' : undefined}
            />
          </div>
        )
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader
            icon={<Newspaper className="h-4 w-4" />}
            title="Latest news"
            subtitle="Ranked for relevance · links open the original publisher"
          />
          <CardBody>
            {isLoading ? (
              <Skeleton className="h-40 w-full" />
            ) : data?.news.length ? (
              <ul className="divide-y divide-line">
                {data.news.map((n) => (
                  <li key={n.id}>
                    <a
                      href={n.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group flex items-start justify-between gap-3 py-2.5"
                    >
                      <span>
                        <span className="block text-sm text-ink group-hover:text-primary-soft">
                          {n.title}
                        </span>
                        <span className="text-xs text-ink-3">
                          {n.publisher} · {relativeTime(n.published_at)}
                        </span>
                      </span>
                      <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0 text-ink-3" aria-hidden />
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState
                title="No supporting source was found."
                description="No relevant recent headlines for this asset."
              />
            )}
          </CardBody>
        </Card>
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Financial snapshot"
              subtitle={
                data?.financial ? `SEC EDGAR · ${data.financial.entity_name}` : 'U.S.-listed companies only'
              }
            />
            <CardBody>
              {data?.financial ? (
                <FinancialKpis fin={data.financial} />
              ) : (
                <p className="text-sm text-ink-3">
                  Fundamentals are not applicable or not available for this asset.
                </p>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Recent investigations" />
            <CardBody>
              {data?.recent_investigations.length ? (
                <ul className="space-y-2">
                  {data.recent_investigations.map((r) => (
                    <li key={r.investigation_id}>
                      <Link
                        to={`/app/investigation/${r.investigation_id}`}
                        className="block rounded-lg border border-line p-3 hover:border-line-strong"
                      >
                        <p className="text-sm text-ink">{r.question}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-ink-3">{r.summary ?? r.status}</p>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-ink-3">No investigations yet — click “Investigate why”.</p>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
