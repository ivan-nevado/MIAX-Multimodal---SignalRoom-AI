export interface Session {
  email: string;
  userId: string;
}

export interface SignUpResult {
  needsConfirmation: boolean;
  session: Session | null;
}

/** One interface, three implementations: Cognito (AWS), local backend (dev) and demo (no backend). */
export interface AuthService {
  readonly mode: 'cognito' | 'local' | 'demo';
  readonly supportsEmailVerification: boolean;
  getSession(): Promise<Session | null>;
  getToken(): Promise<string | null>;
  signIn(email: string, password: string): Promise<Session>;
  signUp(email: string, password: string): Promise<SignUpResult>;
  confirmSignUp(email: string, code: string): Promise<void>;
  resendCode(email: string): Promise<void>;
  forgotPassword(email: string): Promise<void>;
  confirmForgotPassword(email: string, code: string, newPassword: string): Promise<void>;
  signOut(): Promise<void>;
}

export class AuthError extends Error {
  constructor(
    message: string,
    public readonly code: string = 'auth_error',
  ) {
    super(message);
  }
}
