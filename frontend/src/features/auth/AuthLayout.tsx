import type { ReactNode } from 'react';
import { Logo } from '@/components/ui/misc';
import { useAuth } from '@/hooks/useAuth';

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { service } = useAuth();
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[680px] -translate-x-1/2 rounded-full bg-primary/15 blur-3xl"
        aria-hidden
      />
      <div className="relative w-full max-w-sm">
        <div className="mb-8 flex justify-center">
          <Logo />
        </div>
        <div className="card glow p-6">
          <h1 className="font-display text-xl font-semibold text-ink">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-ink-3">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
        {footer && <div className="mt-5 text-center text-sm text-ink-3">{footer}</div>}
        <p className="mt-6 text-center text-[11px] text-ink-3">
          {service?.mode === 'cognito' && 'Secured by Amazon Cognito · '}
          {service?.mode === 'local' && 'Local development sign-in · '}
          {service?.mode === 'demo' && 'Demo mode: any email works · '}
          Educational prototype — not investment advice.
        </p>
      </div>
    </div>
  );
}
