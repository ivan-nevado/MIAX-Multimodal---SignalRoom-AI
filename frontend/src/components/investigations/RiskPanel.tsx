import { ShieldAlert } from 'lucide-react';
import type { InvestigationResult, RiskItem, Source } from '@/types/api';
import { RiskRadar } from '@/components/charts';
import { Badge, riskTone } from '@/components/ui/badge';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/states';
import { titleCase } from '@/lib/formatting';
import { cn } from '@/lib/utils';

/** Risk matrix: qualitative impact levels (HIGH / MEDIUM / LOW), labelled — not colour-only. */
export function RiskMatrix({ risks }: { risks: RiskItem[] }) {
  const rows: RiskItem['level'][] = ['HIGH', 'MEDIUM', 'LOW'];
  return (
    <div className="space-y-2" role="table" aria-label="Risk matrix">
      {rows.map((level) => {
        const items = risks.filter((r) => r.level === level);
        return (
          <div key={level} role="row" className="grid grid-cols-[88px_1fr] items-center gap-3">
            <div role="rowheader">
              <Badge tone={riskTone(level)} className="w-full justify-center">
                {level}
              </Badge>
            </div>
            <div
              role="cell"
              className={cn(
                'flex min-h-10 flex-wrap gap-2 rounded-lg border border-line p-2',
                items.length === 0 && 'opacity-50',
              )}
            >
              {items.length ? (
                items.map((r) => (
                  <span key={r.risk} className="rounded-md bg-elevated px-2 py-1 text-xs text-ink">
                    {titleCase(r.risk)}
                  </span>
                ))
              ) : (
                <span className="text-xs text-ink-3">None</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function RiskPanel({ result }: { result: InvestigationResult }) {
  const risks = result.risks?.items ?? [];
  const byId = new Map<string, Source>(result.sources.map((s) => [s.id, s]));
  if (!risks.length)
    return (
      <EmptyState
        icon={<ShieldAlert className="h-5 w-5" />}
        title="No material risks assessed"
        description="The Risk Agent found no risk supported by the available evidence."
      />
    );
  return (
    <div className="space-y-5">
      {result.risk_summary && (
        <Card>
          <CardBody>
            <p className="text-sm leading-relaxed text-ink-2">{result.risk_summary}</p>
          </CardBody>
        </Card>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Risk matrix" subtitle="Qualitative levels — never probabilities" />
          <CardBody>
            <RiskMatrix risks={risks} />
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Risk radar" />
          <CardBody>
            <RiskRadar risks={risks} />
          </CardBody>
        </Card>
      </div>
      <ul className="space-y-3">
        {risks.map((r) => (
          <li key={r.risk} className="card p-4">
            <div className="flex items-center gap-2">
              <Badge tone={riskTone(r.level)}>{r.level}</Badge>
              <p className="font-medium text-ink">{titleCase(r.risk)} risk</p>
            </div>
            <p className="mt-2 text-sm text-ink-2">{r.reason}</p>
            <p className="mt-2 text-xs text-ink-3">
              Evidence:{' '}
              {r.evidence_ids.map((id) => byId.get(id)?.publisher ?? byId.get(id)?.title ?? id).join(' · ')}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
