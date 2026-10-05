import { motion } from 'framer-motion';
import { Radio, Sparkles } from 'lucide-react';
import type { AgentProgress } from '@/hooks/useInvestigationStream';
import { AgentTimeline } from '@/components/agents/AgentTimeline';
import { AGENT_ICONS } from '@/components/agents/agentMeta';
import { Meter } from '@/components/ui/misc';
import { cn } from '@/lib/utils';

/** The central UX moment: "SignalRoom is assembling your research team…" with REAL agent progress. */
export function InvestigationProgress({
  title,
  progress,
  message,
  agents,
  streamMode,
}: {
  title: string;
  progress: number;
  message: string;
  agents: AgentProgress[];
  streamMode: string;
}) {
  const working = agents.filter((a) => a.state === 'running');
  return (
    <div className="card glow overflow-hidden">
      <div className="relative border-b border-line px-6 py-7">
        <div
          className="pointer-events-none absolute -top-24 -right-16 h-56 w-56 rounded-full bg-primary/20 blur-3xl"
          aria-hidden
        />
        <p className="flex items-center gap-2 text-xs font-medium text-primary-soft">
          <Sparkles className="h-3.5 w-3.5" aria-hidden /> SignalRoom is assembling your research team…
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold text-ink">Investigating {title}</h2>
        <div className="mt-5 flex items-center gap-4">
          <div className="flex-1">
            <Meter value={progress} label="Investigation progress" />
          </div>
          <span className="tabular text-sm font-semibold text-ink">{progress}%</span>
        </div>
        <p className="mt-3 text-sm text-ink-2" aria-live="polite">
          {message}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {working.map((a) => {
            const Icon = AGENT_ICONS[a.agent];
            return (
              <motion.span
                key={a.agent}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs text-primary-soft"
              >
                {Icon && <Icon className="h-3 w-3 animate-pulse-soft" aria-hidden />} {a.label} working
              </motion.span>
            );
          })}
        </div>
      </div>
      <div className="px-4 py-4">
        <AgentTimeline agents={agents} />
        <p className={cn('mt-3 flex items-center gap-1.5 px-2 text-[11px] text-ink-3')}>
          <Radio className="h-3 w-3" aria-hidden /> Live updates via{' '}
          {streamMode === 'polling' ? 'polling (fallback)' : 'Server-Sent Events'} · progress reflects
          completed agent steps only
        </p>
      </div>
    </div>
  );
}
