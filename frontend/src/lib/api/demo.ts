// Demo adapter (VITE_DEMO_MODE=true). Replays REAL SignalRoom runs recorded with
// scripts/record_demo_data.py — real market data, headlines, sources and model output.
// Progress events are replayed with compressed timing and clearly labelled as a replay.
import type {
  AssetDetail,
  AssetMatch,
  Briefing,
  BriefingPreferences,
  Investigation,
  InvestigationEvent,
  InvestigationSummary,
  MarketOverview,
  SearchHit,
  SearchModality,
  SearchResponse,
  Transcript,
  UploadView,
  WatchlistItem,
} from '@/types/api';
import assetsJson from '@demo/assets.json';
import briefingJson from '@demo/briefing.json';
import emailHtml from '@demo/email_preview.html?raw';
import investigationJson from '@demo/investigation.json';
import multimodalJson from '@demo/investigation_multimodal.json';
import videoJson from '@demo/investigation_video.json';
import type { EventStreamHandlers, SignalRoomApi } from './types';

interface Recording {
  investigation: Investigation;
  events: InvestigationEvent[];
  transcript?: Transcript | null;
}

const assets = assetsJson as unknown as {
  recorded_at: string;
  watchlist: WatchlistItem[];
  overview: MarketOverview;
  details: Record<string, Record<string, AssetDetail>>;
  search: AssetMatch[];
};
const recordings: Record<string, Recording> = {
  nvda: investigationJson as unknown as Recording,
  multimodal: multimodalJson as unknown as Recording,
  video: videoJson as unknown as Recording,
};
const REPLAY_MS = 11000;

let watchlist = [...assets.watchlist];
let preferences: BriefingPreferences = {
  enabled: true,
  local_time: '08:00',
  timezone: 'Europe/Madrid',
  email_enabled: false,
  audio_enabled: true,
  voice: 'professional',
};

interface Session {
  id: string;
  recording: Recording;
  startedAt: number;
  question: string;
  extraFollowups: Investigation['followups'];
}
const sessions = new Map<string, Session>();

function seed(id: string, key: keyof typeof recordings, startedAt: number): Session {
  const rec = recordings[key];
  const s: Session = {
    id,
    recording: rec,
    startedAt,
    question: rec.investigation.question,
    extraFollowups: [],
  };
  sessions.set(id, s);
  return s;
}
seed(recordings.nvda.investigation.investigation_id, 'nvda', 0);
seed(recordings.multimodal.investigation.investigation_id, 'multimodal', 0);
seed(recordings.video.investigation.investigation_id, 'video', 0);

function replayFraction(s: Session): number {
  return s.startedAt === 0 ? 1 : Math.min(1, (Date.now() - s.startedAt) / REPLAY_MS);
}

function replayedEvents(s: Session): InvestigationEvent[] {
  const events = s.recording.events;
  const visible = Math.ceil(events.length * replayFraction(s));
  return events.slice(0, visible).map((e, i) => ({ ...e, investigation_id: s.id, seq: i + 1 }));
}

function view(s: Session): Investigation {
  const base = s.recording.investigation;
  const done = replayFraction(s) >= 1;
  const events = replayedEvents(s);
  const last = events[events.length - 1];
  return {
    ...base,
    investigation_id: s.id,
    question: s.question,
    status: done ? 'completed' : (last?.status ?? 'running'),
    progress: done ? 100 : (last?.progress ?? 0),
    current_agent: done ? null : (last?.agent ?? null),
    status_message: done ? 'Investigation complete' : (last?.message ?? 'Queued'),
    result: done ? base.result : null,
    audio_status: done ? 'ready' : 'pending',
    audio_url: done ? '/demo/investigation.wav' : null,
    infographic_url: base.infographic_status === 'ready' ? '/demo/visual-brief.png' : null,
    followups: [...base.followups, ...s.extraFollowups],
  };
}

function delay<T>(value: T, ms = 250): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));
}

function detailFor(symbol: string, range: string): AssetDetail {
  const bySymbol = assets.details[symbol] ?? assets.details.NVDA;
  return bySymbol[range] ?? bySymbol['1mo'] ?? Object.values(bySymbol)[0];
}

