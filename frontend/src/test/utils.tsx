import type { ReactElement } from 'react';
import { render } from '@testing-library/react';
import { QueryClient } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AppProviders } from '@/app/providers/AppProviders';
import type { AuthService, Session } from '@/lib/auth';
import type { Investigation, InvestigationResult } from '@/types/api';

export function fakeAuth(session: Session | null = { email: 'ana@example.com', userId: 'u1' }): AuthService {
  let current = session;
  return {
    mode: 'local',
    supportsEmailVerification: false,
    getSession: async () => current,
    getToken: async () => (current ? 'token' : null),
    signIn: async (email) => (current = { email, userId: 'u1' }),
    signUp: async (email) => ({ needsConfirmation: false, session: (current = { email, userId: 'u1' }) }),
    confirmSignUp: async () => {},
    resendCode: async () => {},
    forgotPassword: async () => {},
    confirmForgotPassword: async () => {},
    signOut: async () => {
      current = null;
    },
  };
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', path = '*', auth = fakeAuth() }: { route?: string; path?: string; auth?: AuthService } = {},
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <AppProviders authService={auth} client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={ui} />
          <Route path="/login" element={<p>Login screen</p>} />
          <Route path="/app/investigation/:id" element={<p>Investigation screen</p>} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  );
}

export function makeResult(overrides: Partial<InvestigationResult> = {}): InvestigationResult {
  return {
    symbol: 'NVDA',
    asset_name: 'NVIDIA Corporation',
    question: 'Why did NVIDIA fall today?',
    intent: 'why_move',
    executive_summary: 'NVIDIA fell 6.2% amid export headlines.',
    what_happened: 'The stock declined on heavy volume.',
    drivers: [
      {
        driver_id: 'd1',
        name: 'Export restrictions',
        category: 'regulation',
        explanation: 'Reported by five publishers.',
        contribution_score: 62,
        raw_score: 0.5,
        components: null,
        evidence_ids: ['s1'],
      },
      {
        driver_id: 'd2',
        name: 'Valuation concerns',
        category: 'other',
        explanation: '',
        contribution_score: 38,
        raw_score: 0.3,
        components: null,
        evidence_ids: [],
      },
    ],
    market_context: '',
    financial_context: '',
    sentiment_summary: '',
    risk_summary: 'Regulatory risk is elevated.',
    what_to_watch: ['Further export guidance'],
    uncertainties: ['Timing of headlines'],
    claims: [],
    market: null,
    news: null,
    sentiment: null,
    events: null,
    financial: null,
    macro: null,
    risks: { items: [{ risk: 'regulatory', level: 'HIGH', reason: 'Export rules.', evidence_ids: ['s1'] }] },
    documents: [],
    images: [],
    audio: [],
    sources: [
      {
        id: 's1',
        title: 'U.S. tightens export rules',
        publisher: 'reuters.com',
        url: 'https://reuters.com/a',
        published_at: null,
        retrieved_at: new Date().toISOString(),
        source_type: 'news',
        relevance: 0.9,
        provider: 'gdelt',
        tags: [],
      },
    ],
    agent_runs: [
      {
        agent: 'market',
        status: 'completed',
        summary: 'Analyzed price, volatility and volume',
        started_at: '',
        finished_at: '',
        duration_ms: 1200,
      },
    ],
    model_usage: [],
    warnings: [],
    ai_narrative_available: true,
    generated_at: new Date().toISOString(),
    disclaimer: 'Educational prototype.',
    ...overrides,
  };
}

export function makeInvestigation(overrides: Partial<Investigation> = {}): Investigation {
  return {
    investigation_id: 'inv_1',
    symbol: 'NVDA',
    asset_name: 'NVIDIA Corporation',
    asset_type: 'equity',
    question: 'Why did NVIDIA fall today?',
    status: 'completed',
    progress: 100,
    current_agent: null,
    status_message: 'Investigation complete',
    plan: {
      intent: 'why_move',
      agents: ['market', 'news', 'evidence', 'synthesis'],
      rationale: '',
      time_window_days: 7,
    },
    attachments: [],
    result: makeResult(),
    error: null,
    audio_status: 'none',
    audio_url: null,
    infographic_status: 'none',
    infographic_url: null,
    followups: [],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
    ...overrides,
  };
}
