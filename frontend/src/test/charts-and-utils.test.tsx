import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CandlestickChart, DriverContributionBars, RiskRadar, SentimentTimeline } from '@/components/charts';
import { buildEvidenceGraph } from '@/components/evidence/EvidenceGraph';
import { RiskMatrix } from '@/components/investigations/RiskPanel';
import { ErrorState } from '@/components/ui/states';
import { parseSseChunk } from '@/lib/api/sse';
import { encodeWav, downsample } from '@/lib/audio/wav';
import { direction, formatCompactMoney, formatPct, formatPrice, relativeTime } from '@/lib/formatting';
import { passwordProblem } from '@/lib/auth/password';
import { makeResult } from './utils';

describe('charts', () => {
  const candles = [
    { time: '2026-10-01', open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 },
    { time: '2026-10-02', open: 1.5, high: 2, low: 1, close: 1.2, volume: 20 },
  ];

  it('renders the candlestick chart container with an accessible label', () => {
    render(<CandlestickChart data={candles} label="NVDA price chart" />);
    expect(screen.getByRole('figure', { name: 'NVDA price chart' })).toBeInTheDocument();
  });

  it('shows empty and loading states', () => {
    const { rerender, container } = render(<CandlestickChart data={[]} />);
    expect(screen.getByText('No data available for this period.')).toBeInTheDocument();
    rerender(<CandlestickChart data={candles} loading />);
    expect(container.querySelector('[aria-hidden]')).toBeTruthy();
  });

  it('shows an error state', () => {
    render(<CandlestickChart data={candles} error="Provider down" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Provider down');
  });

  it('renders sentiment & risk charts with empty states', () => {
    render(<SentimentTimeline data={[]} />);
    expect(screen.getByText('No sentiment data for this period.')).toBeInTheDocument();
    render(<RiskRadar risks={[]} />);
    expect(screen.getByText('No assessed risks.')).toBeInTheDocument();
  });

  it('renders driver bars as accessible buttons and handles no drivers', () => {
    const { rerender } = render(<DriverContributionBars drivers={makeResult().drivers} />);
    expect(screen.getByRole('button', { name: /Export restrictions: 62 percent/ })).toBeInTheDocument();
    rerender(<DriverContributionBars drivers={[]} />);
    expect(screen.getByText(/No supporting source was found/)).toBeInTheDocument();
  });

  it('builds the evidence graph: root → drivers → sources (unknown ids ignored)', () => {
    const r = makeResult();
    const { nodes, edges } = buildEvidenceGraph('NVIDIA', -6.2, r.drivers, r.sources);
    expect(nodes.map((n) => n.type)).toEqual(['root', 'driver', 'source', 'driver']);
    expect(edges).toHaveLength(3);
  });

  it('risk matrix labels levels with text, not colour only', () => {
    render(<RiskMatrix risks={[{ risk: 'regulatory', level: 'HIGH', reason: '', evidence_ids: [] }]} />);
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('Regulatory')).toBeInTheDocument();
  });
});

describe('utilities', () => {
  it('parses SSE frames including ids and partial chunks', () => {
    const { events, rest } = parseSseChunk(
      'retry: 2000\n\nid: 5\nevent: progress\ndata: {"seq":5}\n\nevent: end\ndata: {"status":"completed"}\n\nid: 6\nevent: prog',
    );
    expect(events).toEqual([
      { event: 'progress', id: '5', data: '{"seq":5}' },
      { event: 'end', id: undefined, data: '{"status":"completed"}' },
    ]);
    expect(rest).toBe('id: 6\nevent: prog');
  });

  it('formats financial numbers', () => {
    expect(formatPct(-6.234)).toBe('-6.23%');
    expect(formatPct(1.5)).toBe('+1.50%');
    expect(formatPrice(180.5, 'USD')).toBe('$180.50');
    expect(formatPrice(null)).toBe('—');
    expect(formatCompactMoney(46_700_000_000)).toBe('$46.7B');
    expect(direction(-0.1)).toBe('down');
    expect(relativeTime(new Date(Date.now() - 8 * 60_000).toISOString())).toBe('8 minutes ago');
  });

  it('encodes microphone audio as 16-bit PCM WAV', async () => {
    const wav = encodeWav(downsample(new Float32Array(48000), 48000, 16000), 16000);
    expect(wav.size).toBe(44 + 16000 * 2);
    expect(new TextDecoder().decode(new Uint8Array(await wav.slice(0, 4).arrayBuffer()))).toBe('RIFF');
  });

  it('mirrors the Cognito password policy', () => {
    expect(passwordProblem('short')).toMatch(/8 characters/);
    expect(passwordProblem('alllowercase1')).toMatch(/upper/);
    expect(passwordProblem('Sup3rSecret')).toBeNull();
  });

  it('renders error states with retry', () => {
    render(<ErrorState message="Cannot reach SignalRoom." onRetry={() => {}} />);
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });
});
