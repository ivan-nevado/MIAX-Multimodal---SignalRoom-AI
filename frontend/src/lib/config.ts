// Only safe, public configuration is exposed to the browser (never API keys).
const env = import.meta.env;

export const config = {
  apiBaseUrl: (env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '',
  appEnv: (env.VITE_APP_ENV as string | undefined) ?? 'local',
  demoMode: String(env.VITE_DEMO_MODE ?? 'false') === 'true',
  cognito: {
    region: (env.VITE_COGNITO_REGION as string | undefined) ?? '',
    userPoolId: (env.VITE_COGNITO_USER_POOL_ID as string | undefined) ?? '',
    clientId: (env.VITE_COGNITO_CLIENT_ID as string | undefined) ?? '',
  },
};

export type AuthMode = 'demo' | 'cognito' | 'local';

export function resolveAuthMode(): AuthMode {
  if (config.demoMode) return 'demo';
  if (config.cognito.userPoolId && config.cognito.clientId) return 'cognito';
  return 'local';
}
