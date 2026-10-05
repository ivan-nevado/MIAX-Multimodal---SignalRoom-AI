import { useMemo, useState } from 'react';
import { ImagePlus, Headphones, RefreshCw, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { Investigation } from '@/types/api';
import { AgentTimeline } from '@/components/agents/AgentTimeline';
import { AudioPlayer } from '@/components/briefing/AudioPlayer';
import { SourceCard } from '@/components/evidence/SourceCard';
import { EvidencePanel } from '@/components/investigations/EvidencePanel';
import { FinancialPanel } from '@/components/investigations/FinancialPanel';
import { FollowUpPanel } from '@/components/investigations/FollowUpPanel';
import { InvestigationProgress } from '@/components/investigations/InvestigationProgress';
import { MarketPanel } from '@/components/investigations/MarketPanel';
import { ModelUsagePanel } from '@/components/investigations/ModelUsagePanel';
import { MultimodalPanel } from '@/components/investigations/MultimodalPanel';
import { RiskPanel } from '@/components/investigations/RiskPanel';
import { SummaryPanel } from '@/components/investigations/SummaryPanel';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Disclosure } from '@/components/ui/misc';
import { ErrorState } from '@/components/ui/states';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useDeleteInvestigation, useInvestigationAction } from '@/hooks/queries';
import { agentLabel, deriveAgentProgress, useInvestigationStream } from '@/hooks/useInvestigationStream';
import { relativeTime } from '@/lib/formatting';

