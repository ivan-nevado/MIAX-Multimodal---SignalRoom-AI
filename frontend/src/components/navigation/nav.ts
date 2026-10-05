import { BookOpen, FlaskConical, House, ListChecks, Search, Settings, type LucideIcon } from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/app/dashboard', label: 'Dashboard', icon: House },
  { to: '/app/research', label: 'Research', icon: FlaskConical },
  { to: '/app/search', label: 'Search', icon: Search },
  { to: '/app/watchlist', label: 'Watchlist', icon: ListChecks },
  { to: '/app/briefings', label: 'Briefings', icon: BookOpen },
  { to: '/app/settings', label: 'Settings', icon: Settings },
];

// Mobile bottom navigation (Home · Research · Watchlist · Briefing · Settings).
export const MOBILE_NAV: NavItem[] = NAV_ITEMS.filter((i) => i.label !== 'Search').map((i) =>
  i.label === 'Dashboard'
    ? { ...i, label: 'Home' }
    : i.label === 'Briefings'
      ? { ...i, label: 'Briefing' }
      : i,
);