// Demo search: keyword scoring over the recorded runs (the live app uses Gemini embeddings).
function demoSearch(q: string, modality: SearchModality): SearchResponse {
  const words = q
    .toLowerCase()
    .split(/W+/)
    .filter((w) => w.length > 2);
  const hits: SearchHit[] = [];
  const groups: Record<SearchModality, SearchHit['modality'][]> = {
    all: ['summary', 'driver', 'claim', 'news', 'document', 'image', 'audio', 'video'],
    analysis: ['summary', 'driver', 'claim'],
    news: ['news'],
    document: ['document'],
    image: ['image'],
    audio: ['audio'],
    video: ['video'],
  };
  for (const s of sessions.values()) {
    const inv = view(s);
    const r = inv.result;
    if (!r) continue;
    const chunks: [SearchHit['modality'], string, string, string | null][] = [
      ['summary', 'Executive summary', r.executive_summary, null],
      ...r.drivers.map((d): [SearchHit['modality'], string, string, string | null] => [
        'driver',
        'Driver: ' + d.name,
        d.explanation,
        null,
      ]),
      ...r.documents.flatMap((d) => [
        ['document', d.filename + ' - summary', d.summary, null] as [
          SearchHit['modality'],
          string,
          string,
          string | null,
        ],
        ...d.key_facts.map((f): [SearchHit['modality'], string, string, string | null] => [
          'document',
          d.filename + ' - key facts',
          f.fact + ': ' + (f.value ?? ''),
          f.page ? 'p. ' + f.page : null,
        ]),
      ]),
      ...r.images.map((i): [SearchHit['modality'], string, string, string | null] => [
        'image',
        i.filename,
        [...i.observations, i.interpretation].join(' '),
        null,
      ]),
      ...r.audio.flatMap((a) =>
        a.transcript_preview.map((t): [SearchHit['modality'], string, string, string | null] => [
          'audio',
          a.filename + ' - transcript',
          t.speaker + ': ' + t.text,
          t.start,
        ]),
      ),
      ...(r.videos ?? []).flatMap((v) => [
        ...v.slides.map((sl): [SearchHit['modality'], string, string, string | null] => [
          'video',
          v.filename + ' - slide: ' + sl.title,
          sl.description + ' ' + sl.figures.map((f) => f.fact + ': ' + f.value).join('; '),
          sl.timestamp,
        ]),
        ...v.transcript_preview.map((t): [SearchHit['modality'], string, string, string | null] => [
          'video',
          v.filename + ' - transcript',
          t.speaker + ': ' + t.text,
          t.start,
        ]),
      ]),
    ];
    for (const [mod, title, text, location] of chunks) {
      if (!groups[modality].includes(mod) || !text) continue;
      const hay = (title + ' ' + text).toLowerCase();
      const score = words.length ? words.filter((w) => hay.includes(w)).length / words.length : 0;
      if (score >= 0.5)
        hits.push({
          investigation_id: inv.investigation_id,
          symbol: inv.symbol,
          asset_name: inv.asset_name,
          question: inv.question,
          created_at: inv.created_at,
          modality: mod,
          title,
          snippet: text.slice(0, 420),
          ref: null,
          location,
          score,
        });
    }
  }
  hits.sort((a, b) => b.score - a.score);
  return { query: q, mode: 'keyword', indexed_investigations: sessions.size, hits: hits.slice(0, 20) };
}

