import { useId, useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

export function Logo({ className, to = '/' }: { className?: string; to?: string }) {
  // Unique gradient id: the logo renders twice (desktop sidebar + mobile header).
  const gradientId = `sr-logo-${useId().replace(/:/g, '')}`;
  return (
    <Link to={to} className={cn('inline-flex items-center gap-2', className)} aria-label="SignalRoom home">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="var(--color-primary)" />
            <stop offset="1" stopColor="var(--color-accent)" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="8" fill="var(--color-elevated)" />
        <path
          d="M6 20 L11 20 L14 10 L18 24 L21 15 L26 15"
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="font-display text-[17px] font-bold tracking-tight text-ink">
        Signal<span className="text-ink-2">Room</span>
      </span>
    </Link>
  );
}

export function SectionTitle({
  eyebrow,
  title,
  description,
  className,
  center,
}: {
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  className?: string;
  center?: boolean;
}) {
  return (
    <div className={cn(center && 'mx-auto max-w-2xl text-center', className)}>
      {eyebrow && (
        <p className="mb-2 text-xs font-semibold tracking-[0.18em] text-primary-soft uppercase">{eyebrow}</p>
      )}
      <h2 className="font-display text-2xl font-semibold text-ink sm:text-3xl">{title}</h2>
      {description && <p className="mt-3 text-[15px] leading-relaxed text-ink-2">{description}</p>}
    </div>
  );
}

/** Progressive disclosure: experts can drill down, everyone else sees the headline first. */
export function Disclosure({
  title,
  children,
  defaultOpen = false,
  icon,
  meta,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  icon?: ReactNode;
  meta?: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const id = `disclosure-${title.replace(/\W+/g, '-').toLowerCase()}`;
  return (
    <div className="rounded-xl border border-line bg-surface">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-ink">
          {icon}
          {title}
        </span>
        <span className="flex items-center gap-2 text-xs text-ink-3">
          {meta}
          <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} aria-hidden />
        </span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            id={id}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-line px-4 py-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function Meter({
  value,
  max = 100,
  tone = 'primary',
  label,
}: {
  value: number;
  max?: number;
  tone?: 'primary' | 'accent' | 'warning';
  label: string;
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      role="meter"
      aria-label={label}
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={max}
      className="h-2 w-full overflow-hidden rounded-full bg-elevated"
    >
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
        className={cn(
          'h-full rounded-full',
          tone === 'primary' && 'bg-gradient-to-r from-primary to-primary-soft',
          tone === 'accent' && 'bg-gradient-to-r from-accent to-primary',
          tone === 'warning' && 'bg-warning',
        )}
      />
    </div>
  );
}
