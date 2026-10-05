import { Link } from 'react-router-dom';
import { Logo } from '@/components/ui/misc';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <Logo />
      <h1 className="font-display text-3xl font-semibold">No signal here.</h1>
      <p className="text-sm text-ink-3">The page you are looking for does not exist.</p>
      <Link to="/" className="text-sm text-primary-soft hover:text-ink">
        Back to SignalRoom
      </Link>
    </div>
  );
}
