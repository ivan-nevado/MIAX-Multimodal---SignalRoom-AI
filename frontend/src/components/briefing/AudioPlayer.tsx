import { useEffect, useRef, useState } from 'react';
import { AudioLines, LoaderCircle, Pause, Play } from 'lucide-react';
import { formatDuration } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import type { MediaStatus } from '@/types/api';

/** Briefing audio player: "Preparing briefing audio..." → "▶ 4:12". */
export function AudioPlayer({
  src,
  status = 'ready',
  title = 'Listen to briefing',
  durationHint,
  className,
}: {
  src: string | null;
  status?: MediaStatus;
  title?: string;
  durationHint?: number | null;
  className?: string;
}) {
  const audio = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(durationHint ?? 0);

  useEffect(() => {
    setPlaying(false);
    setTime(0);
  }, [src]);

  if (status === 'pending') {
    return (
      <div
        className={cn(
          'flex items-center gap-3 rounded-xl border border-line bg-elevated/50 px-4 py-3 text-sm text-ink-2',
          className,
        )}
        role="status"
      >
        <LoaderCircle className="h-4 w-4 animate-spin text-primary-soft" aria-hidden />
        Preparing briefing audio…
      </div>
    );
  }
  if (status === 'failed') {
    return (
      <div className={cn('rounded-xl border border-line px-4 py-3 text-sm text-ink-3', className)}>
        Audio could not be generated this time.
      </div>
    );
  }
  if (!src) return null;

  const toggle = () => {
    const el = audio.current;
    if (!el) return;
    if (el.paused) void el.play();
    else el.pause();
  };

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-xl border border-line bg-elevated/50 px-3 py-2.5',
        className,
      )}
    >
      <audio
        ref={audio}
        src={src}
        preload="metadata"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) =>
          Number.isFinite(e.currentTarget.duration) && setDuration(e.currentTarget.duration)
        }
      />
      <button
        type="button"
        onClick={toggle}
        aria-label={playing ? 'Pause briefing' : 'Play briefing'}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/30"
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="ml-0.5 h-4 w-4" />}
      </button>
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 text-xs font-medium text-ink-2">
          <AudioLines className="h-3.5 w-3.5 text-primary-soft" aria-hidden /> {title}
        </p>
        <input
          type="range"
          min={0}
          max={duration || 1}
          step={0.1}
          value={time}
          aria-label="Seek"
          onChange={(e) => {
            if (audio.current) audio.current.currentTime = Number(e.target.value);
          }}
          className="mt-1 h-1 w-full cursor-pointer accent-[var(--color-primary)]"
        />
      </div>
      <span className="tabular shrink-0 text-xs text-ink-3">
        {playing || time > 0 ? `${formatDuration(time)} / ` : '▶ '}
        {formatDuration(duration)}
      </span>
    </div>
  );
}
