import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { InvestigationView } from '@/features/investigations/InvestigationView';
import { ResearchComposer } from '@/features/investigations/ResearchComposer';
import { deriveAgentProgress } from '@/hooks/useInvestigationStream';
import { api } from '@/lib/api';
import type { InvestigationEvent } from '@/types/api';
import { makeInvestigation, makeResult, renderWithProviders } from './utils';

vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return {
    ...actual,
    api: {
      createInvestigation: vi.fn(),
      subscribeToEvents: vi.fn(() => () => {}),
      retryInvestigation: vi.fn(),
      followUp: vi.fn(),
      requestAudio: vi.fn(),
      requestInfographic: vi.fn(),
      deleteInvestigation: vi.fn(),
      searchAssets: vi.fn(async () => []),
      transcript: vi.fn(),
    },
  };
});

const event = (seq: number, agent: string, phase: string, message: string): InvestigationEvent => ({
  investigation_id: 'inv_1',
  seq,
  timestamp: '',
  event_type: agent,
  message,
  agent,
  progress: seq * 10,
  status: 'running',
  metadata: { phase },
});

beforeEach(() => vi.clearAllMocks());

describe('investigation creation', () => {
  it('queues an investigation and navigates to its live page', async () => {
    vi.mocked(api.createInvestigation).mockResolvedValue({ investigation_id: 'inv_42', status: 'queued' });
    renderWithProviders(
      <ResearchComposer
        initialAsset={{
          symbol: 'NVDA',
          name: 'NVIDIA',
          asset_type: 'equity',
          exchange: null,
          source: 'alias',
        }}
      />,
      { route: '/app/research' },
    );
    await userEvent.type(
      screen.getByLabelText('What do you want to understand?'),
      'Why did NVIDIA fall today?',
    );
    await userEvent.click(screen.getByRole('button', { name: /investigate/i }));
    await waitFor(() =>
      expect(api.createInvestigation).toHaveBeenCalledWith({
        asset: 'NVDA',
        question: 'Why did NVIDIA fall today?',
        upload_ids: [],
        generate_audio: true,
      }),
    );
    expect(await screen.findByText('Investigation screen')).toBeInTheDocument();
  });

  it('shows a safe error when the API rejects the request', async () => {
    vi.mocked(api.createInvestigation).mockRejectedValue(
      new Error('Daily investigation limit reached for this prototype.'),
    );
    renderWithProviders(
      <ResearchComposer
        initialAsset={{
          symbol: 'NVDA',
          name: 'NVIDIA',
          asset_type: 'equity',
          exchange: null,
          source: 'alias',
        }}
      />,
    );
    await userEvent.type(screen.getByLabelText('What do you want to understand?'), 'Why?? today');
    await userEvent.click(screen.getByRole('button', { name: /investigate/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Daily investigation limit reached');
  });
});

describe('investigation states', () => {
  it('derives real agent progress from persisted events', () => {
    const agents = deriveAgentProgress(
      [
        event(1, 'orchestrator', 'completed', 'Assembled research team'),
        event(2, 'market', 'started', 'Market Agent started'),
        event(3, 'news', 'completed', 'Reviewed 32 articles'),
      ],
      ['market', 'news', 'synthesis'],
    );
    expect(agents.map((a) => [a.agent, a.state])).toEqual([
      ['orchestrator', 'completed'],
      ['market', 'running'],
      ['news', 'completed'],
      ['synthesis', 'pending'],
    ]);
  });

  it('renders the live progress view while running', () => {
    renderWithProviders(
      <InvestigationView
        investigation={makeInvestigation({
          status: 'collecting_data',
          progress: 40,
          result: null,
          status_message: 'Market Agent started',
        })}
      />,
    );
    expect(screen.getByText(/assembling your research team/i)).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: 'Investigation progress' })).toHaveAttribute(
      'aria-valuenow',
      '40',
    );
    expect(api.subscribeToEvents).toHaveBeenCalled();
  });

  it('renders summary, drivers and the evidence-weighted label when completed', async () => {
    renderWithProviders(<InvestigationView investigation={makeInvestigation()} />);
    expect(screen.getByText('NVIDIA fell 6.2% amid export headlines.')).toBeInTheDocument();
    expect(screen.getAllByText('Export restrictions').length).toBeGreaterThan(0);
    expect(screen.getByText('62%')).toBeInTheDocument();
    expect(screen.getByText(/Evidence-weighted contribution/)).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Risk' })).toBeInTheDocument();
  });

  it('shows a safe failure message with retry (never a traceback)', async () => {
    renderWithProviders(
      <InvestigationView
        investigation={makeInvestigation({
          status: 'failed',
          result: null,
          error:
            'Could not complete the investigation. Market data was available, but the news provider was unavailable. You can retry.',
        })}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('news provider was unavailable');
    await userEvent.click(screen.getByRole('button', { name: /retry/i }));
    expect(api.retryInvestigation).toHaveBeenCalledWith('inv_1');
  });

  it('flags when the AI narrative was unavailable', () => {
    renderWithProviders(
      <InvestigationView
        investigation={makeInvestigation({ result: makeResult({ ai_narrative_available: false }) })}
      />,
    );
    expect(screen.getByText(/deterministic metrics only/)).toBeInTheDocument();
  });
});
