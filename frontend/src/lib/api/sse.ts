// Investigation progress over Server-Sent Events.
// EventSource cannot send an Authorization header, so we read the SSE stream with fetch().
// The server closes the stream every ~50 s (CloudFront/ALB friendly) and we reconnect with
// Last-Event-ID. If streaming fails repeatedly we fall back to polling ?format=json.
import type { InvestigationEvent } from '@/types/api';
import { apiUrl, authHeaders, request } from './client';
import type { EventStreamHandlers } from './types';

const POLL_MS = 2000;

export function parseSseChunk(buffer: string): {
  events: { event: string; id?: string; data: string }[];
  rest: string;
} {
  const events: { event: string; id?: string; data: string }[] = [];
  const blocks = buffer.split(/\r?\n\r?\n/);
  const rest = blocks.pop() ?? '';
  for (const block of blocks) {
    let event = 'message';
    let id: string | undefined;
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith(':')) continue;
      const [field, ...restParts] = line.split(':');
      const value = restParts.join(':').replace(/^ /, '');
      if (field === 'event') event = value;
      else if (field === 'id') id = value;
      else if (field === 'data') data.push(value);
    }
    if (data.length || event !== 'message') events.push({ event, id, data: data.join('\n') });
  }
  return { events, rest };
}

export function subscribeToEvents(
  investigationId: string,
  handlers: EventStreamHandlers,
  afterSeq = 0,
): () => void {
  let lastSeq = afterSeq;
  let stopped = false;
  let failures = 0;
  let controller: AbortController | null = null;
  let pollTimer: ReturnType<typeof setTimeout> | null = null;

  const emit = (event: InvestigationEvent) => {
    if (event.seq <= lastSeq) return;
    lastSeq = event.seq;
    handlers.onEvent(event);
  };

  const poll = async () => {
    if (stopped) return;
    try {
      const events = await request<InvestigationEvent[]>(
        `/investigations/${investigationId}/events?format=json&after=${lastSeq}`,
      );
      events.forEach(emit);
      const last = events[events.length - 1];
      if (last && (last.event_type === 'completed' || last.event_type === 'failed')) {
        const inv = await request<{ status: string; followups: { status: string }[] }>(
          `/investigations/${investigationId}`,
        );
        if (!inv.followups.some((f) => f.status === 'queued' || f.status === 'running')) {
          handlers.onEnd?.(inv.status);
          return;
        }
      }
    } catch {
      /* transient: keep polling */
    }
    pollTimer = setTimeout(poll, POLL_MS);
  };

  const stream = async () => {
    while (!stopped) {
      controller = new AbortController();
      try {
        const resp = await fetch(apiUrl(`/investigations/${investigationId}/events?after=${lastSeq}`), {
          headers: {
            ...(await authHeaders()),
            Accept: 'text/event-stream',
            'Last-Event-ID': String(lastSeq),
          },
          signal: controller.signal,
        });
        if (!resp.ok || !resp.body) throw new Error(`SSE HTTP ${resp.status}`);
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let ended = false;
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parsed = parseSseChunk(buffer);
          buffer = parsed.rest;
          for (const msg of parsed.events) {
            if (msg.event === 'progress') emit(JSON.parse(msg.data) as InvestigationEvent);
            if (msg.event === 'end') {
              ended = true;
              handlers.onEnd?.((JSON.parse(msg.data || '{}') as { status?: string }).status ?? 'completed');
            }
          }
        }
        failures = 0;
        if (ended) return;
      } catch (err) {
        if (stopped || (err as Error).name === 'AbortError') return;
        failures += 1;
        if (failures >= 2) {
          handlers.onModeChange?.('polling');
          void poll();
          return;
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
    }
  };

  handlers.onModeChange?.('sse');
  void stream();
  return () => {
    stopped = true;
    controller?.abort();
    if (pollTimer) clearTimeout(pollTimer);
  };
}
