import { useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { useAuth } from '@/hooks/useAuth';

export default function LoginPage() {
  const { signIn, session, service, notice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/app/dashboard';
  const [email, setEmail] = useState(service?.mode === 'demo' ? 'demo@signalroom.ai' : '');
  const [password, setPassword] = useState(service?.mode === 'demo' ? 'demo-password' : '');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (session) return <Navigate to={from} replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your research room."
      footer={
        <>
          New to SignalRoom?{' '}
          <Link to="/signup" className="text-primary-soft hover:text-ink">
            Create an account
          </Link>
        </>
      }
    >
      {notice && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-warning/30 bg-warning/5 p-3 text-sm text-ink-2"
        >
          {notice}
        </p>
      )}
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Email" htmlFor="email">
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Password" htmlFor="password">
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {error && (
          <p role="alert" className="text-sm text-negative">
            {error}
          </p>
        )}
        <Button type="submit" className="w-full" loading={loading}>
          Sign in
        </Button>
        <div className="text-center">
          <Link to="/forgot-password" className="text-xs text-ink-3 hover:text-ink">
            Forgot your password?
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
}