export const demoApi: SignalRoomApi = {
  authConfig: () => delay({ mode: 'demo', invite_only: false }),
  health: () =>
    delay({
      status: 'ok',
      version: 'demo',
      backend: 'demo (recorded data)',
      auth: 'demo',
      checks: { api: 'ok' },
      providers: {
        openrouter: true,
        yahoo_finance: true,
        sec: true,
        gdelt: true,
        alpha_vantage: false,
        fred: false,
        ses: false,
      },
      ai_models: {
        reasoning: { provider: 'openrouter', model: 'openai/gpt-6-luna' },
        vision: { provider: 'openrouter', model: 'google/gemini-3.8-flash' },
        transcription: { provider: 'openrouter', model: 'google/gemini-3.8-flash' },
        tts: { provider: 'openrouter', model: 'openai/gpt-audio-mini' },
        image: { provider: 'openrouter', model: 'google/gemini-3.1-flash-image' },
      },
    }),
  me: () =>
    delay({
      user_id: 'demo-user',
      email: 'demo@signalroom.ai',
      preferences: { timezone: 'Europe/Madrid', display_currency: 'USD', briefing: preferences },
      created_at: assets.recorded_at,
      auth_mode: 'demo',
    }),
  deleteMyData: () => delay({ investigations: 0, briefings: 0, uploads: 0, files: 0 }),
  watchlist: () => delay(watchlist),
  async addToWatchlist(symbol) {
    const match = assets.search.find(
      (m) =>
        m.symbol.toLowerCase() === symbol.toLowerCase() ||
        m.name.toLowerCase().includes(symbol.toLowerCase()),
    );
    const item: WatchlistItem = {
      symbol: match?.symbol ?? symbol.toUpperCase(),
      display_name: match?.name ?? symbol,
      asset_type: match?.asset_type ?? 'equity',
      position: watchlist.length,
      added_at: new Date().toISOString(),
      quote: null,
    };
    watchlist = [...watchlist, item];
    return delay(item);
  },
  async removeFromWatchlist(symbol) {
    watchlist = watchlist.filter((w) => w.symbol !== symbol);
  },
  async reorderWatchlist(symbols) {
    watchlist = symbols.map((s, i) => ({
      ...(watchlist.find((w) => w.symbol === s) as WatchlistItem),
      position: i,
    }));
  },
  searchAssets: (q) => {
    const lower = q.toLowerCase();
    const seen = new Set<string>();
    return delay(
      assets.search
        .filter(
          (m) =>
            (m.symbol.toLowerCase().includes(lower) || m.name.toLowerCase().includes(lower)) &&
            !seen.has(m.symbol) &&
            seen.add(m.symbol),
        )
        .slice(0, 8),
    );
  },
  asset: (symbol, range) => delay(detailFor(symbol, range === '6mo' ? '1mo' : range), 350),
  marketOverview: () => delay(assets.overview),
  async createInvestigation(req) {
    const id = `demo_${Date.now().toString(36)}`;
    const ids = req.upload_ids ?? [];
    const key = ids.some((u) => u.startsWith('up_demo_video')) ? 'video' : ids.length ? 'multimodal' : 'nvda';
    const s = seed(id, key, Date.now());
    s.question = req.question;
    return delay({ investigation_id: id, status: 'queued' }, 400);
  },
  investigation: async (id) => {
    const s = sessions.get(id);
    if (!s) throw new Error('Investigation not found.');
    return delay(view(s), 150);
  },
  investigations: () =>
    delay(
      [...sessions.values()]
        .sort((a, b) => b.startedAt - a.startedAt)
        .map((s): InvestigationSummary => {
          const v = view(s);
          return {
            investigation_id: v.investigation_id,
            symbol: v.symbol,
            asset_name: v.asset_name,
            question: v.question,
            status: v.status,
            progress: v.progress,
            summary: v.result?.executive_summary ?? null,
            move_pct: v.result?.market?.metrics.move_pct ?? null,
            created_at: v.created_at,
            completed_at: v.completed_at,
          };
        }),
    ),
  async deleteInvestigation(id) {
    sessions.delete(id);
  },
  retryInvestigation: (id) => delay({ investigation_id: id, status: 'queued' }),
  async followUp(id, question) {
    const s = sessions.get(id);
    if (!s) throw new Error('Investigation not found.');
    const recorded = s.recording.investigation.followups[0];
    s.extraFollowups.push({
      followup_id: `fu_${Date.now()}`,
      question,
      status: 'completed',
      answer: recorded?.answer ?? 'Demo mode replays recorded answers only.',
      evidence_ids: recorded?.evidence_ids ?? [],
      agents_run: [],
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    });
    return delay({ followup_id: 'demo', status: 'queued' }, 900);
  },
  requestAudio: () => delay({ status: 'ready' as const }),
  requestInfographic: () => delay({ status: 'ready' as const }),
  search: (q, modality = 'all') => delay(demoSearch(q, modality), 300),
  searchByImage: (_file, modality = 'all') => delay(demoSearch('chart revenue price', modality), 600),
  transcript: async (id) => {
    const s = sessions.get(id);
    return delay(
      s?.recording.transcript ??
        recordings.multimodal.transcript ?? { language: 'en', speakers: [], segments: [] },
    );
  },
  subscribeToEvents(id: string, handlers: EventStreamHandlers, afterSeq = 0) {
    let last = afterSeq;
    handlers.onModeChange?.('sse');
    const timer = setInterval(() => {
      const s = sessions.get(id);
      if (!s) return;
      replayedEvents(s)
        .filter((e) => e.seq > last)
        .forEach((e) => {
          last = e.seq;
          handlers.onEvent(e);
        });
      if (replayFraction(s) >= 1) {
        clearInterval(timer);
        handlers.onEnd?.('completed');
      }
    }, 350);
    return () => clearInterval(timer);
  },
  async uploadFile(file, kind, onProgress): Promise<UploadView> {
    for (const pct of [20, 55, 85, 100]) {
      await delay(null, 120);
      onProgress?.(pct);
    }
    return {
      upload_id: `up_demo_${kind}_${Date.now()}`,
      kind,
      filename: file.name,
      content_type: file.type,
      size_bytes: file.size,
      status: 'uploaded',
      created_at: new Date().toISOString(),
    };
  },
  transcribeVoice: () =>
    delay(
      {
        text: 'Why did NVIDIA move today?',
        language: 'en',
        resolved_symbol: 'NVDA',
        resolved_name: 'NVIDIA Corporation',
      },
      900,
    ),
  briefings: () => {
    const b = briefingJson as unknown as Briefing;
    return delay([
      {
        briefing_id: b.briefing_id,
        date: b.date,
        briefing_type: b.briefing_type,
        status: b.status,
        headline: b.headline,
        audio_status: b.audio_status,
        created_at: b.created_at,
      },
    ]);
  },
  briefing: () => delay({ ...(briefingJson as unknown as Briefing), audio_url: '/demo/briefing.wav' }),
  generateBriefing: () =>
    delay({ briefing_id: (briefingJson as unknown as Briefing).briefing_id, status: 'completed' }, 600),
  emailPreview: () => delay(emailHtml as string),
  briefingPreferences: () => delay(preferences),
  async updateBriefingPreferences(patch) {
    preferences = { ...preferences, ...patch };
    return delay(preferences);
  },
};
