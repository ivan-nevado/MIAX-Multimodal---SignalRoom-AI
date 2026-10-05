import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProtectedRoute } from '@/app/router/ProtectedRoute';
import { fakeAuth, renderWithProviders } from './utils';

describe('login guard', () => {
  it('redirects unauthenticated users from /app/* to /login', async () => {
    renderWithProviders(
      <ProtectedRoute>
        <p>Secret dashboard</p>
      </ProtectedRoute>,
      { route: '/app/dashboard', path: '/app/*', auth: fakeAuth(null) },
    );
    expect(await screen.findByText('Login screen')).toBeInTheDocument();
    expect(screen.queryByText('Secret dashboard')).not.toBeInTheDocument();
  });

  it('renders protected content for signed-in users', async () => {
    renderWithProviders(
      <ProtectedRoute>
        <p>Secret dashboard</p>
      </ProtectedRoute>,
      { route: '/app/dashboard', path: '/app/*' },
    );
    expect(await screen.findByText('Secret dashboard')).toBeInTheDocument();
  });
});
