import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import * as Tooltip from '@radix-ui/react-tooltip';
import { useState, type ReactNode } from 'react';
import { ApiError } from '@/lib/api';
import type { AuthService } from '@/lib/auth';
import { AuthProvider } from './AuthProvider';

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // Retry transient failures, never 4xx (auth/validation/not-found).
        retry: (count, error) =>
          !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
      },
    },
  });
}

export function AppProviders({
  children,
  authService,
  client,
}: {
  children: ReactNode;
  authService?: AuthService;
  client?: QueryClient;
}) {
  const [queryClient] = useState(() => client ?? makeQueryClient());
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider service={authService}>
        <Tooltip.Provider delayDuration={200}>{children}</Tooltip.Provider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
