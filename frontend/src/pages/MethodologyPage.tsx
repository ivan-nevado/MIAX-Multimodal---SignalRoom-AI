import { PublicLayout, Section } from '@/components/layout/PublicLayout';
import { RESEARCH_TEAM } from '@/components/agents/agentMeta';

const SOURCES = [
  [
    'Yahoo Finance (yfinance)',
    'No key',
    'Prices, volume, quotes, search and headlines. Possibly delayed; research use.',
  ],
  [
    'SEC EDGAR',
    'No key',
    'Company facts (revenue, margins, cash, debt) and recent filings for U.S. registrants.',
  ],
  [
    'GDELT DOC 2.0',
    'No key',
    'Global news discovery, tone and volume timelines (rate limited, with automatic fallback).',
  ],
  ['Alpha Vantage', 'Free key (optional)', 'Fallback daily prices and news sentiment.'],
  ['FRED', 'Free key (optional)', 'Macro series: Fed funds, CPI, unemployment, GDP, 10-year yield.'],
];

export default function MethodologyPage() {
  return (
    <PublicLayout
      title="Methodology"
      intro="How SignalRoom turns market data, news, filings, documents, charts, audio and video into a sourced explanation."
    >
      <Section id="agents" title="The AI research team">
        <p>
          An orchestrator reads your question and attachments and assembles only the agents needed. Collection
          agents run in parallel; analysis agents then cross-check the evidence; a synthesis agent writes the
          brief.
        </p>
        <ul className="space-y-2">
          {RESEARCH_TEAM.map((m) => (
            <li key={m.name}>
              <span className="font-medium text-ink">{m.name}.</span> {m.role}
            </li>
          ))}
        </ul>
        <p>
          Documents are read with text extraction first and a vision model only on table- or chart-heavy
          pages; audio is transcribed with speaker turns and quotes are verified word-for-word against the
          transcript. Videos (results webinars, investor presentations) are read in one multimodal pass: the
          speech and the slides shown on screen, with timestamps and the figures exactly as displayed. Every
          finished investigation is indexed with a multimodal embedding model, so you can search all your
          research by meaning, or with an image, across transcripts, slides, PDF pages, charts and news.
        </p>
      </Section>
      <Section id="data-sources" title="Data sources">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead>
              <tr className="text-xs text-ink-3 uppercase">
                <th className="pb-2 font-medium">Source</th>
                <th className="pb-2 font-medium">Access</th>
                <th className="pb-2 font-medium">Used for</th>
              </tr>
            </thead>
            <tbody>
              {SOURCES.map(([name, access, use]) => (
                <tr key={name} className="border-t border-line/70">
                  <td className="py-2 pr-3 text-ink">{name}</td>
                  <td className="py-2 pr-3">{access}</td>
                  <td className="py-2">{use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          Every datum records its source and retrieval time (and publication time when available). Headlines
          link to the original publisher; article bodies are not copied.
        </p>
      </Section>
      <Section id="evidence-scoring" title="Evidence-weighted contribution">
        <p>
          For each candidate driver (a news theme, broad market pressure or an uploaded disclosure) SignalRoom
          computes:
        </p>
        <pre className="overflow-x-auto rounded-xl border border-line bg-surface p-4 text-xs leading-relaxed text-ink">
          {`raw = relevance × source_support × temporal_alignment × sentiment_factor

source_support     = 1 − exp(−independent_publishers / 3)
temporal_alignment = 1 near the session, then decays with distance (min 0.2)
sentiment_factor   = 0.75 … 1.25 (tone agrees with the direction of the move)
contribution       = raw / Σ raw × 100   (top drivers, renormalised)`}
        </pre>
        <p>
          This is a transparent heuristic computed in code — not a probability and not a causal model.
          Language models never produce these numbers; they only explain the drivers.
        </p>
      </Section>
      <Section id="safeguards" title="Accuracy safeguards">
        <ul className="list-disc space-y-2 pl-5">
          <li>All statistics are computed deterministically; models only interpret structured results.</li>
          <li>
            Every model answer is validated against a schema; invalid answers are retried once, then the
            system degrades gracefully.
          </li>
          <li>
            Claims citing unknown sources are removed; facts without evidence are dropped; unhedged causal
            language is softened.
          </li>
          <li>
            Facts, derived metrics, interpretations and hypotheses are labelled separately; “Not enough
            evidence available” is preferred to speculation.
          </li>
        </ul>
      </Section>
    </PublicLayout>
  );
}
