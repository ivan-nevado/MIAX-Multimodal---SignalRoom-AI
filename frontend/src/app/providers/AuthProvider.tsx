import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { createAuthService, setAuthService, type AuthService, type Session } from '@/lib/auth';
import { AuthContext, type AuthState } from '@/hooks/useAuth';

export function AuthProvider({
  children,
  service: injected,
}: {
  children: ReactNode;
  service?: AuthService;
}) {
  const [service, setService] = useState<AuthService | null>(injected ?? null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const svc = injected ?? (await createAuthService());
      setAuthService(svc);
      const existing = await svc.getSession();
      if (!cancelled) {
        setService(svc);
        setSession(existing);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [injected]);

  const signOut = useCallback(async () => {
    await service?.signOut();
    setSession(null);
    queryClient.clear();
  }, [service, queryClient]);

  useEffect(() => {
    const onUnauthorized = (e: Event) => {
      const detail = (e as CustomEvent<string | undefined>).detail;
      if (detail) setNotice(detail);
      void signOut();
    };
    window.addEventListener('signalroom:unauthorized', onUnauthorized);
    return () => window.removeEventListener('signalroom:unauthorized', onUnauthorized);
  }, [signOut]);

  const value = useMemo<AuthState>(
    () => ({
      service,
      session,
      loading,
      notice,
      signIn: async (email, password) => {
        if (!service) throw new Error('Auth not ready');
        setNotice(null);
        const s = await service.signIn(email, password);
        setSession(s);
        return s;
      },
      signUp: async (email, password) => {
        if (!service) throw new Error('Auth not ready');
        const result = await service.signUp(email, password);
        if (result.session) setSession(result.session);
        return result;
      },
      signOut,
    }),
    [service, session, loading, notice, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
