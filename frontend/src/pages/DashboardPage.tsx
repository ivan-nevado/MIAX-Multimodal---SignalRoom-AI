import { Link, useNavigate } from 'react-router-dom';
import { Activity, CalendarClock, FlaskConical, ListChecks, Plus, Sparkles } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Change } from '@/components/ui/change';
import { EmptyState, ErrorState, Skeleton } from '@/components/ui/states';
import { WatchlistTable } from '@/components/watchlist/WatchlistTable';
import { BriefingWidget, LatestEvents } from '@/features/dashboard/BriefingWidget';
import { MarketStrip } from '@/features/dashboard/MarketStrip';
import { RecentInvestigations } from '@/features/investigations/RecentInvestigations';
import { useWatchlist } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { useInvestigateWhy } from '@/hooks/useInvestigateWhy';

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? 'Good morning' : h < 19 ? 'Good afternoon' : 'Good evening';
}

export default function DashboardPage() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const watchlist = useWatchlist();
  const why = useInvestigateWhy();
  const movers = [...(watchlist.data ?? [])]
    .filter((w) => w.quote?.move_pct !== null && w.quote?.move_pct !== undefined)
    .sort((a, b) => Math.abs(b.quote?.move_pct ?? 0) - Math.abs(a.quote?.move_pct ?? 0))
    .slice(0, 3);

  return (
    <div className="space-y-6">
      <PageHeader
        title={`${greeting()}${session?.email ? `, ${session.email.split('@')[0]}` : ''}`}
        subtitle="Your AI financial research room — know what moved the market, and why."
        actions={
          <Button variant="gradient" onClick={() => navigate('/app/research')}>
            <Sparkles className="h-4 w-4" /> Investigate
          </Button>
        }
      />
      <MarketStrip />
      {why.error && <ErrorState title="Could not start the investigation" message={why.error.message} />}

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader
            icon={<ListChecks className="h-4 w-4" />}
            title="Watchlist"
            subtitle="Click “Why?” and the research team investigates the move."
            action={
              <Button size="sm" variant="ghost" onClick={() => navigate('/app/watchlist')}>
                <Plus className="h-3.5 w-3.5" /> Manage
              </Button>
            }
          />
          <CardBody>
            {watchlist.isLoading ? (
              <Skeleton className="h-56 w-full" />
            ) : watchlist.error ? (
              <ErrorState
                message={(watchlist.error as Error).message}
                onRetry={() => void watchlist.refetch()}
              />
            ) : watchlist.data?.length ? (
              <WatchlistTable
                items={watchlist.data}
                onWhy={(item) => void why.investigate(item.symbol, item.display_name)}
              />
            ) : (
              <EmptyState
                title="Build your market"
                description="Add companies, indices and assets you want to monitor."
                action={
                  <Button size="sm" onClick={() => navigate('/app/watchlist')}>
                    Add assets
                  </Button>
                }
              />
            )}
          </CardBody>
        </Card>
        <BriefingWidget />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader
            icon={<Activity className="h-4 w-4" />}
            title="Recent major moves"
            subtitle="Largest moves in your watchlist"
          />
          <CardBody>
            {movers.length ? (
              <ul className="space-y-3">
                {movers.map((m) => (
                  <li key={m.symbol} className="flex items-center justify-between gap-3">
                    <Link to={`/app/asset/${encodeURIComponent(m.symbol)}`} className="min-w-0">
                      <p className="truncate text-sm font-medium text-ink">{m.display_name}</p>
                      <p className="text-xs text-ink-3">{m.symbol}</p>
                    </Link>
                    <div className="flex items-center gap-2">
                      {Math.abs(m.quote?.move_pct ?? 0) >= 3 && <Badge tone="warning">Large move</Badge>}
                      <Change value={m.quote?.move_pct} />
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => void why.investigate(m.symbol, m.display_name)}
                        loading={why.pending}
                        aria-label={`Why did ${m.display_name} move?`}
                      >
                        Why?
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-3">No moves yet.</p>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHeader
            icon={<CalendarClock className="h-4 w-4" />}
            title="Latest important events"
            subtitle="From your latest briefing"
          />
          <CardBody>
            <LatestEvents />
          </CardBody>
        </Card>
        <Card>
          <CardHeader icon={<FlaskConical className="h-4 w-4" />} title="Recent investigations" />
          <CardBody className="pt-1">
            <RecentInvestigations limit={5} />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
