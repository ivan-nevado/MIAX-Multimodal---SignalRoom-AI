import { motion } from 'framer-motion';
import { Check, CircleDashed, CircleMinus, CircleX, LoaderCircle } from 'lucide-react';
import type { AgentProgress } from '@/hooks/useInvestigationStream';
import { cn } from '@/lib/utils';
import { AGENT_ICONS } from './agentMeta';

const STATE_ICON = {
  completed: { icon: Check, cls: 'text-positive bg-positive/10 border-positive/30', label: 'completed' },
  running: { icon: LoaderCircle, cls: 'text-primary-soft bg-primary/10 border-primary/40', label: 'running' },
  pending: { icon: CircleDashed, cls: 'text-ink-3 bg-elevated border-line', label: 'waiting' },
  failed: { icon: CircleX, cls: 'text-negative bg-negative/10 border-negative/30', label: 'failed' },
  skipped: { icon: CircleMinus, cls: 'text-ink-3 bg-elevated border-line', label: 'skipped' },
};

/** Visible multi-agent execution: ✓ Market Agent — "Analyzed price, volatility and volume". */
export function AgentTimeline({ agents, compact }: { agents: AgentProgress[]; compact?: boolean }) {
  return (
    <ol className="relative space-y-1" aria-label="Agent execution timeline">
      {agents.map((a, i) => {
        const meta = STATE_ICON[a.state];
        const StateIcon = meta.icon;
        const AgentIcon = AGENT_ICONS[a.agent] ?? CircleDashed;
        return (
          <motion.li
            key={a.agent}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.03 }}
            className="relative flex gap-3 rounded-lg px-2 py-2"
          >
            {i < agents.length - 1 && (
              <span aria-hidden className="absolute top-9 left-[21px] h-[calc(100%-22px)] w-px bg-line" />
            )}
            <span
              className={cn(
                'relative z-10 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border',
                meta.cls,
              )}
            >
              <StateIcon className={cn('h-3.5 w-3.5', a.state === 'running' && 'animate-spin')} aria-hidden />
              <span className="sr-only">{meta.label}</span>
            </span>
            <div className="min-w-0 flex-1">
              <p
                className={cn(
                  'flex items-center gap-1.5 text-[13px] font-medium',
                  a.state === 'pending' ? 'text-ink-3' : 'text-ink',
                )}
              >
                <AgentIcon className="h-3.5 w-3.5 text-ink-3" aria-hidden />
                {a.label}
                {a.durationMs ? (
                  <span className="tabular ml-auto text-[11px] font-normal text-ink-3">
                    {(a.durationMs / 1000).toFixed(1)}s
                  </span>
                ) : null}
              </p>
              {!compact && a.summary && a.state !== 'pending' && (
                <p className="mt-0.5 text-xs text-ink-3">{a.summary}</p>
              )}
            </div>
          </motion.li>
        );
      })}
    </ol>
  );
}
