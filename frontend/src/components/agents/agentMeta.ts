import {
  AudioLines,
  Brain,
  CalendarClock,
  Clapperboard,
  FileText,
  Globe,
  Image as ImageIcon,
  LineChart,
  Mic,
  Network,
  Newspaper,
  Scale,
  ShieldAlert,
  Sparkles,
  Waves,
  type LucideIcon,
} from 'lucide-react';

export const AGENT_ICONS: Record<string, LucideIcon> = {
  orchestrator: Network,
  market: LineChart,
  news: Newspaper,
  financial: Scale,
  macro: Globe,
  document: FileText,
  vision: ImageIcon,
  audio: AudioLines,
  video: Clapperboard,
  sentiment: Waves,
  event_detection: CalendarClock,
  risk: ShieldAlert,
  evidence: Brain,
  synthesis: Sparkles,
  voice: Mic,
};

/** The research team shown on the landing page. */
export const RESEARCH_TEAM = [
  {
    name: 'Market Scout',
    agent: 'market',
    role: 'Measures the move: returns, volume, volatility and drawdown — computed, never guessed.',
  },
  {
    name: 'News Scout',
    agent: 'news',
    role: 'Finds, de-duplicates and clusters the headlines that matter, with links to the original source.',
  },
  {
    name: 'Financial Analyst',
    agent: 'financial',
    role: 'Reads SEC filings, reports, earnings calls and results webinars for revenue, margins, cash and guidance.',
  },
  {
    name: 'Risk Analyst',
    agent: 'risk',
    role: 'Flags regulatory, valuation, macro and liquidity risks — every flag cites its evidence.',
  },
  {
    name: 'Research Analyst',
    agent: 'evidence',
    role: 'Cross-checks each claim against sources and scores likely drivers transparently.',
  },
  {
    name: 'Chief Editor',
    agent: 'synthesis',
    role: 'Writes the brief: what happened, why it likely happened and what to watch next.',
  },
];
