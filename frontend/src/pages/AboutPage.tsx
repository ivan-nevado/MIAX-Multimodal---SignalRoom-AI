import { Link } from 'react-router-dom';
import { PublicLayout, Section } from '@/components/layout/PublicLayout';

export default function AboutPage() {
  return (
    <PublicLayout
      title="About SignalRoom"
      intro="SignalRoom is an AI financial intelligence room built as a startup MVP for the MIAX programme (workshop B5-T4: design and prototyping of a FinTech startup based on multimodal AI)."
    >
      <Section title="Our mission">
        <p>
          Markets produce information in every format — prices, headlines, filings, earnings calls, charts.
          Understanding a single move can take hours. SignalRoom puts a team of specialised AI agents to work
          so anyone can answer <em>“What moved the market, and why?”</em> in minutes, with the evidence one
          click away.
        </p>
      </Section>
      <Section title="What makes it different">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            An orchestrated research team, not a single chatbot: each agent has one job and only the agents a
            question needs are run.
          </li>
          <li>
            Numbers come from code (returns, volatility, fundamentals); language models interpret them and
            never invent figures.
          </li>
          <li>
            Every important claim links to its sources, and likely drivers are scored with a transparent
            formula.
          </li>
          <li>
            Multimodal in and out: PDFs, chart screenshots, earnings-call audio and voice questions in;
            written briefs, charts, evidence graphs, narrated audio and email out.
          </li>
        </ul>
      </Section>
      <Section title="Status">
        <p>
          SignalRoom is an educational prototype. It does not provide personalised investment advice, does not
          execute trades and is not a regulated financial service. See the{' '}
          <Link className="text-primary-soft hover:text-ink" to="/terms">
            Terms
          </Link>{' '}
          and the{' '}
          <Link className="text-primary-soft hover:text-ink" to="/privacy">
            Privacy notice
          </Link>
          .
        </p>
      </Section>
      <Section title="How it works">
        <p>
          Read the{' '}
          <Link className="text-primary-soft hover:text-ink" to="/methodology">
            methodology
          </Link>{' '}
          for the agent architecture, data sources and how driver contributions are computed.
        </p>
      </Section>
    </PublicLayout>
  );
}
