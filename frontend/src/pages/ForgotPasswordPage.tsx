import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { AuthLayout } from '@/features/auth/AuthLayout';
import { useAuth } from '@/hooks/useAuth';
import { passwordProblem } from '@/lib/auth/password';

export default function ForgotPasswordPage() {
  const { service } = useAuth();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep] = useState<'request' | 'reset' | 'done'>('request');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setError(null);
    setLoading(true);
    try {
      await fn();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const request = (e: FormEvent) => {
    e.preventDefault();
    void run(async () => {
      await service?.forgotPassword(email);
      setStep('reset');
    });
  };

  const reset = (e: FormEvent) => {
    e.preventDefault();
    const problem = passwordProblem(password);
    if (problem) return setError(problem);
    void run(async () => {
      await service?.confirmForgotPassword(email, code, password);
      setStep('done');
    });
  };

  return (
    <AuthLayout
      title="Reset your password"
      subtitle={
        step === 'request'
          ? 'We will email you a verification code.'
          : step === 'reset'
            ? `Enter the code sent to ${email}.`
            : undefined
      }
      footer={
        <Link to="/login" className="text-primary-soft hover:text-ink">
          Back to sign in
        </Link>
      }
    >
      {step === 'request' && (
        <form onSubmit={request} className="space-y-4">
          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          {error && (
            <p role="alert" className="text-sm text-negative">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={loading}>
            Send code
          </Button>
        </form>
      )}
      {step === 'reset' && (
        <form onSubmit={reset} className="space-y-4">
          <Field label="Verification code" htmlFor="code">
            <Input id="code" inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
          <Field label="New password" htmlFor="password">
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
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
            Set new password
          </Button>
        </form>
      )}
      {step === 'done' && (
        <p className="text-sm text-ink-2">
          Your password was updated.{' '}
          <Link to="/login" className="text-primary-soft">
            Sign in
          </Link>
        </p>
      )}
    </AuthLayout>
  );
}
