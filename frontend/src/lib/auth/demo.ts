// Demo mode (VITE_DEMO_MODE=true): explore the full UI without credentials or a backend.
import type { AuthService, Session, SignUpResult } from './types';

const KEY = 'signalroom.demo.session';

export class DemoAuthService implements AuthService {
  readonly mode = 'demo' as const;
  readonly supportsEmailVerification = false;

  async getSession(): Promise<Session | null> {
    const email = sessionStorage.getItem(KEY);
    return email ? { email, userId: 'demo-user' } : null;
  }

  async getToken(): Promise<string | null> {
    return sessionStorage.getItem(KEY) ? 'demo-token' : null;
  }

  async signIn(email: string): Promise<Session> {
    const value = email.trim() || 'demo@signalroom.ai';
    sessionStorage.setItem(KEY, value);
    return { email: value, userId: 'demo-user' };
  }

  async signUp(email: string): Promise<SignUpResult> {
    return { needsConfirmation: false, session: await this.signIn(email) };
  }

  async confirmSignUp(): Promise<void> {}
  async resendCode(): Promise<void> {}
  async forgotPassword(): Promise<void> {}
  async confirmForgotPassword(): Promise<void> {}

  async signOut(): Promise<void> {
    sessionStorage.removeItem(KEY);
  }
}
