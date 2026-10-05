import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight } from 'lucide-react';
import { AudioPlayer } from '@/components/briefing/AudioPlayer';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { EmptyState, Skeleton } from '@/components/ui/states';
import { useBriefing, useBriefings, useGenerateBriefing } from '@/hooks/queries';
import { formatDate } from '@/lib/formatting';

export function BriefingWidget() {
  const list = useBriefings();
  const latestId = list.data?.[0]?.briefing_id;
  const { data: briefing, isLoading } = useBriefing(latestId);
  const generate = useGenerateBriefing();
  return (
    <Card className="h-full">
      <CardHeader
        icon={<BookOpen className="h-4 w-4" />}
        title="Daily briefing"
        subtitle={
          briefing
            ? `${formatDate(briefing.date)} · ${briefing.briefing_type === 'daily' ? 'scheduled' : 'on demand'}`
            : 'Your personalised market briefing'
        }
        action={
          briefing && (
            <Link
              to={`/app/briefing/${briefing.briefing_id}`}
              className="text-xs text-primary-soft hover:text-ink"
            >
              Open <ChevronRight className="inline h-3 w-3" />
            </Link>
          )
        }
      />
      <CardBody>
        {list.isLoading || isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : !briefing ? (
          <EmptyState
            title="Your first briefing will appear here."
            description="Generate one now or enable the daily briefing in Settings."
            action={
              <Button
                size="sm"
                onClick={() => generate.mutate({ withAudio: true, sendEmail: false })}
                loading={generate.isPending}
              >
                Generate briefing
              </Button>
            }
          />
        ) : briefing.status !== 'completed' ? (
          <p className="text-sm text-ink-3">Preparing your briefing…</p>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-xs text-ink-3">{briefing.greeting}</p>
              <p className="mt-1 font-display text-lg leading-snug font-semibold text-ink">
                {briefing.headline}
              </p>
              <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-ink-2">{briefing.summary}</p>
            </div>
            <AudioPlayer
              src={briefing.audio_url}
              status={briefing.audio_status}
              durationHint={briefing.audio_duration_seconds}
            />
          </div>
        )}
      </CardBody>
    </Card>
  );
}

export function LatestEvents() {
  const list = useBriefings();
  const { data: briefing } = useBriefing(list.data?.[0]?.briefing_id);
  const items = [
    ...(briefing?.sections.map((s) => ({ title: s.title, detail: s.why_it_matters, tag: s.symbol })) ?? []),
    ...(briefing?.macro_events.map((m) => ({ title: m, detail: '', tag: 'Macro' })) ?? []),
  ];
  if (!items.length)
    return <p className="text-sm text-ink-3">Key events from your latest briefing will appear here.</p>;
  return (
    <ul className="space-y-3">
      {items.slice(0, 6).map((e) => (
        <li key={e.title} className="flex gap-3">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden />
          <div>
            <p className="text-sm text-ink">
              {e.tag && <span className="mr-1.5 text-xs text-primary-soft">{e.tag}</span>}
              {e.title}
            </p>
            {e.detail && <p className="text-xs text-ink-3">{e.detail}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}
