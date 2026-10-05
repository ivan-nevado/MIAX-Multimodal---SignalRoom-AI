import { useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { CircleHelp, LogOut, Menu, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog } from '@/components/ui/dialog';
import { Logo } from '@/components/ui/misc';
import { MOBILE_NAV, NAV_ITEMS } from '@/components/navigation/nav';
import { useAuth } from '@/hooks/useAuth';
import { config } from '@/lib/config';
import { cn } from '@/lib/utils';

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav aria-label="Main" className="space-y-1">
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              isActive ? 'bg-elevated text-ink' : 'text-ink-3 hover:bg-elevated/60 hover:text-ink',
            )
          }
        >
          <Icon className="h-4 w-4" aria-hidden />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function LightDisclaimer() {
  return (
    <p className="text-[11px] leading-relaxed text-ink-3">
      Educational research prototype · Not investment advice · Market data may be delayed.
    </p>
  );
}

export function AppShell() {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();
  const [drawer, setDrawer] = useState(false);

  const logout = async () => {
    await signOut();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-line bg-surface/60 px-4 py-5 backdrop-blur lg:flex">
        <Logo to="/app/dashboard" className="px-2" />
        <div className="mt-8 flex-1">
          <NavList />
        </div>
        <div className="space-y-3 border-t border-line pt-4">
          <Link
            to="/methodology"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink-3 hover:text-ink"
          >
            <CircleHelp className="h-4 w-4" aria-hidden /> Help
          </Link>
          <div className="px-3">
            <p className="truncate text-xs text-ink-2">{session?.email}</p>
            <button
              onClick={logout}
              className="mt-2 inline-flex items-center gap-2 text-xs text-ink-3 hover:text-ink"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden /> Sign out
            </button>
          </div>
          <div className="px-3">
            <LightDisclaimer />
          </div>
        </div>
      </aside>

      {/* Mobile top bar + drawer */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-background/85 px-4 py-3 backdrop-blur lg:hidden">
        <Logo to="/app/dashboard" />
        <Button variant="ghost" size="icon" aria-label="Open menu" onClick={() => setDrawer(true)}>
          <Menu className="h-5 w-5" />
        </Button>
      </header>
      <Dialog open={drawer} onOpenChange={setDrawer} title="Menu" side="left">
        <NavList onNavigate={() => setDrawer(false)} />
        <div className="mt-6 border-t border-line pt-4">
          <p className="truncate text-xs text-ink-2">{session?.email}</p>
          <Button variant="ghost" size="sm" className="mt-2 -ml-3" onClick={logout}>
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </Button>
        </div>
      </Dialog>

      <main className="pb-24 lg:pb-10 lg:pl-60">
        {config.demoMode && (
          <div className="border-b border-primary/20 bg-primary/10 px-4 py-2 text-center text-xs text-primary-soft">
            <Sparkles className="mr-1.5 inline h-3.5 w-3.5" aria-hidden />
            Demo mode — replaying real SignalRoom runs recorded with live data. Connect the backend for live
            investigations.
          </div>
        )}
        <div className="mx-auto w-full max-w-[1320px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom navigation */}
      <nav
        aria-label="Mobile"
        className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-surface/95 backdrop-blur lg:hidden"
      >
        {MOBILE_NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn('flex flex-col items-center gap-1 py-2.5 text-[11px]', isActive ? 'text-ink' : 'text-ink-3')
            }
          >
            <Icon className="h-5 w-5" aria-hidden />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
