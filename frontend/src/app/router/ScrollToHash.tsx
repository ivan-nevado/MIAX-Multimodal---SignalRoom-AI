import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/** Scroll to #anchors on navigation (also for lazily rendered pages); otherwise scroll to top. */
export function ScrollToHash() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) {
      window.scrollTo({ top: 0 });
      return;
    }
    let tries = 0;
    const id = decodeURIComponent(hash.slice(1));
    const timer = setInterval(() => {
      const el = document.getElementById(id);
      if (el || ++tries > 20) {
        clearInterval(timer);
        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
    return () => clearInterval(timer);
  }, [pathname, hash]);
  return null;
}
