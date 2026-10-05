import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { InvestigationEvent } from '@/types/api';
import { keys } from './queries';

export interface AgentProgress {
  agent: string;
  label: string;
  state: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  summary: string;
  durationMs?: number;
}

const AGENT_LABELS: Record<string, string> = {
  orchestrator: 'Orchestrator',
  market: 'Market Agent',
  news: 'News Agent',
  financial: 'Financial Agent',
  macro: 'Macro Agent',
  document: 'Document Agent',
  vision: 'Vision Agent',
  audio: 'Audio Agent',
  video: 'Video Agent',
  sentiment: 'Sentiment Agent',
  event_detection: 'Event Detection Agent',
  risk: 'Risk Agent',
  evidence: 'Evidence Agent',
  synthesis: 'Synthesis Agent',
  voice: 'Voice Agent',
};

export function agentLabel(agent: string): string {
  return AGENT_LABELS[agent] ?? agent;
}

/** Derive per-agent state from persisted progress events (no fake progress). */
export function deriveAgentProgress(events: InvestigationEvent[], plan: string[] | null): AgentProgress[] {
  const order = ['orchestrator', ...(plan ?? []).filter((a) => a !== 'orchestrator')];
  const map = new Map<string, AgentProgress>();
  for (const agent of order)
    map.set(agent, { agent, label: agentLabel(agent), state: 'pending', summary: '' });
  for (const e of events) {
    if (!e.agent || e.metadata?.followup_id) continue;
    const phase = String(e.metadata?.phase ?? '');
    const current = map.get(e.agent) ?? {
      agent: e.agent,
      label: agentLabel(e.agent),
      state: 'pending' as const,
      summary: '',
    };
    if (phase === 'started') map.set(e.agent, { ...current, state: 'running', summary: e.message });
    else if (['completed', 'failed', 'skipped'].includes(phase))
      map.set(e.agent, {
        ...current,
        state: phase as AgentProgress['state'],
        summary: e.message,
        durationMs: Number(e.metadata?.duration_ms ?? 0),
      });
  }
  return [...map.values()];
}

export function useInvestigationStream(id: string | undefined, active: boolean) {
  const [events, setEvents] = useState<InvestigationEvent[]>([]);
  const [mode, setMode] = useState<'sse' | 'polling' | 'idle'>('idle');
  const qc = useQueryClient();

  useEffect(() => {
    if (!id || !active) return;
    const unsubscribe = api.subscribeToEvents(id, {
      onEvent: (event) => {
        setEvents((prev) => (prev.some((p) => p.seq === event.seq) ? prev : [...prev, event]));
        if (
          ['completed', 'failed', 'followup_completed', 'planning'].includes(event.event_type) ||
          event.metadata?.phase === 'completed'
        ) {
          void qc.invalidateQueries({ queryKey: keys.investigation(id) });
        }
      },
      onEnd: () => {
        setMode('idle');
        void qc.invalidateQueries({ queryKey: keys.investigation(id) });
        void qc.invalidateQueries({ queryKey: keys.investigations });
      },
      onModeChange: setMode,
    });
    return unsubscribe;
  }, [id, active, qc]);

  const latest = useMemo(() => events[events.length - 1], [events]);
  return { events, latest, mode };
}
