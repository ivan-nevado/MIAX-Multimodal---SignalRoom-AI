import { config, resolveAuthMode } from '@/lib/config';
import { DemoAuthService } from './demo';
import { LocalAuthService } from './local';
import type { AuthService } from './types';

export * from './types';

let instance: AuthService | null = null;

export async function createAuthService(): Promise<AuthService> {
  const mode = resolveAuthMode();
  if (mode === 'demo') return new DemoAuthService();
  if (mode === 'cognito') {
    // Loaded lazily so local/demo bundles never pull the Cognito SDK.
    const { CognitoAuthService } = await import('./cognito');
    return new CognitoAuthService(config.cognito.userPoolId, config.cognito.clientId);
  }
  return new LocalAuthService();
}

export function setAuthService(service: AuthService): void {
  instance = service;
}

export function getAuthService(): AuthService | null {
  return instance;
}
