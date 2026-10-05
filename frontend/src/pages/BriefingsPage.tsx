import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight, Headphones } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody } from '@/components/ui/card';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states';
import { useBriefings, useGenerateBriefing } from '@/hooks/queries';
import { formatDate } from '@/lib/formatting';

export default function BriefingsPage() {
  const { data, isLoading, error, refetch } = useBriefings();
  const generate = useGenerateBriefing();
  return (
    <div>
      <PageHeader
        title="Briefings"
        subtitle="Editorial market briefings for your watchlist — on screen, by email and as audio."
        actions={
          <Button
            variant="gradient"
            onClick={() => generate.mutate({ withAudio: true, sendEmail: false })}
            loading={generate.isPending}
          >
            <BookOpen className="h-4 w-4" /> Generate briefing now
          </Button>
        }
      />
      {generate.error && <ErrorState message={(generate.error as Error).message} className="mb-4" />}
      <Card>
        <CardBody>
          {isLoading ? (
            <Skeleton className="h-48 w-full" />
          ) : error ? (
            <ErrorState message={(error as Error).message} onRetry={() => void refetch()} />
          ) : data?.length ? (
            <ul className="divide-y divide-line">
              {data.map((b) => (
                <li key={b.briefing_id}>
                  <Link
                    to={`/app/briefing/${b.briefing_id}`}
                    className="group flex items-center gap-4 py-3.5"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-medium text-ink group-hover:text-primary-soft">
                        {b.headline ?? 'Preparing briefing…'}
                      </p>
                      <p className="mt-0.5 flex items-center gap-2 text-xs text-ink-3">
                        {formatDate(b.date)}{' '}
                        <Badge>{b.briefing_type === 'daily' ? 'Daily' : 'On demand'}</Badge>
                        {b.audio_status === 'ready' && (
                          <span className="inline-flex items-center gap-1">
                            <Headphones className="h-3 w-3" aria-hidden /> audio
                          </span>
                        )}
                      </p>
                    </div>
                    {b.status !== 'completed' && (
                      <Badge tone={b.status === 'failed' ? 'negative' : 'primary'}>{b.status}</Badge>
                    )}
                    <ChevronRight className="h-4 w-4 text-ink-3" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={<BookOpen className="h-5 w-5" />}
              title="Your first briefing will appear here."
              description="Generate one now, or enable the scheduled daily briefing in Settings."
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}
