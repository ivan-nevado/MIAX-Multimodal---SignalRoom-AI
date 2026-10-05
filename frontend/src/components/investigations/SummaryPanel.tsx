import { CircleAlert, Eye, Lightbulb, ListChecks } from 'lucide-react';
import type { InvestigationResult } from '@/types/api';
import { ContributionLabel, DriverContributionBars } from '@/components/charts';
import { Badge, confidenceTone } from '@/components/ui/badge';
import { Card, CardBody } from '@/components/ui/card';
import { Change } from '@/components/ui/change';
import { formatPrice, formatPct } from '@/lib/formatting';

/** Default view — understandable in under 30 seconds: What happened? Why? What matters? */
export function SummaryPanel({
  result,
  onShowEvidence,
}: {
  result: InvestigationResult;
  onShowEvidence: () => void;
}) {
  const m = result.market?.metrics;
  return (
    <div className="grid gap-5 xl:grid-cols-5">
      <Card className="xl:col-span-3">
        <CardBody className="space-y-5">
          {m && (
            <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
              <div>
                <p className="text-xs text-ink-3">{result.asset_name ?? result.symbol}</p>
                <p className="tabular font-display text-3xl font-semibold text-ink">
                  {formatPrice(m.last_price, m.currency)}
                </p>
              </div>
              <Change value={m.move_pct} size="lg" />
              {m.unusual_move && <Badge tone="warning">Unusual session</Badge>}
              <p className="w-full text-xs text-ink-3">
                Latest session {m.as_of} · volume {formatPct(m.volume_change_pct, 0)} vs 20-day average
                {m.benchmark_symbol ? ` · ${m.benchmark_symbol} ${formatPct(m.benchmark_move_pct)}` : ''} ·
                Market data may be delayed.
              </p>
            </div>
          )}
          <section aria-labelledby="sum-exec">
            <h2
              id="sum-exec"
              className="flex items-center gap-2 text-xs font-semibold tracking-[0.14em] text-primary-soft uppercase"
            >
              <Lightbulb className="h-3.5 w-3.5" aria-hidden /> Executive summary
            </h2>
            <p className="mt-2 text-[15px] leading-relaxed text-ink">{result.executive_summary}</p>
          </section>
          {result.what_happened && (
            <section aria-labelledby="sum-what">
              <h3 id="sum-what" className="text-sm font-semibold text-ink">
                What happened
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-ink-2">{result.what_happened}</p>
            </section>
          )}
          {!result.ai_narrative_available && (
            <p className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs text-ink-2">
              <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" aria-hidden />
              The AI narrative was unavailable; this summary was produced from deterministic metrics only.
            </p>
          )}
        </CardBody>
      </Card>

      <Card className="xl:col-span-2">
        <CardBody>
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="font-display text-lg font-semibold text-ink">Why?</h2>
            <ContributionLabel />
          </div>
          <DriverContributionBars drivers={result.drivers} />
          <button
            type="button"
            onClick={onShowEvidence}
            className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-primary-soft hover:text-ink"
          >
            <Eye className="h-4 w-4" aria-hidden /> Show evidence
          </button>
        </CardBody>
      </Card>

      <Card className="xl:col-span-3">
        <CardBody>
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
            <ListChecks className="h-4 w-4 text-primary-soft" aria-hidden /> What matters next
          </h2>
          {result.what_to_watch.length ? (
            <ul className="mt-3 space-y-2">
              {result.what_to_watch.map((w) => (
                <li key={w} className="flex gap-2 text-sm text-ink-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
                  {w}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink-3">Not enough evidence available.</p>
          )}
        </CardBody>
      </Card>

      <Card className="xl:col-span-2">
        <CardBody>
          <h2 className="text-sm font-semibold text-ink">Uncertainty & confidence</h2>
          {result.sentiment && (
            <p className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-2">
              Evidence confidence{' '}
              <Badge tone={confidenceTone(result.sentiment.evidence_confidence)}>
                {result.sentiment.evidence_confidence}
              </Badge>
              <span className="text-xs text-ink-3">{result.sentiment.confidence_reason}</span>
            </p>
          )}
          <ul className="mt-3 space-y-1.5">
            {result.uncertainties.map((u) => (
              <li key={u} className="text-xs leading-relaxed text-ink-3">
                · {u}
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