export function InvestigationView({ investigation }: { investigation: Investigation }) {
  const inv = investigation;
  const navigate = useNavigate();
  const running = !['completed', 'failed'].includes(inv.status);
  const followupBusy = inv.followups.some((f) => f.status === 'queued' || f.status === 'running');
  const { events, mode } = useInvestigationStream(inv.investigation_id, running || followupBusy);
  const actions = useInvestigationAction(inv.investigation_id);
  const remove = useDeleteInvestigation();
  const [tab, setTab] = useState('summary');

  const plan =
    inv.plan?.agents ??
    inv.result?.agent_runs.map((r) => r.agent).filter((a) => a !== 'orchestrator') ??
    null;
  const agents = useMemo(() => {
    if (!running && inv.result) {
      return inv.result.agent_runs.map((r) => ({
        agent: r.agent,
        label: agentLabel(r.agent),
        state: r.status,
        summary: r.summary,
        durationMs: r.duration_ms,
      }));
    }
    return deriveAgentProgress(events, plan);
  }, [events, plan, running, inv.result]);
  const latest = events[events.length - 1];
  const title = inv.asset_name ?? inv.symbol ?? 'your research question';

  const header = (
    <PageHeader
      eyebrow={
        <span className="flex flex-wrap items-center gap-2">
          {inv.symbol && <Badge tone="primary">{inv.symbol}</Badge>}
          {inv.plan && <Badge>{inv.plan.intent.replace('_', ' ')}</Badge>}
          <span>{relativeTime(inv.created_at)}</span>
        </span>
      }
      title={inv.asset_name ?? inv.symbol ?? 'Research'}
      subtitle={inv.question}
      actions={
        <Button
          variant="ghost"
          size="sm"
          onClick={() => remove.mutate(inv.investigation_id, { onSuccess: () => navigate('/app/research') })}
          aria-label="Delete investigation"
        >
          <Trash2 className="h-4 w-4" /> Delete
        </Button>
      }
    />
  );

  if (inv.status === 'failed') {
    return (
      <div>
        {header}
        <ErrorState
          title="Could not complete the investigation."
          message={inv.error ?? 'An unexpected error occurred.'}
          onRetry={() => actions.retry.mutate()}
        />
      </div>
    );
  }

  if (running || !inv.result) {
    return (
      <div className="mx-auto max-w-3xl">
        {header}
        <InvestigationProgress
          title={title}
          progress={latest?.progress ?? inv.progress}
          message={latest?.message ?? inv.status_message}
          agents={agents}
          streamMode={mode}
        />
      </div>
    );
  }

  const result = inv.result;
  const hasMedia =
    result.documents.length + result.images.length + result.audio.length + (result.videos?.length ?? 0) > 0;

  return (
    <div>
      {header}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList aria-label="Investigation sections">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="evidence">Drivers & evidence</TabsTrigger>
              {result.market && <TabsTrigger value="market">Market</TabsTrigger>}
              <TabsTrigger value="financials">Financials</TabsTrigger>
              <TabsTrigger value="risk">Risk</TabsTrigger>
              {hasMedia && <TabsTrigger value="media">Documents & media</TabsTrigger>}
              <TabsTrigger value="sources">Sources ({result.sources.length})</TabsTrigger>
            </TabsList>
            <TabsContent value="summary">
              <SummaryPanel result={result} onShowEvidence={() => setTab('evidence')} />
              <div className="mt-5">
                <FollowUpPanel
                  followups={inv.followups}
                  sources={result.sources}
                  onAsk={(q) => actions.followUp.mutate({ question: q })}
                  pending={actions.followUp.isPending}
                />
              </div>
            </TabsContent>
            <TabsContent value="evidence">
              <EvidencePanel result={result} />
            </TabsContent>
            {result.market && (
              <TabsContent value="market">
                <MarketPanel result={result} />
              </TabsContent>
            )}
            <TabsContent value="financials">
              <FinancialPanel result={result} />
            </TabsContent>
            <TabsContent value="risk">
              <RiskPanel result={result} />
            </TabsContent>
            {hasMedia && (
              <TabsContent value="media">
                <MultimodalPanel result={result} investigationId={inv.investigation_id} />
              </TabsContent>
            )}
            <TabsContent value="sources">
              <div className="grid gap-3 md:grid-cols-2">
                {result.sources.map((s) => (
                  <SourceCard key={s.id} source={s} />
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </div>

        <aside className="space-y-5" aria-label="Investigation status">
          <Card>
            <CardHeader
              icon={<Headphones className="h-4 w-4" />}
              title="Listen"
              subtitle="Narrated research brief"
            />
            <CardBody>
              {inv.audio_status === 'none' ? (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => actions.audio.mutate()}
                  loading={actions.audio.isPending}
                >
                  <Headphones className="h-4 w-4" /> Listen to briefing
                </Button>
              ) : (
                <AudioPlayer src={inv.audio_url} status={inv.audio_status} />
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader
              icon={<ImagePlus className="h-4 w-4" />}
              title="Visual brief"
              subtitle="AI-generated illustration of the verified findings"
            />
            <CardBody>
              {inv.infographic_status === 'ready' && inv.infographic_url ? (
                <a href={inv.infographic_url} target="_blank" rel="noopener noreferrer">
                  <img
                    src={inv.infographic_url}
                    alt="AI-generated visual summary of the investigation"
                    className="w-full rounded-lg border border-line"
                  />
                </a>
              ) : inv.infographic_status === 'pending' ? (
                <p className="text-sm text-ink-3">Generating visual brief…</p>
              ) : (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => actions.infographic.mutate()}
                  loading={actions.infographic.isPending}
                >
                  <ImagePlus className="h-4 w-4" />{' '}
                  {inv.infographic_status === 'failed' ? 'Retry visual brief' : 'Create visual brief'}
                </Button>
              )}
            </CardBody>
          </Card>
          <Card>
            <CardHeader
              title="Agent timeline"
              subtitle={`${agents.filter((a) => a.state === 'completed').length} agents completed`}
            />
            <CardBody className="pt-3">
              <AgentTimeline agents={agents} />
            </CardBody>
          </Card>
          <Disclosure title="Model usage & cost" meta={`${result.model_usage.length} calls`}>
            <ModelUsagePanel usage={result.model_usage} />
          </Disclosure>
          {result.warnings.length > 0 && (
            <Disclosure title="Data notes" meta={`${result.warnings.length}`}>
              <ul className="space-y-1 text-xs text-ink-3">
                {result.warnings.map((w) => (
                  <li key={w}>· {w}</li>
                ))}
              </ul>
            </Disclosure>
          )}
          <p className="text-[11px] leading-relaxed text-ink-3">{result.disclaimer}</p>
          <Button variant="ghost" size="sm" onClick={() => navigate('/app/research')}>
            <RefreshCw className="h-3.5 w-3.5" /> New investigation
          </Button>
        </aside>
      </div>
    </div>
  );
}
