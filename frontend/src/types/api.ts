// Types mirroring the FastAPI/Pydantic schemas (backend/app/schemas).

export type AssetType = 'equity' | 'etf' | 'index' | 'crypto' | 'fx' | 'commodity' | 'other';
export type EvidenceConfidence = 'high' | 'medium' | 'low';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type MediaStatus = 'none' | 'pending' | 'ready' | 'failed';
export type SourceType =
  | 'news'
  | 'market_data'
  | 'sec_filing'
  | 'financial_data'
  | 'macro'
  | 'document'
  | 'image'
  | 'audio'
  | 'video';

export interface Source {
  id: string;
  title: string;
  publisher: string | null;
  url: string | null;
  published_at: string | null;
  retrieved_at: string;
  source_type: SourceType;
  relevance: number;
  provider: string | null;
  tags: string[];
}

export interface ModelUsage {
  provider: string;
  model: string;
  purpose: string;
  agent: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number;
  cost_usd: number | null;
  ok: boolean;
}

export interface PricePoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface SeriesPoint {
  date: string;
  value: number;
}

export interface MarketMetrics {
  symbol: string;
  currency: string | null;
  as_of: string | null;
  last_price: number | null;
  previous_close: number | null;
  move_pct: number | null;
  return_5d_pct: number | null;
  return_1m_pct: number | null;
  volume: number | null;
  avg_volume_20d: number | null;
  volume_change_pct: number | null;
  volatility_20d: number | null;
  drawdown_30d: number | null;
  zscore_move: number | null;
  anomaly_score: number | null;
  ma_20: number | null;
  ma_50: number | null;
  day_high: number | null;
  day_low: number | null;
  benchmark_symbol: string | null;
  benchmark_move_pct: number | null;
  relative_performance_pct: number | null;
  unusual_move: boolean;
  observations: string[];
}

export interface MarketFindings {
  metrics: MarketMetrics;
  history: PricePoint[];
  intraday: PricePoint[];
  source_ids: string[];
}

export interface NewsArticle {
  id: string;
  title: string;
  url: string;
  publisher: string;
  published_at: string | null;
  retrieved_at: string;
  provider: string;
  tone: number | null;
  relevance: number;
}

export interface NewsCluster {
  cluster_id: string;
  theme: string;
  summary: string;
  event_type: string;
  tone: number | null;
  relevance: number;
  article_ids: string[];
  first_seen: string | null;
  source_count: number;
}

export interface NewsFindings {
  query: string;
  articles_reviewed: number;
  articles: NewsArticle[];
  clusters: NewsCluster[];
  tone_timeline: SeriesPoint[];
  volume_timeline: SeriesPoint[];
  providers_used: string[];
}

export interface SentimentFindings {
  overall_tone: number | null;
  recent_tone: number | null;
  prior_tone: number | null;
  sentiment_change: number | null;
  label: 'positive' | 'neutral' | 'negative' | 'unknown';
  agreement: 'aligned' | 'mixed' | 'divergent' | 'unknown';
  evidence_confidence: EvidenceConfidence;
  confidence_reason: string;
  timeline: SeriesPoint[];
  cluster_sentiment: { cluster_id: string; theme: string; tone: number }[];
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  event_type: string;
  title: string;
  description: string;
  origin: 'news' | 'market' | 'filing' | 'document' | 'audio' | 'image' | 'video';
  source_ids: string[];
}

export interface Filing {
  form: string;
  filed: string;
  description: string | null;
  url: string | null;
}

export interface FinancialSnapshot {
  applicable: boolean;
  note: string | null;
  entity_name: string | null;
  cik: string | null;
  fiscal_period: string | null;
  period_end: string | null;
  revenue: number | null;
  revenue_growth_yoy: number | null;
  revenue_growth_qoq: number | null;
  operating_income: number | null;
  operating_margin: number | null;
  net_income: number | null;
  net_margin: number | null;
  assets: number | null;
  liabilities: number | null;
  cash: number | null;
  debt: number | null;
  shares_outstanding: number | null;
  recent_filings: Filing[];
  source_ids: string[];
}

export interface MacroIndicator {
  id: string;
  name: string;
  value: number | null;
  change: number | null;
  unit: string;
  as_of: string | null;
  provider: string;
  series: SeriesPoint[];
  source_id: string | null;
}

export interface DocumentFact {
  fact: string;
  value: string | null;
  page: number | null;
}

