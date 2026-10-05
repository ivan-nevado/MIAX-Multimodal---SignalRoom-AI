import type {
  AssetDetail,
  AssetMatch,
  Briefing,
  BriefingPreferences,
  BriefingSummary,
  CreateInvestigationRequest,
  Health,
  Investigation,
  InvestigationEvent,
  InvestigationSummary,
  MarketOverview,
  Me,
  MediaStatus,
  SearchModality,
  SearchResponse,
  Transcript,
  UploadView,
  VoiceCommandResult,
  WatchlistItem,
} from '@/types/api';

export type HistoryRange = '1d' | '5d' | '1mo' | '6mo' | '1y';
export type UploadKind = 'document' | 'image' | 'audio' | 'video';

export interface EventStreamHandlers {
  onEvent: (event: InvestigationEvent) => void;
  onEnd?: (status: string) => void;
  onModeChange?: (mode: 'sse' | 'polling') => void;
}

/** The contract both the HTTP client and the demo adapter implement. */
export interface SignalRoomApi {
  health(): Promise<Health>;
  authConfig(): Promise<{ mode: string; invite_only: boolean }>;
  me(): Promise<Me>;
  deleteMyData(): Promise<Record<string, number>>;
  watchlist(): Promise<WatchlistItem[]>;
  addToWatchlist(symbol: string): Promise<WatchlistItem>;
  removeFromWatchlist(symbol: string): Promise<void>;
  reorderWatchlist(symbols: string[]): Promise<void>;
  searchAssets(q: string): Promise<AssetMatch[]>;
  asset(symbol: string, range: HistoryRange): Promise<AssetDetail>;
  marketOverview(): Promise<MarketOverview>;
  createInvestigation(req: CreateInvestigationRequest): Promise<{ investigation_id: string; status: string }>;
  investigation(id: string): Promise<Investigation>;
  investigations(limit?: number): Promise<InvestigationSummary[]>;
  deleteInvestigation(id: string): Promise<void>;
  retryInvestigation(id: string): Promise<{ investigation_id: string; status: string }>;
  followUp(
    id: string,
    question: string,
    uploadIds?: string[],
  ): Promise<{ followup_id: string; status: string }>;
  requestAudio(id: string): Promise<{ status: MediaStatus }>;
  requestInfographic(id: string): Promise<{ status: MediaStatus }>;
  transcript(id: string, uploadId: string): Promise<Transcript>;
  search(q: string, modality?: SearchModality): Promise<SearchResponse>;
  searchByImage(file: File, modality?: SearchModality): Promise<SearchResponse>;
  subscribeToEvents(id: string, handlers: EventStreamHandlers, afterSeq?: number): () => void;
  uploadFile(file: File, kind: UploadKind, onProgress?: (pct: number) => void): Promise<UploadView>;
  transcribeVoice(wav: Blob): Promise<VoiceCommandResult>;
  briefings(): Promise<BriefingSummary[]>;
  briefing(id: string): Promise<Briefing>;
  generateBriefing(withAudio: boolean, sendEmail: boolean): Promise<{ briefing_id: string; status: string }>;
  emailPreview(id: string): Promise<string>;
  briefingPreferences(): Promise<BriefingPreferences>;
  updateBriefingPreferences(patch: Partial<BriefingPreferences>): Promise<BriefingPreferences>;
}
