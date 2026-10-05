import { ExternalLink, FileText } from 'lucide-react';
import type { FinancialSnapshot, InvestigationResult } from '@/types/api';
import { Card, CardBody, CardHeader, Stat } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/states';
import { formatCompactMoney, formatDate, formatRatioPct } from '@/lib/formatting';

export function FinancialKpis({ fin }: { fin: FinancialSnapshot }) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Stat
        label="Revenue"
        value={formatCompactMoney(fin.revenue)}
        hint={fin.period_end ? `${fin.fiscal_period} to ${fin.period_end}` : undefined}
      />
      <Stat
        label="Revenue growth YoY"
        value={formatRatioPct(fin.revenue_growth_yoy)}
        hint={`QoQ ${formatRatioPct(fin.revenue_growth_qoq)}`}
      />
      <Stat label="Operating margin" value={formatRatioPct(fin.operating_margin).replace('+', '')} />
      <Stat label="Net margin" value={formatRatioPct(fin.net_margin).replace('+', '')} />
      <Stat label="Cash" value={formatCompactMoney(fin.cash)} />
      <Stat label="Debt" value={formatCompactMoney(fin.debt)} />
    </div>
  );
}

export function FinancialPanel({ result }: { result: InvestigationResult }) {
  const fin = result.financial;
  return (
    <div className="space-y-5">
      {result.financial_context && (
        <Card>
          <CardBody>
            <h2 className="text-sm font-semibold text-ink">Financial context</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-2">{result.financial_context}</p>
          </CardBody>
        </Card>
      )}
      {fin && fin.applicable ? (
        <>
          <FinancialKpis fin={fin} />
          <p className="text-xs text-ink-3">
            Source: SEC EDGAR XBRL company facts ({fin.entity_name}). Missing values are shown as “—”, never
            estimated.
          </p>
          {fin.recent_filings.length > 0 && (
            <Card>
              <CardHeader title="Recent SEC filings" />
              <CardBody>
                <ul className="divide-y divide-line">
                  {fin.recent_filings.map((f) => (
                    <li
                      key={`${f.form}-${f.filed}`}
                      className="flex items-center justify-between gap-3 py-2.5 text-sm"
                    >
                      <span className="flex items-center gap-2 text-ink">
                        <FileText className="h-4 w-4 text-ink-3" aria-hidden /> {f.form}
                        <span className="text-ink-3">{f.description !== f.form ? f.description : ''}</span>
                      </span>
                      <span className="flex items-center gap-3 text-xs text-ink-3">
                        {formatDate(f.filed)}
                        {f.url && (
                          <a
                            href={f.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            aria-label={`Open ${f.form} on SEC.gov`}
                            className="text-primary-soft hover:text-ink"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}
        </>
      ) : (
        <EmptyState
          title="Fundamentals not applicable"
          description={fin?.note ?? 'SEC fundamentals apply to U.S.-listed companies.'}
        />
      )}
    </div>
  );
}
