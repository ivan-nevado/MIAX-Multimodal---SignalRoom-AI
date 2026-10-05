// React Query hooks: caching, loading states, retries and invalidation live here, not in components.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type HistoryRange } from '@/lib/api';
import type { BriefingPreferences, CreateInvestigationRequest, SearchModality } from '@/types/api';

export const keys = {
  me: ['me'] as const,
  health: ['health'] as const,
  watchlist: ['watchlist'] as const,
  overview: ['market-overview'] as const,
  asset: (symbol: string, range: HistoryRange) => ['asset', symbol, range] as const,
  search: (q: string) => ['asset-search', q] as const,
  investigations: ['investigations'] as const,
  investigation: (id: string) => ['investigation', id] as const,
  transcript: (id: string, upload: string) => ['transcript', id, upload] as const,
  briefings: ['briefings'] as const,
  briefing: (id: string) => ['briefing', id] as const,
  briefingPrefs: ['briefing-preferences'] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.me });
export const useHealth = () => useQuery({ queryKey: keys.health, queryFn: api.health, staleTime: 60_000 });
export const useWatchlist = () =>
  useQuery({ queryKey: keys.watchlist, queryFn: api.watchlist, refetchInterval: 120_000 });
export const useMarketOverview = () =>
  useQuery({ queryKey: keys.overview, queryFn: api.marketOverview, refetchInterval: 120_000 });
export const useAsset = (symbol: string, range: HistoryRange) =>
  useQuery({
    queryKey: keys.asset(symbol, range),
    queryFn: () => api.asset(symbol, range),
    enabled: Boolean(symbol),
  });
export const useAssetSearch = (q: string) =>
  useQuery({
    queryKey: keys.search(q),
    queryFn: () => api.searchAssets(q),
    enabled: q.trim().length >= 1,
    staleTime: 300_000,
  });
export const useInvestigations = (limit = 20) =>
  useQuery({ queryKey: [...keys.investigations, limit], queryFn: () => api.investigations(limit) });
export const useTranscript = (id: string, uploadId: string, enabled: boolean) =>
  useQuery({ queryKey: keys.transcript(id, uploadId), queryFn: () => api.transcript(id, uploadId), enabled });
export const useSemanticSearch = (q: string, modality: SearchModality) =>
  useQuery({
    queryKey: ['search', q, modality],
    queryFn: () => api.search(q, modality),
    enabled: q.trim().length >= 2,
    staleTime: 60_000,
  });
export const useBriefings = () => useQuery({ queryKey: keys.briefings, queryFn: api.briefings });
export const useBriefingPreferences = () =>
  useQuery({ queryKey: keys.briefingPrefs, queryFn: api.briefingPreferences });

export function useBriefing(id: string | undefined) {
  return useQuery({
    queryKey: keys.briefing(id ?? ''),
    queryFn: () => api.briefing(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const b = query.state.data;
      return b && (b.status === 'queued' || b.status === 'running' || b.audio_status === 'pending')
        ? 3000
        : false;
    },
  });
}

export function useInvestigation(id: string | undefined) {
  return useQuery({
    queryKey: keys.investigation(id ?? ''),
    queryFn: () => api.investigation(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const inv = query.state.data;
      if (!inv) return false;
      const busy =
        !['completed', 'failed'].includes(inv.status) ||
        inv.audio_status === 'pending' ||
        inv.infographic_status === 'pending' ||
        inv.followups.some((f) => f.status === 'queued' || f.status === 'running');
      return busy ? 4000 : false;
    },
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.addToWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.watchlist }),
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.removeFromWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.watchlist }),
  });
}

export function useReorderWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.reorderWatchlist,
    onSettled: () => qc.invalidateQueries({ queryKey: keys.watchlist }),
  });
}

export function useCreateInvestigation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: CreateInvestigationRequest) => api.createInvestigation(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.investigations }),
  });
}

export function useDeleteInvestigation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteInvestigation,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.investigations }),
  });
}

export function useInvestigationAction(id: string) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: keys.investigation(id) });
  return {
    retry: useMutation({ mutationFn: () => api.retryInvestigation(id), onSuccess: refresh }),
    followUp: useMutation({
      mutationFn: (v: { question: string; uploadIds?: string[] }) =>
        api.followUp(id, v.question, v.uploadIds),
      onSuccess: refresh,
    }),
    audio: useMutation({ mutationFn: () => api.requestAudio(id), onSuccess: refresh }),
    infographic: useMutation({ mutationFn: () => api.requestInfographic(id), onSuccess: refresh }),
  };
}

export function useGenerateBriefing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { withAudio: boolean; sendEmail: boolean }) =>
      api.generateBriefing(v.withAudio, v.sendEmail),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.briefings }),
  });
}

export function useUpdateBriefingPreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<BriefingPreferences>) => api.updateBriefingPreferences(patch),
    onSuccess: (data) => qc.setQueryData(keys.briefingPrefs, data),
  });
}

export function useDeleteMyData() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteMyData, onSuccess: () => qc.invalidateQueries() });
}
