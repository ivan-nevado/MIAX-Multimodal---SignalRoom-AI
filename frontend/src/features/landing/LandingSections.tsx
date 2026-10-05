import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Clapperboard,
  ArrowRight,
  BarChart3,
  Check,
  ChevronDown,
  FileText,
  Headphones,
  Image as ImageIcon,
  LineChart,
  Newspaper,
  Sparkles,
  Type,
  Globe,
  ExternalLink,
} from 'lucide-react';
import { AGENT_ICONS, RESEARCH_TEAM } from '@/components/agents/agentMeta';
import { AudioPlayer } from '@/components/briefing/AudioPlayer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SectionTitle } from '@/components/ui/misc';
import { cn } from '@/lib/utils';

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.5 },
};

// Seeded, illustrative scenario for the landing page only (labelled as such).
const DEMO_DRIVERS = [
  { name: 'Regulatory / export news', pct: 62 },
  { name: 'Valuation concerns', pct: 21 },
  { name: 'Market / sector pressure', pct: 17 },
];

export function WhyCard({ className }: { className?: string }) {
  return (
    <div className={cn('card glow relative overflow-hidden p-6', className)}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-ink-3">NVIDIA · NVDA</p>
          <p className="tabular mt-1 font-display text-4xl font-semibold text-negative">−6.2%</p>
        </div>
        <Badge tone="warning">Illustrative scenario</Badge>
      </div>
      <p className="mt-6 font-display text-sm font-semibold tracking-[0.2em] text-primary-soft">WHY?</p>
      <ul className="mt-3 space-y-3.5">
        {DEMO_DRIVERS.map((d, i) => (
          <li key={d.name}>
            <div className="mb-1.5 flex justify-between text-sm">
              <span className="text-ink">
                {i === 0 && (
                  <span className="mr-2 text-[10px] font-semibold tracking-wider text-primary-soft uppercase">
                    Primary
                  </span>
                )}
                {d.name}
              </span>
              <span className="tabular font-semibold text-ink">{d.pct}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-elevated">
              <motion.div
                initial={{ width: 0 }}
                whileInView={{ width: `${d.pct}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, delay: 0.2 + i * 0.12 }}
                className={cn(
                  'h-full rounded-full bg-gradient-to-r',
                  i === 0 ? 'from-primary to-accent' : 'from-ink-3 to-ink-2',
                )}
              />
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-5 text-[11px] text-ink-3">
        Evidence-weighted contribution — a transparent heuristic, not a probability.
      </p>
    </div>
  );
}

const HERO_STEPS = [
  ['market', 'Market data collected', 'NVDA −6.2% · volume 2.8× average'],
  ['news', 'Relevant news identified', '32 articles · 7 independent publishers'],
  ['event_detection', 'News clustered', '3 themes · regulation leads'],
  ['financial', 'Financial context analyzed', 'SEC filings · margins & cash'],
  ['risk', 'Risk analysis completed', 'Regulatory risk: HIGH'],
  ['synthesis', 'Synthesizing evidence', 'Writing the brief…'],
] as const;

function HeroProgressCard() {
  return (
    <div className="card glow p-5">
      <p className="flex items-center gap-2 text-xs text-primary-soft">
        <Sparkles className="h-3.5 w-3.5" aria-hidden /> Investigating NVIDIA
      </p>
      <ol className="mt-4 space-y-2.5">
        {HERO_STEPS.map(([agent, title, detail], i) => {
          const Icon = AGENT_ICONS[agent];
          const running = i === HERO_STEPS.length - 1;
          return (
            <motion.li
              key={title}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.25 }}
              className="flex items-start gap-3"
            >
              <span
                className={cn(
                  'mt-0.5 flex h-6 w-6 items-center justify-center rounded-full border',
                  running
                    ? 'border-primary/40 bg-primary/10 text-primary-soft'
                    : 'border-positive/30 bg-positive/10 text-positive',
                )}
              >
                {running ? (
                  <Icon className="h-3 w-3 animate-pulse-soft" aria-hidden />
                ) : (
                  <Check className="h-3 w-3" aria-hidden />
                )}
              </span>
              <span>
                <span className="block text-sm text-ink">{title}</span>
                <span className="text-xs text-ink-3">{detail}</span>
              </span>
            </motion.li>
          );
        })}
      </ol>
      <p className="mt-4 text-[11px] text-ink-3">Illustrative example of the live agent timeline.</p>
    </div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden px-4 pt-16 pb-20 sm:px-6 lg:pt-24">
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl"
        aria-hidden
      />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <Badge tone="primary" className="mb-5">
            <Sparkles className="h-3 w-3" aria-hidden /> Your AI financial research room
          </Badge>
          <h1 className="font-display text-4xl leading-[1.05] font-semibold text-ink sm:text-6xl">
            Know what moved the market. <span className="gradient-text">Know why.</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-2">
            SignalRoom combines market data, news, financial filings, charts and audio into one AI research
            workflow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/signup">
              <Button size="lg" variant="gradient">
                Start researching <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="#how">
              <Button size="lg" variant="secondary">
                See how it works
              </Button>
            </a>
          </div>
          <p className="mt-6 text-xs text-ink-3">
            Research less. Understand more. From market movement to evidence in minutes.
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
        >
          <HeroProgressCard />
        </motion.div>
      </div>
    </section>
  );
}

const FORMATS = [
  { label: 'News', icon: Newspaper },
  { label: 'Financial reports', icon: FileText },
  { label: 'Charts', icon: BarChart3 },
  { label: 'Earnings calls', icon: Headphones },
  { label: 'Market data', icon: LineChart },
  { label: 'Macro events', icon: Globe },
];

export function Problem() {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <SectionTitle
          center
          eyebrow="The problem"
          title="Markets generate enormous amounts of information across different formats."
        />
        <motion.ul
          {...fadeUp}
          className="mx-auto mt-10 grid max-w-4xl grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
        >
          {FORMATS.map(({ label, icon: Icon }) => (
            <li
              key={label}
              className="card flex flex-col items-center gap-2 px-3 py-5 text-center text-sm text-ink-2"
            >
              <Icon className="h-5 w-5 text-ink-3" aria-hidden />
              {label}
            </li>
          ))}
        </motion.ul>
        <div className="mt-6 flex justify-center">
          <ChevronDown className="h-6 w-6 text-primary-soft" aria-hidden />
        </div>
        <p className="mt-4 text-center font-display text-xl text-ink">
          SignalRoom turns them into one coherent intelligence layer.
        </p>
      </div>
    </section>
  );
}

export function Team() {
  return (
    <section id="how" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <SectionTitle
          center
          eyebrow="An AI research team, not a chatbot"
          title="Specialised agents investigate, cross-check and explain."
          description="An orchestrator assembles only the agents your question needs. Numbers are computed in code; language models interpret them."
        />
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {RESEARCH_TEAM.map((member, i) => {
            const Icon = AGENT_ICONS[member.agent];
            return (
              <motion.div
                key={member.name}
                {...fadeUp}
                transition={{ duration: 0.45, delay: i * 0.05 }}
                className="card p-5"
              >
                <div className="flex items-center gap-3">
                  <span className="rounded-xl bg-primary/10 p-2.5 text-primary-soft">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="font-display text-base font-semibold text-ink">{member.name}</h3>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-ink-2">{member.role}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

const INPUTS = [
  { label: 'PDF', icon: FileText },
  { label: 'Image', icon: ImageIcon },
  { label: 'Audio', icon: Headphones },
  { label: 'Video', icon: Clapperboard },
  { label: 'Market data', icon: LineChart },
  { label: 'News', icon: Newspaper },
  { label: 'Text', icon: Type },
];

export function Multimodal() {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <SectionTitle center eyebrow="Multimodal by design" title="Every format, one research brief." />
        <motion.div {...fadeUp} className="mx-auto mt-12 flex max-w-3xl flex-col items-center gap-5">
          <div className="grid w-full grid-cols-4 gap-3 sm:grid-cols-7">
            {INPUTS.map(({ label, icon: Icon }) => (
              <div key={label} className="card flex flex-col items-center gap-2 py-4 text-xs text-ink-2">
                <Icon className="h-5 w-5 text-primary-soft" aria-hidden />
                {label}
              </div>
            ))}
          </div>
          <ChevronDown className="h-6 w-6 text-ink-3" aria-hidden />
          <div className="glow rounded-2xl border border-primary/40 bg-elevated px-10 py-5 text-center">
            <p className="font-display text-xl font-semibold text-ink">SignalRoom</p>
            <p className="mt-1 text-xs text-ink-3">
              GPT-6 Luna · Gemini 3.8 Flash · GPT Audio · Gemini Image · Gemini Embedding 2 — orchestrated
              with LangGraph
            </p>
          </div>
          <ChevronDown className="h-6 w-6 text-ink-3" aria-hidden />
          <div className="grid w-full grid-cols-2 gap-3 sm:grid-cols-5">
            {['Research brief', 'Charts', 'Evidence graph', 'Audio briefing', 'Email', 'Semantic search'].map(
              (o) => (
                <div
                  key={o}
                  className="rounded-xl border border-line bg-surface px-3 py-3 text-center text-xs text-ink"
                >
                  {o}
                </div>
              ),
            )}
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export function DailyBriefingSection() {
  return (
    <section id="briefing" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto grid max-w-6xl items-center gap-10 lg:grid-cols-2">
        <SectionTitle
          eyebrow="Daily briefing"
          title="Your market, briefed every morning."
          description="Pick a time and timezone. SignalRoom reviews your watchlist, the news and the macro backdrop, then writes — and reads — an editorial briefing. Optionally by email."
        />
        <motion.div {...fadeUp} className="card p-6">
          <p className="text-xs text-ink-3">Good morning.</p>
          <p className="mt-1 font-display text-lg font-semibold text-ink">Three things matter today.</p>
          <ol className="mt-4 space-y-3 text-sm text-ink-2">
            <li>
              <span className="font-medium text-ink">1. Your largest mover.</span> What moved, by how much,
              and the likely drivers — with sources.
            </li>
            <li>
              <span className="font-medium text-ink">2. The macro backdrop.</span> Rates, volatility, dollar
              and oil in one line each.
            </li>
            <li>
              <span className="font-medium text-ink">3. Risk flags.</span> What deserves attention before the
              open.
            </li>
          </ol>
          <AudioPlayer className="mt-5" src="/demo/briefing.wav" title="Listen to a real recorded briefing" />
        </motion.div>
      </div>
    </section>
  );
}

const EVIDENCE = [
  { publisher: 'Reuters', title: 'U.S. tightens export rules on advanced AI chips', time: '2h ago' },
  { publisher: 'Bloomberg', title: 'Chip stocks slide as export curbs widen', time: '3h ago' },
  { publisher: 'SEC EDGAR', title: '8-K current report', time: 'yesterday' },
];

export function EvidenceSection() {
  const [open, setOpen] = useState(true);
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <SectionTitle
          center
          eyebrow="Sources & evidence"
          title="Every conclusion expands to the evidence behind it."
          description="Facts, computed metrics, interpretation and hypotheses are always labelled — and every claim links to its sources."
        />
        <motion.div {...fadeUp} className="card mx-auto mt-10 max-w-2xl p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="warning">Interpretation</Badge>
            <Badge tone="positive">Evidence: high</Badge>
            <span className="text-xs text-ink-3">5 independent sources · illustrative</span>
          </div>
          <p className="mt-3 text-ink">Export restrictions are the main reported concern.</p>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-3 inline-flex items-center gap-1 text-sm text-primary-soft"
          >
            Show evidence{' '}
            <ChevronDown className={cn('h-4 w-4 transition-transform', open && 'rotate-180')} aria-hidden />
          </button>
          {open && (
            <ul className="mt-3 space-y-2">
              {EVIDENCE.map((e) => (
                <li
                  key={e.title}
                  className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2 text-sm"
                >
                  <span>
                    <span className="text-ink">{e.title}</span>
                    <span className="block text-xs text-ink-3">
                      {e.publisher} · {e.time}
                    </span>
                  </span>
                  <ExternalLink className="h-3.5 w-3.5 text-ink-3" aria-hidden />
                </li>
              ))}
            </ul>
          )}
        </motion.div>
      </div>
    </section>
  );
}

const PLANS = [
  {
    name: 'Free',
    price: '€0',
    features: ['Basic watchlist', 'Daily market brief', 'Limited investigations'],
    cta: 'Start free',
    highlight: false,
  },
  {
    name: 'Pro',
    price: '€19/mo',
    features: [
      'Deeper investigations',
      'Multimodal uploads (PDF, image, audio)',
      'Personalised audio briefings',
      'Larger watchlists',
    ],
    cta: 'Start researching',
    highlight: true,
  },
];

export function Pricing() {
  return (
    <section id="pricing" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-4xl">
        <SectionTitle
          center
          eyebrow="Pricing"
          title="Start free. Go deeper with Pro."
          description="Conceptual plans for this prototype — no payments are processed."
        />
        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {PLANS.map((p) => (
            <div key={p.name} className={cn('card p-6', p.highlight && 'glow border-primary/40')}>
              <div className="flex items-baseline justify-between">
                <h3 className="font-display text-xl font-semibold text-ink">{p.name}</h3>
                <p className="tabular font-display text-2xl font-semibold text-ink">{p.price}</p>
              </div>
              <ul className="mt-5 space-y-2.5">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-ink-2">
                    <Check className="h-4 w-4 text-positive" aria-hidden /> {f}
                  </li>
                ))}
              </ul>
              <Link to="/signup" className="mt-6 block">
                <Button className="w-full" variant={p.highlight ? 'gradient' : 'secondary'}>
                  {p.cta}
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
