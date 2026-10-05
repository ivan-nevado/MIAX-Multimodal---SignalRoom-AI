import { config } from '@/lib/config';
import { httpApi } from './http';
import type { EventStreamHandlers, SignalRoomApi } from './types';

export { ApiError } from './client';
export type { HistoryRange, SignalRoomApi, UploadKind } from './types';

/**
 * In demo mode the recorded-data adapter is loaded lazily (keeps ~600 KB of recorded
 * JSON out of the normal bundle). Every other build talks to the FastAPI backend.
 */
function lazyDemo(): SignalRoomApi {
  const load = () => import('./demo').then((m) => m.demoApi);
  return new Proxy({} as SignalRoomApi, {
    get(_target, prop: keyof SignalRoomApi) {
      if (prop === 'subscribeToEvents') {
        return (id: string, handlers: EventStreamHandlers, after?: number) => {
          let unsubscribe: (() => void) | null = null;
          let cancelled = false;
          void load().then((api) => {
            if (!cancelled) unsubscribe = api.subscribeToEvents(id, handlers, after);
          });
          return () => {
            cancelled = true;
            unsubscribe?.();
          };
        };
      }
      return async (...args: unknown[]) => {
        const api = await load();
        return (api[prop] as (...a: unknown[]) => unknown)(...args);
      };
    },
  });
}

export const api: SignalRoomApi = config.demoMode ? lazyDemo() : httpApi;