export interface DocumentFindings {
  upload_id: string;
  filename: string;
  page_count: number;
  pages_analyzed: number[];
  summary: string;
  key_facts: DocumentFact[];
  visual_pages: {
    page: number;
    content_type: string;
    description: string;
    extracted_figures: DocumentFact[];
  }[];
  risks: string[];
  guidance: string[];
  source_id: string | null;
}

export interface ImageFindings {
  upload_id: string;
  filename: string;
  image_type: string;
  observations: string[];
  uncertainties: string[];
  relevant_levels: string[];
  detected_symbol: string | null;
  interpretation: string;
  source_id: string | null;
}

export interface TranscriptSegment {
  speaker: string;
  start: string | null;
  text: string;
}

export interface VideoSlide {
  timestamp: string | null;
  title: string;
  description: string;
  figures: { fact: string; value: string | null; page: number | null }[];
}

export interface VideoFindings {
  upload_id: string;
  filename: string;
  summary: string;
  language: string;
  speakers: string[];
  segment_count: number;
  transcript_preview: TranscriptSegment[];
  slides: VideoSlide[];
  key_points: string[];
  guidance: string[];
  management_tone: string;
  risks: string[];
  notable_quotes: string[];
  source_id: string | null;
}

export interface AudioFindings {
  upload_id: string;
  filename: string;
  language: string;
  speakers: string[];
  segment_count: number;
  transcript_preview: TranscriptSegment[];
  analysis: {
    summary: string;
    key_points: string[];
    guidance: string[];
    management_tone: string;
    risks: string[];
    notable_quotes: string[];
  } | null;
  source_id: string | null;
}

export interface RiskItem {
  risk: string;
  level: RiskLevel;
  reason: string;
  evidence_ids: string[];
}

export interface Driver {
  driver_id: string;
  name: string;
  category: string;
  explanation: string;
  contribution_score: number;
  raw_score: number;
  components: {
    relevance: number;
    source_support: number;
    temporal_alignment: number;
    sentiment_shift: number;
  } | null;
  evidence_ids: string[];
}

export interface Claim {
  claim_id: string;
  claim: string;
  claim_type: 'observed_fact' | 'derived_metric' | 'interpretation' | 'hypothesis';
  evidence_ids: string[];
  source_count: number;
  evidence_confidence: EvidenceConfidence;
}

export interface AgentRun {
  agent: string;
  status: 'completed' | 'failed' | 'skipped';
  summary: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
}

export interface AgentPlan {
  intent: string;
  agents: string[];
  rationale: string;
  time_window_days: number;
}

export interface InvestigationResult {
  symbol: string | null;
  asset_name: string | null;
  question: string;
  intent: string;
  executive_summary: string;
  what_happened: string;
  drivers: Driver[];
  market_context: string;
  financial_context: string;
  sentiment_summary: string;
  risk_summary: string;
  what_to_watch: string[];
  uncertainties: string[];
  claims: Claim[];
  market: MarketFindings | null;
  news: NewsFindings | null;
  sentiment: SentimentFindings | null;
  events: { events: TimelineEvent[] } | null;
  financial: FinancialSnapshot | null;
  macro: { indicators: MacroIndicator[]; notes: string[] } | null;
  risks: { items: RiskItem[] } | null;
  documents: DocumentFindings[];
  images: ImageFindings[];
  audio: AudioFindings[];
  videos?: VideoFindings[];
  sources: Source[];
  agent_runs: AgentRun[];
  model_usage: ModelUsage[];
  warnings: string[];
  ai_narrative_available: boolean;
  generated_at: string;
  disclaimer: string;
}

export interface FollowUp {
  followup_id: string;
  question: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  answer: string | null;
  evidence_ids: string[];
  agents_run: string[];
  created_at: string;
  completed_at: string | null;
}

export interface Attachment {
  upload_id: string;
  kind: 'document' | 'image' | 'audio' | 'video';
  filename: string;
  content_type: string;
  size_bytes: number;
}

