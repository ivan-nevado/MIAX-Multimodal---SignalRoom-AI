// Local development auth against the FastAPI backend (AUTH_MODE=local). Not used in AWS.
import { config } from '@/lib/config';
import { AuthError, type AuthService, type Session, type SignUpResult } from './types';

const STORAGE_KEY = 'signalroom.local.session';

interface StoredSession {
  token: string;
  email: string;
  userId: string;
  expiresAt: number;
}

function read(): StoredSession | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredSession;
    return parsed.expiresAt > Date.now() ? parsed : null;
  } catch {
    return null;
  }
}

async function call(path: string, email: string, password: string): Promise<StoredSession> {
  const resp = await fetch(`${config.apiBaseUrl}/api/v1/auth/local/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const body = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
  if (!resp.ok)
    throw new AuthError(String(body.message ?? 'Authentication failed.'), String(body.error ?? 'auth_error'));
  const session: StoredSession = {
    token: String(body.access_token),
    email: String(body.email),
    userId: String(body.user_id),
    expiresAt: Date.now() + Number(body.expires_in) * 1000,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  return session;
}

export class LocalAuthService implements AuthService {
  readonly mode = 'local' as const;
  readonly supportsEmailVerification = false;

  async getSession(): Promise<Session | null> {
    const s = read();
    return s ? { email: s.email, userId: s.userId } : null;
  }

  async getToken(): Promise<string | null> {
    return read()?.token ?? null;
  }

  async signIn(email: string, password: string): Promise<Session> {
    const s = await call('login', email.trim().toLowerCase(), password);
    return { email: s.email, userId: s.userId };
  }

  async signUp(email: string, password: string): Promise<SignUpResult> {
    const s = await call('signup', email.trim().toLowerCase(), password);
    return { needsConfirmation: false, session: { email: s.email, userId: s.userId } };
  }

  async confirmSignUp(): Promise<void> {}
  async resendCode(): Promise<void> {}

  async forgotPassword(): Promise<void> {
    throw new AuthError(
      'Password reset by email is available with Amazon Cognito (cloud deployment).',
      'unsupported',
    );
  }

  async confirmForgotPassword(): Promise<void> {
    throw new AuthError(
      'Password reset by email is available with Amazon Cognito (cloud deployment).',
      'unsupported',
    );
  }

  async signOut(): Promise<void> {
    localStorage.removeItem(STORAGE_KEY);
  }
}
