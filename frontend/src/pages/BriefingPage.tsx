import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Mail, ShieldAlert } from 'lucide-react';
import { api } from '@/lib/api';
import { AudioPlayer } from '@/components/briefing/AudioPlayer';
import { SourceCard } from '@/components/evidence/SourceCard';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Change } from '@/components/ui/change';
import { Dialog } from '@/components/ui/dialog';
import { Disclosure } from '@/components/ui/misc';
import { ErrorState, Skeleton, Spinner } from '@/components/ui/states';
import { useBriefing } from '@/hooks/queries';
import { formatDate, formatPrice } from '@/lib/formatting';

export default function BriefingPage() {
  const { id } = useParams();
  const { data: b, isLoading, error, refetch } = useBriefing(id);
  const [emailHtml, setEmailHtml] = useState<string | null>(null);
  const [emailOpen, setEmailOpen] = useState(false);

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error || !b)
    return (
      <ErrorState
        title="Briefing unavailable"
        message={(error as Error | null)?.message}
        onRetry={() => void refetch()}
      />
    );
  if (b.status === 'failed')
    return <ErrorState title="Could not prepare the briefing." message={b.error ?? undefined} />;
  if (b.status !== 'completed')
    return <Spinner label="Preparing your briefing… the Briefing Agent is reviewing your watchlist" />;

  const byId = new Map(b.sources.map((s) => [s.id, s]));
  const openEmail = async () => {
    setEmailOpen(true);
    if (!emailHtml) setEmailHtml(await api.emailPreview(b.briefing_id));
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow={`${formatDate(b.date)} · ${b.briefing_type === 'daily' ? 'Daily briefing' : 'On-demand briefing'}`}
        title={b.headline ?? 'Briefing'}
        subtitle={b.greeting ?? undefined}
        actions={
          <Button variant="secondary" onClick={() => void openEmail()}>
            <Mail className="h-4 w-4" /> Email preview
          </Button>
        }
      />
      <AudioPlayer src={b.audio_url} status={b.audio_status} durationHint={b.audio_duration_seconds} />
      <Card>
        <CardBody>
          <p className="text-[15px] leading-relaxed text-ink">{b.summary}</p>
        </CardBody>
      </Card>
      <ol className="space-y-4">
        {b.sections.map((s, i) => (
          <li key={s.title} className="card p-5">
            <p className="text-xs font-semibold tracking-wider text-primary-soft">
              {i + 1}
              {s.symbol ? ` · ${s.symbol}` : ''}
            </p>
            <h2 className="mt-1 font-display text-lg font-semibold text-ink">{s.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-ink-2">{s.body}</p>
            {s.why_it_matters && (
              <p className="mt-2 text-sm text-ink-2">
                <span className="font-semibold text-ink">Why it matters: </span>
                {s.why_it_matters}
              </p>
            )}
            {s.source_ids.length > 0 && (
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {s.source_ids
                  .map((sid) => byId.get(sid))
                  .filter(Boolean)
                  .slice(0, 4)
                  .map((src) => (
                    <SourceCard key={src!.id} source={src!} compact />
                  ))}
              </div>
            )}
          </li>
        ))}
      </ol>
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader title="Watchlist moves" />
          <CardBody>
            <table className="w-full text-sm">
              <tbody>
                {b.watchlist_moves.map((m) => (
                  <tr key={m.symbol} className="border-t border-line/70">
                    <td className="py-2 text-ink">
                      {m.name ?? m.symbol} <span className="text-xs text-ink-3">{m.symbol}</span>
                    </td>
                    <td className="tabular py-2 text-right text-ink-2">{formatPrice(m.last_price)}</td>
                    <td className="py-2 text-right">
                      <Change value={m.move_pct} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<ShieldAlert className="h-4 w-4" />} title="Risk flags & macro" />
          <CardBody className="space-y-3">
            {b.risk_flags.map((r) => (
              <p key={r} className="text-sm text-warning">
                · {r}
              </p>
            ))}
            {b.macro_events.map((m) => (
              <p key={m} className="text-sm text-ink-2">
                · {m}
              </p>
            ))}
          </CardBody>
        </Card>
      </div>
      <Disclosure title="All sources" meta={`${b.sources.length}`}>
        <div className="grid gap-2 sm:grid-cols-2">
          {b.sources.map((s) => (
            <SourceCard key={s.id} source={s} compact />
          ))}
        </div>
      </Disclosure>
      <p className="text-[11px] leading-relaxed text-ink-3">{b.disclaimer}</p>
      <Dialog
        open={emailOpen}
        onOpenChange={setEmailOpen}
        title="Daily briefing email"
        description="Rendered exactly as sent through Amazon SES."
      >
        {emailHtml ? (
          <iframe
            title="Email preview"
            srcDoc={emailHtml}
            sandbox=""
            className="h-[70vh] w-full rounded-lg border border-line bg-background"
          />
        ) : (
          <Spinner />
        )}
      </Dialog>
    </div>
  );
}
