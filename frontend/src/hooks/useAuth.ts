import { createContext, useContext } from 'react';
import type { AuthService, Session, SignUpResult } from '@/lib/auth';

export interface AuthState {
  service: AuthService | null;
  session: Session | null;
  loading: boolean;
  /** Reason shown on the login page after a forced sign-out (e.g. not on the invite list). */
  notice: string | null;
  signIn(email: string, password: string): Promise<Session>;
  signUp(email: string, password: string): Promise<SignUpResult>;
  signOut(): Promise<void>;
}

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
