import { useState, type FormEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { useAuth } from '@/hooks/useAuth';
import { passwordProblem } from '@/lib/auth/password';

export default function SignupPage() {
  const { signUp, signIn, session, service } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'form' | 'verify'>('form');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const authConfig = useQuery({
    queryKey: ['auth-config'],
    queryFn: api.authConfig,
    staleTime: Infinity,
    retry: false,
  });

  if (session) return <Navigate to="/app/dashboard" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const problem = service?.mode === 'demo' ? null : passwordProblem(password);
    if (problem) return setError(problem);
    setLoading(true);
    try {
      const result = await signUp(email, password);
      if (result.needsConfirmation) {
        setStep('verify');
        setInfo(`We sent a verification code to ${email}.`);
      } else {
        navigate('/app/dashboard');
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await service?.confirmSignUp(email, code);
      await signIn(email, password);
      navigate('/app/dashboard');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title={step === 'form' ? 'Create your research room' : 'Verify your email'}
      subtitle={step === 'form' ? 'Your AI financial research team, ready in seconds.' : (info ?? undefined)}
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="text-primary-soft hover:text-ink">
            Sign in
          </Link>
        </>
      }
    >
      {step === 'form' ? (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {authConfig.data?.invite_only && (
            <p className="rounded-lg border border-primary/30 bg-primary/10 p-3 text-xs text-ink-2">
              Invite-only demo: only emails added by the SignalRoom team can create an account.
            </p>
          )}
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
          <Field
            label="Password"
            htmlFor="password"
            hint="At least 8 characters with upper, lower case letters and a number."
          >
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
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
            Create account
          </Button>
        </form>
      ) : (
        <form onSubmit={verify} className="space-y-4">
          <Field label="Verification code" htmlFor="code">
            <Input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </Field>
          {error && (
            <p role="alert" className="text-sm text-negative">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={loading}>
            Verify and continue
          </Button>
          <button
            type="button"
            className="w-full text-xs text-ink-3 hover:text-ink"
            onClick={() => void service?.resendCode(email).then(() => setInfo('A new code is on its way.'))}
          >
            Resend code
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