export interface Investigation {
  investigation_id: string;
  symbol: string | null;
  asset_name: string | null;
  asset_type: string | null;
  question: string;
  status: string;
  progress: number;
  current_agent: string | null;
  status_message: string;
  plan: AgentPlan | null;
  attachments: Attachment[];
  result: InvestigationResult | null;
  error: string | null;
  audio_status: MediaStatus;
  audio_url: string | null;
  infographic_status: MediaStatus;
  infographic_url: string | null;
  followups: FollowUp[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface InvestigationSummary {
  investigation_id: string;
  symbol: string | null;
  asset_name: string | null;
  question: string;
  status: string;
  progress: number;
  summary: string | null;
  move_pct: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface InvestigationEvent {
  investigation_id: string;
  seq: number;
  timestamp: string;
  event_type: string;
  message: string;
  agent: string | null;
  progress: number | null;
  status: string | null;
  metadata: Record<string, unknown>;
}

export interface CreateInvestigationRequest {
  asset?: string | null;
  question: string;
  upload_ids?: string[];
  generate_audio?: boolean;
}

export interface AssetMatch {
  symbol: string;
  name: string;
  asset_type: AssetType;
  exchange: string | null;
  source: 'alias' | 'provider';
}

export interface AssetQuote {
  symbol: string;
  name: string;
  asset_type: AssetType;
  currency: string | null;
  last_price: number | null;
  previous_close: number | null;
  move_pct: number | null;
  retrieved_at: string;
  delayed_notice: string;
}

export interface NewsHeadline {
  id: string;
  title: string;
  url: string;
  publisher: string;
  published_at: string | null;
  relevance: number;
}

export interface AssetDetail {
  quote: AssetQuote;
  metrics: MarketMetrics | null;
  history: PricePoint[];
  range: string;
  news: NewsHeadline[];
  financial: FinancialSnapshot | null;
  recent_investigations: {
    investigation_id: string;
    question: string;
    status: string;
    created_at: string;
    summary: string | null;
  }[];
}

export interface WatchlistItem {
  symbol: string;
  display_name: string;
  asset_type: AssetType;
  position: number;
  added_at: string;
  quote: AssetQuote | null;
}

export interface MarketOverview {
  indices: AssetQuote[];
  retrieved_at: string;
  delayed_notice: string;
}

export interface BriefingSection {
  title: string;
  symbol: string | null;
  body: string;
  why_it_matters: string;
  source_ids: string[];
}

export interface WatchlistMove {
  symbol: string;
  name: string | null;
  last_price: number | null;
  move_pct: number | null;
  return_5d_pct: number | null;
  volume_change_pct: number | null;
  unusual_move: boolean;
}

export interface Briefing {
  briefing_id: string;
  user_id: string;
  date: string;
  briefing_type: 'daily' | 'on_demand';
  status: 'queued' | 'running' | 'completed' | 'failed';
  headline: string | null;
  greeting: string | null;
  summary: string | null;
  sections: BriefingSection[];
  top_events: string[];
  watchlist_moves: WatchlistMove[];
  macro_events: string[];
  risk_flags: string[];
  sources: Source[];
  audio_status: MediaStatus;
  audio_duration_seconds: number | null;
  audio_url: string | null;
  email_status: string;
  error: string | null;
  ai_narrative_available: boolean;
  created_at: string;
  completed_at: string | null;
  disclaimer: string;
}

export interface BriefingSummary {
  briefing_id: string;
  date: string;
  briefing_type: string;
  status: string;
  headline: string | null;
  audio_status: string;
  created_at: string;
}

export interface BriefingPreferences {
  enabled: boolean;
  local_time: string;
  timezone: string;
  email_enabled: boolean;
  audio_enabled: boolean;
  voice: 'professional';
}

export interface Me {
  user_id: string;
  email: string;
  preferences: { timezone: string; display_currency: string; briefing: BriefingPreferences };
  created_at: string;
  auth_mode: string;
}

export interface PresignResponse {
  upload_id: string;
  upload_url: string;
  method: 'PUT';
  headers: Record<string, string>;
  expires_in: number;
}

export interface UploadView {
  upload_id: string;
  kind: 'document' | 'image' | 'audio' | 'video';
  filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface Transcript {
  language: string;
  speakers: string[];
  segments: TranscriptSegment[];
}

export interface VoiceCommandResult {
  text: string;
  language: string | null;
  resolved_symbol: string | null;
  resolved_name: string | null;
}

export interface Health {
  status: string;
  version: string;
  backend: string;
  auth: string;
  checks: Record<string, string>;
  providers: Record<string, boolean>;
  ai_models: Record<string, { provider: string; model: string }>;
}

export type SearchModality = 'all' | 'analysis' | 'news' | 'document' | 'image' | 'audio' | 'video';

export interface SearchHit {
  investigation_id: string;
  symbol: string | null;
  asset_name: string | null;
  question: string;
  created_at: string;
  modality: 'summary' | 'driver' | 'claim' | 'news' | 'document' | 'image' | 'audio' | 'video';
  title: string;
  snippet: string;
  ref: string | null;
  location: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  mode: 'semantic' | 'keyword' | 'image';
  indexed_investigations: number;
  hits: SearchHit[];
}
