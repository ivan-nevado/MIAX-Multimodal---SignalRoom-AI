import type {
  AssetDetail,
  AssetMatch,
  Briefing,
  BriefingPreferences,
  BriefingSummary,
  Health,
  Investigation,
  InvestigationSummary,
  MarketOverview,
  Me,
  MediaStatus,
  SearchResponse,
  PresignResponse,
  Transcript,
  UploadView,
  VoiceCommandResult,
  WatchlistItem,
} from '@/types/api';
import { apiUrl, authHeaders, request, ApiError } from './client';
import { subscribeToEvents } from './sse';
import type { SignalRoomApi, UploadKind } from './types';

/** Browser → storage upload with progress (XMLHttpRequest exposes upload progress; fetch does not). */
function putWithProgress(
  url: string,
  file: File,
  headers: Record<string, string>,
  onProgress?: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    Object.entries(headers).forEach(([k, v]) => xhr.setRequestHeader(k, v));
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new ApiError('Upload failed. Please retry.', xhr.status, 'upload_failed'));
    xhr.onerror = () => reject(new ApiError('Upload failed: network error.', 0, 'upload_failed'));
    xhr.send(file);
  });
}

function mimeFor(file: File): string {
  if (file.type) return file.type;
  const ext = file.name.toLowerCase().split('.').pop() ?? '';
  return (
    (
      {
        pdf: 'application/pdf',
        png: 'image/png',
        jpg: 'image/jpeg',
        jpeg: 'image/jpeg',
        webp: 'image/webp',
        mp3: 'audio/mpeg',
        wav: 'audio/wav',
        m4a: 'audio/mp4',
        ogg: 'audio/ogg',
        flac: 'audio/flac',
        mp4: 'video/mp4',
        webm: 'video/webm',
        mov: 'video/quicktime',
      } as Record<string, string>
    )[ext] ?? 'application/octet-stream'
  );
}

export const httpApi: SignalRoomApi = {
  health: () => request<Health>('/health'),
  authConfig: () => request<{ mode: string; invite_only: boolean }>('/auth/config'),
  me: () => request<Me>('/me'),
  deleteMyData: () => request('/me/data', { method: 'DELETE' }),
  watchlist: () => request<WatchlistItem[]>('/watchlist'),
  addToWatchlist: (symbol) => request<WatchlistItem>('/watchlist', { method: 'POST', body: { symbol } }),
  removeFromWatchlist: (symbol) =>
    request<void>(`/watchlist/${encodeURIComponent(symbol)}`, { method: 'DELETE' }),
  reorderWatchlist: (symbols) => request<void>('/watchlist/order', { method: 'PUT', body: { symbols } }),
  searchAssets: (q) => request<AssetMatch[]>(`/assets/search?q=${encodeURIComponent(q)}`),
  asset: (symbol, range) => request<AssetDetail>(`/assets/${encodeURIComponent(symbol)}?range=${range}`),
  marketOverview: () => request<MarketOverview>('/market/overview'),
  createInvestigation: (req) =>
    request('/investigations', { method: 'POST', body: req as unknown as Record<string, unknown> }),
  investigation: (id) => request<Investigation>(`/investigations/${id}`),
  investigations: (limit = 20) => request<InvestigationSummary[]>(`/investigations?limit=${limit}`),
  deleteInvestigation: (id) => request<void>(`/investigations/${id}`, { method: 'DELETE' }),
  retryInvestigation: (id) => request(`/investigations/${id}/retry`, { method: 'POST' }),
  followUp: (id, question, uploadIds = []) =>
    request(`/investigations/${id}/followups`, { method: 'POST', body: { question, upload_ids: uploadIds } }),
  requestAudio: (id) => request<{ status: MediaStatus }>(`/investigations/${id}/audio`, { method: 'POST' }),
  requestInfographic: (id) =>
    request<{ status: MediaStatus }>(`/investigations/${id}/infographic`, { method: 'POST' }),
  transcript: (id, uploadId) => request<Transcript>(`/investigations/${id}/transcripts/${uploadId}`),
  search: (q, modality = 'all') =>
    request<SearchResponse>(`/search?q=${encodeURIComponent(q)}&modality=${modality}`),
  searchByImage: (file, modality = 'all') => {
    const form = new FormData();
    form.append('file', file);
    return request<SearchResponse>(`/search/by-image?modality=${modality}`, { method: 'POST', body: form });
  },
  subscribeToEvents,
  async uploadFile(file: File, kind: UploadKind, onProgress?: (pct: number) => void): Promise<UploadView> {
    const contentType = mimeFor(file);
    const presign = await request<PresignResponse>('/uploads/presign', {
      method: 'POST',
      body: { filename: file.name, content_type: contentType, size_bytes: file.size, kind },
    });
    await putWithProgress(presign.upload_url, file, presign.headers, onProgress);
    return request<UploadView>('/uploads/complete', {
      method: 'POST',
      body: { upload_id: presign.upload_id },
    });
  },
  transcribeVoice(wav: Blob) {
    const form = new FormData();
    form.append('file', wav, 'voice-command.wav');
    return request<VoiceCommandResult>('/voice/transcribe', { method: 'POST', body: form });
  },
  briefings: () => request<BriefingSummary[]>('/briefings'),
  briefing: (id) => request<Briefing>(`/briefings/${id}`),
  generateBriefing: (withAudio, sendEmail) =>
    request('/briefings/generate', {
      method: 'POST',
      body: { with_audio: withAudio, send_email: sendEmail },
    }),
  async emailPreview(id) {
    const resp = await fetch(apiUrl(`/briefings/${id}/email-preview`), { headers: await authHeaders() });
    if (!resp.ok) throw new ApiError('Email preview is not available yet.', resp.status);
    return resp.text();
  },
  briefingPreferences: () => request<BriefingPreferences>('/preferences/briefing'),
  updateBriefingPreferences: (patch) =>
    request<BriefingPreferences>('/preferences/briefing', { method: 'PATCH', body: patch }),
};
