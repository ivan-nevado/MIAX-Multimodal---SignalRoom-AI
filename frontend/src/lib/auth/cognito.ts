// Amazon Cognito User Pools (public SPA client, no secret). Sessions persist in localStorage.
import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserAttribute,
  CognitoUserPool,
  type CognitoUserSession,
} from 'amazon-cognito-identity-js';
import { AuthError, type AuthService, type Session, type SignUpResult } from './types';

function friendly(err: unknown): AuthError {
  const e = err as { code?: string; name?: string; message?: string };
  const code = e.code ?? e.name ?? 'auth_error';
  const messages: Record<string, string> = {
    NotAuthorizedException: 'Incorrect email or password.',
    UserNotFoundException: 'Incorrect email or password.',
    UserNotConfirmedException: 'Please verify your email address first.',
    UsernameExistsException: 'An account with this email already exists.',
    CodeMismatchException: 'That verification code is not correct.',
    ExpiredCodeException: 'That code has expired. Request a new one.',
    InvalidPasswordException:
      'Password must be at least 8 characters with upper, lower case letters and numbers.',
    LimitExceededException: 'Too many attempts. Please wait a moment and try again.',
    // Raised by the pre sign-up Lambda (terraform/modules/cognito) for emails not on the invite list.
    UserLambdaValidationException: 'This SignalRoom demo is invite-only. Ask the team to add your email.',
  };
  return new AuthError(messages[code] ?? e.message ?? 'Authentication failed.', code);
}

export class CognitoAuthService implements AuthService {
  readonly mode = 'cognito' as const;
  readonly supportsEmailVerification = true;
  private pool: CognitoUserPool;

  constructor(userPoolId: string, clientId: string) {
    this.pool = new CognitoUserPool({ UserPoolId: userPoolId, ClientId: clientId });
  }

  private user(email: string): CognitoUser {
    return new CognitoUser({ Username: email.trim().toLowerCase(), Pool: this.pool });
  }

  private currentSession(): Promise<CognitoUserSession | null> {
    const user = this.pool.getCurrentUser();
    if (!user) return Promise.resolve(null);
    return new Promise((resolve) => {
      // getSession transparently refreshes expired tokens with the refresh token.
      user.getSession((err: Error | null, session: CognitoUserSession | null) => {
        resolve(err || !session?.isValid() ? null : session);
      });
    });
  }

  async getSession(): Promise<Session | null> {
    const session = await this.currentSession();
    if (!session) return null;
    const payload = session.getIdToken().decodePayload();
    return { email: String(payload.email ?? ''), userId: String(payload.sub ?? '') };
  }

  async getToken(): Promise<string | null> {
    const session = await this.currentSession();
    // The ID token carries the email claim; the backend validates signature, issuer, audience and expiry.
    return session ? session.getIdToken().getJwtToken() : null;
  }

  signIn(email: string, password: string): Promise<Session> {
    const user = this.user(email);
    const details = new AuthenticationDetails({ Username: email.trim().toLowerCase(), Password: password });
    return new Promise((resolve, reject) => {
      user.authenticateUser(details, {
        onSuccess: (session) => {
          const payload = session.getIdToken().decodePayload();
          resolve({ email: String(payload.email ?? email), userId: String(payload.sub) });
        },
        onFailure: (err) => reject(friendly(err)),
      });
    });
  }

  signUp(email: string, password: string): Promise<SignUpResult> {
    const attrs = [new CognitoUserAttribute({ Name: 'email', Value: email.trim().toLowerCase() })];
    return new Promise((resolve, reject) => {
      this.pool.signUp(email.trim().toLowerCase(), password, attrs, [], (err, result) => {
        if (err) return reject(friendly(err));
        resolve({ needsConfirmation: !result?.userConfirmed, session: null });
      });
    });
  }

  confirmSignUp(email: string, code: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.user(email).confirmRegistration(code.trim(), true, (err) =>
        err ? reject(friendly(err)) : resolve(),
      );
    });
  }

  resendCode(email: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.user(email).resendConfirmationCode((err) => (err ? reject(friendly(err)) : resolve()));
    });
  }

  forgotPassword(email: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.user(email).forgotPassword({
        onSuccess: () => resolve(),
        onFailure: (err) => reject(friendly(err)),
        inputVerificationCode: () => resolve(),
      });
    });
  }

  confirmForgotPassword(email: string, code: string, newPassword: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.user(email).confirmPassword(code.trim(), newPassword, {
        onSuccess: () => resolve(),
        onFailure: (err) => reject(friendly(err)),
      });
    });
  }

  async signOut(): Promise<void> {
    this.pool.getCurrentUser()?.signOut();
  }
}
