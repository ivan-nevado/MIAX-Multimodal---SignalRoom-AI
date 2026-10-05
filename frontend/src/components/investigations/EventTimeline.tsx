import {
  Clapperboard,
  CalendarClock,
  FileText,
  Headphones,
  Image as ImageIcon,
  Landmark,
  LineChart,
  Newspaper,
} from 'lucide-react';
import type { TimelineEvent } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { formatDate, titleCase } from '@/lib/formatting';

const ORIGIN_ICON = {
  news: Newspaper,
  market: LineChart,
  filing: Landmark,
  document: FileText,
  audio: Headphones,
  video: Clapperboard,
  image: ImageIcon,
};

export function EventTimeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) return <p className="text-sm text-ink-3">No datable events were found.</p>;
  return (
    <ol className="relative space-y-4 border-l border-line pl-5" aria-label="Event timeline">
      {events.map((e) => {
        const Icon = ORIGIN_ICON[e.origin] ?? CalendarClock;
        return (
          <li key={e.id} className="relative">
            <span className="absolute top-0.5 -left-[29px] flex h-[18px] w-[18px] items-center justify-center rounded-full border border-line bg-elevated">
              <Icon className="h-2.5 w-2.5 text-primary-soft" aria-hidden />
            </span>
            <p className="tabular text-xs text-ink-3">{formatDate(e.timestamp, e.timestamp.length > 10)}</p>
            <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
              {e.title}
              <Badge>{titleCase(e.event_type)}</Badge>
            </p>
            {e.description && <p className="mt-0.5 text-xs leading-relaxed text-ink-3">{e.description}</p>}
          </li>
        );
      })}
    </ol>
  );
}
