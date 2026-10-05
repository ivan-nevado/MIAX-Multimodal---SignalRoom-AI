import { motion } from 'framer-motion';
import { Info } from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import type { Driver } from '@/types/api';
import { cn } from '@/lib/utils';

const BAR_TONES = [
  'from-primary to-accent',
  'from-primary/80 to-primary-soft/80',
  'from-ink-3 to-ink-2',
  'from-ink-3/70 to-ink-3',
];

export function ContributionLabel() {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <button type="button" className="inline-flex items-center gap-1 text-xs text-ink-3 hover:text-ink-2">
          Evidence-weighted contribution <Info className="h-3 w-3" aria-hidden />
        </button>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          sideOffset={6}
          className="z-50 max-w-xs rounded-lg border border-line bg-elevated px-3 py-2 text-xs leading-relaxed text-ink-2 shadow-xl"
        >
          A transparent heuristic, not a probability: relevance × independent source support × timing vs the
          move × tone alignment, normalised to 100%. Computed in Python, never by the language model.
          <Tooltip.Arrow className="fill-elevated" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

/** Horizontal driver bars (the core "Why?" visual). */
export function DriverContributionBars({
  drivers,
  onSelect,
  selected,
}: {
  drivers: Driver[];
  onSelect?: (id: string) => void;
  selected?: string | null;
}) {
  if (!drivers.length)
    return <p className="text-sm text-ink-3">No supporting source was found to score likely drivers.</p>;
  return (
    <ul className="space-y-3">
      {drivers.map((d, i) => (
        <li key={d.driver_id}>
          <button
            type="button"
            onClick={() => onSelect?.(d.driver_id)}
            className={cn(
              'w-full rounded-lg p-2 -m-2 text-left transition-colors hover:bg-elevated/60',
              selected === d.driver_id && 'bg-elevated/60',
            )}
            aria-label={`${d.name}: ${d.contribution_score.toFixed(0)} percent evidence-weighted contribution`}
          >
            <div className="mb-1.5 flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium text-ink">
                {i === 0 && (
                  <span className="mr-2 text-[10px] font-semibold tracking-wider text-primary-soft uppercase">
                    Primary
                  </span>
                )}
                {d.name}
              </span>
              <span className="tabular font-display text-base font-semibold text-ink">
                {d.contribution_score.toFixed(0)}%
              </span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-elevated">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${d.contribution_score}%` }}
                transition={{ duration: 0.8, delay: i * 0.08, ease: 'easeOut' }}
                className={cn('h-full rounded-full bg-gradient-to-r', BAR_TONES[i] ?? BAR_TONES[3])}
              />
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}
