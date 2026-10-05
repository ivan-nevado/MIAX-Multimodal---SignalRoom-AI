import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/ui/misc';
import { useAuth } from '@/hooks/useAuth';

export const FOOTER_LINKS: { title: string; links: { label: string; to: string }[] }[] = [
  {
    title: 'Product',
    links: [
      { label: 'Research', to: '/app/research' },
      { label: 'Daily briefing', to: '/#briefing' },
      { label: 'Pricing', to: '/#pricing' },
    ],
  },
  {
    title: 'Research',
    links: [
      { label: 'Methodology', to: '/methodology' },
      { label: 'Data sources', to: '/methodology#data-sources' },
      { label: 'Evidence scoring', to: '/methodology#evidence-scoring' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', to: '/about' },
      { label: 'Privacy', to: '/privacy' },
      { label: 'Terms', to: '/terms' },
    ],
  },
];

export function PublicHeader() {
  const { session } = useAuth();
  return (
    <header className="sticky top-0 z-30 border-b border-line/60 bg-background/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Logo />
        <nav aria-label="Site" className="flex items-center gap-2">
          <Link to="/#how" className="hidden px-3 text-sm text-ink-3 hover:text-ink sm:inline">
            How it works
          </Link>
          <Link to="/#pricing" className="hidden px-3 text-sm text-ink-3 hover:text-ink sm:inline">
            Pricing
          </Link>
          {session ? (
            <Link to="/app/dashboard">
              <Button size="sm" tabIndex={-1}>
                Open SignalRoom
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/login">
                <Button size="sm" variant="ghost" tabIndex={-1}>
                  Sign in
                </Button>
              </Link>
              <Link to="/signup">
                <Button size="sm" tabIndex={-1}>
                  Start researching
                </Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-line px-4 py-12 sm:px-6">
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <p className="font-display text-lg font-semibold text-ink">SignalRoom</p>
          <p className="mt-2 max-w-sm text-xs leading-relaxed text-ink-3">
            SignalRoom is an educational research prototype and does not provide personalized investment
            advice or execute trades.
          </p>
        </div>
        {FOOTER_LINKS.map((group) => (
          <div key={group.title}>
            <p className="text-xs font-semibold tracking-wider text-ink-2 uppercase">{group.title}</p>
            <ul className="mt-3 space-y-2 text-sm text-ink-3">
              {group.links.map((l) => (
                <li key={l.label}>
                  <Link to={l.to} className="hover:text-ink">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="mx-auto mt-10 max-w-6xl text-[11px] leading-relaxed text-ink-3">
        Educational disclaimer: SignalRoom is an educational financial research prototype. Its analysis is
        generated from available data and AI models and may contain errors. It does not provide personalized
        investment advice, execute trades, or guarantee the accuracy or completeness of market information.
        Market data may be delayed.
      </p>
    </footer>
  );
}

/** Layout for public content pages (About, Privacy, Terms, Methodology). */
export function PublicLayout({
  title,
  intro,
  children,
}: {
  title: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-background">
      <PublicHeader />
      <main className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
        <h1 className="font-display text-3xl font-semibold text-ink sm:text-4xl">{title}</h1>
        {intro && <p className="mt-4 text-[15px] leading-relaxed text-ink-2">{intro}</p>}
        <div className="prose-signalroom mt-10 space-y-10">{children}</div>
      </main>
      <PublicFooter />
    </div>
  );
}

export function Section({ id, title, children }: { id?: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="font-display text-xl font-semibold text-ink">{title}</h2>
      <div className="mt-3 space-y-3 text-sm leading-relaxed text-ink-2">{children}</div>
    </section>
  );
}
