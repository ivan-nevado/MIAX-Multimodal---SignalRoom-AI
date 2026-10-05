import { useMemo, useState } from 'react';
import type { Claim, InvestigationResult, Source } from '@/types/api';
import { DriverContributionBars } from '@/components/charts';
import { EvidenceGraph } from '@/components/evidence/EvidenceGraph';
import { SourceCard } from '@/components/evidence/SourceCard';
import { Badge, confidenceTone } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Disclosure } from '@/components/ui/misc';
import { titleCase } from '@/lib/formatting';

const CLAIM_TONE: Record<Claim['claim_type'], 'primary' | 'positive' | 'warning' | 'neutral'> = {
  observed_fact: 'positive',
  derived_metric: 'primary',
  interpretation: 'warning',
  hypothesis: 'neutral',
};

export function ClaimsList({ claims, sources }: { claims: Claim[]; sources: Source[] }) {
  const byId = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources]);
  return (
    <ul className="space-y-3">
      {claims.map((c) => (
        <li key={c.claim_id} className="rounded-xl border border-line p-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={CLAIM_TONE[c.claim_type]}>{titleCase(c.claim_type)}</Badge>
            <Badge tone={confidenceTone(c.evidence_confidence)}>Evidence: {c.evidence_confidence}</Badge>
            <span className="text-xs text-ink-3">
              {c.source_count} source{c.source_count === 1 ? '' : 's'}
            </span>
          </div>
          <p className="mt-2 text-sm text-ink">{c.claim}</p>
          {c.evidence_ids.length > 0 && (
            <p className="mt-1.5 text-xs text-ink-3">
              Evidence:{' '}
              {c.evidence_ids
                .slice(0, 4)
                .map((id) => byId.get(id)?.publisher ?? id)
                .join(' · ')}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}

export function EvidencePanel({ result }: { result: InvestigationResult }) {
  const [selected, setSelected] = useState<string | null>(result.drivers[0]?.driver_id ?? null);
  const driver = result.drivers.find((d) => d.driver_id === selected);
  const byId = useMemo(() => new Map(result.sources.map((s) => [s.id, s])), [result.sources]);
  const rootLabel = result.asset_name ?? result.symbol ?? 'Research question';
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader
          title="Evidence graph"
          subtitle="Move → likely drivers → supporting sources. Click a source to open it."
        />
        <CardBody>
          <EvidenceGraph
            rootLabel={rootLabel}
            move={result.market?.metrics.move_pct ?? null}
            drivers={result.drivers}
            sources={result.sources}
          />
        </CardBody>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader
            title="Likely drivers"
            subtitle="Select a driver to see its explanation and evidence."
          />
          <CardBody>
            <DriverContributionBars drivers={result.drivers} selected={selected} onSelect={setSelected} />
            {driver && (
              <div className="mt-5 space-y-3 border-t border-line pt-4">
                <p className="text-sm leading-relaxed text-ink-2">
                  {driver.explanation || 'No explanation available.'}
                </p>
                {driver.components && (
                  <dl className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(driver.components).map(([k, v]) => (
                      <div key={k} className="rounded-lg bg-elevated/60 px-2.5 py-1.5">
                        <dt className="text-ink-3">{titleCase(k)}</dt>
                        <dd className="tabular font-medium text-ink">{(v as number).toFixed(2)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
                <div className="space-y-2">
                  {driver.evidence_ids
                    .map((id) => byId.get(id))
                    .filter(Boolean)
                    .map((s) => (
                      <SourceCard key={s!.id} source={s!} compact />
                    ))}
                </div>
              </div>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            title="Claims & evidence"
            subtitle="Facts, derived metrics, interpretations and hypotheses are kept apart."
          />
          <CardBody>
            <ClaimsList claims={result.claims} sources={result.sources} />
          </CardBody>
        </Card>
      </div>
      <Disclosure title="How the evidence-weighted contribution is computed">
        <p className="text-sm leading-relaxed text-ink-2">
          raw = relevance × source support × temporal alignment × sentiment factor. Relevance is the mean
          deterministic article relevance (entity mention, recency, finance keywords); source support = 1 − e
          <sup>−publishers/3</sup>; temporal alignment is 1.0 when the story first appeared within 36 h before
          the session and decays exponentially; the sentiment factor (0.75–1.25) rewards headline tone that
          agrees with the direction of the move. Scores are normalised to 100%. This is a transparent
          heuristic — not a statistical causal model and not a probability.
        </p>
      </Disclosure>
    </div>
  );
}
