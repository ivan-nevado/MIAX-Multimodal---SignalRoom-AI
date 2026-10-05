import { config } from '@/lib/config';
import { getAuthService } from '@/lib/auth';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string = 'error',
    public readonly requestId?: string,
  ) {
    super(message);
  }
}

type Json = Record<string, unknown> | unknown[];

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: Json | FormData;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export async function authHeaders(): Promise<Record<string, string>> {
  const token = await getAuthService()?.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function apiUrl(path: string): string {
  return `${config.apiBaseUrl}/api/v1${path}`;
}

/** Fetch wrapper: auth header, JSON, safe user-facing errors (never stack traces). */
export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...(await authHeaders()), ...opts.headers };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  let resp: Response;
  try {
    resp = await fetch(apiUrl(path), { method: opts.method ?? 'GET', headers, body, signal: opts.signal });
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err;
    throw new ApiError('Cannot reach SignalRoom. Check your connection and try again.', 0, 'network_error');
  }
  if (resp.status === 204) return undefined as T;
  const text = await resp.text();
  let data: unknown = undefined;
  try {
    data = text ? JSON.parse(text) : undefined;
  } catch {
    data = text;
  }
  if (!resp.ok) {
    const err = (data ?? {}) as { message?: string; error?: string; request_id?: string };
    const message = typeof err.message === 'string' ? err.message : 'Something went wrong. Please retry.';
    if (resp.status === 401) window.dispatchEvent(new CustomEvent('signalroom:unauthorized'));
    if (resp.status === 403 && err.error === 'not_invited')
      window.dispatchEvent(new CustomEvent('signalroom:unauthorized', { detail: message }));
    throw new ApiError(message, resp.status, err.error ?? 'error', err.request_id);
  }
  return data as T;
}
