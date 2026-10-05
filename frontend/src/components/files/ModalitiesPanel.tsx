import {
  Check,
  Clapperboard,
  FileText,
  Headphones,
  Image as ImageIcon,
  LineChart,
  Mic,
  Newspaper,
  Search,
  Type,
} from 'lucide-react';

const MODALITIES = [
  { label: 'Text', icon: Type },
  { label: 'Market data', icon: LineChart },
  { label: 'News', icon: Newspaper },
  { label: 'PDF', icon: FileText },
  { label: 'Image', icon: ImageIcon },
  { label: 'Audio', icon: Headphones },
  { label: 'Video', icon: Clapperboard },
  { label: 'Voice', icon: Mic },
  { label: 'Semantic search', icon: Search },
];

/** "Research with" — makes the multimodal capabilities obvious without exposing the agent architecture. */
export function ModalitiesPanel() {
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold tracking-[0.16em] text-ink-3 uppercase">Research with</p>
      <ul className="mt-3 grid grid-cols-2 gap-2">
        {MODALITIES.map(({ label, icon: Icon }) => (
          <li key={label} className="flex items-center gap-2 text-sm text-ink-2">
            <Check className="h-3.5 w-3.5 text-positive" aria-hidden />
            <Icon className="h-3.5 w-3.5 text-ink-3" aria-hidden />
            {label}
          </li>
        ))}
      </ul>
      <p className="mt-4 text-xs leading-relaxed text-ink-3">
        Outputs: written brief, charts, evidence graph, risk radar, narrated audio, visual brief and email.
      </p>
    </div>
  );
}
