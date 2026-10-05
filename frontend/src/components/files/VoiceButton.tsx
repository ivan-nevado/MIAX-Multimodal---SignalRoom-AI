import { LoaderCircle, Mic, Square } from 'lucide-react';
import { useVoiceInput } from '@/hooks/useVoiceInput';
import type { VoiceCommandResult } from '@/types/api';
import { cn } from '@/lib/utils';

/** Ask by voice: speech → text (transcription model) → fills the question and resolves the asset. */
export function VoiceButton({ onResult }: { onResult: (r: VoiceCommandResult) => void }) {
  const { state, error, supported, start, stop } = useVoiceInput(onResult);
  if (!supported) return null;
  const recording = state === 'recording';
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={recording ? stop : start}
        disabled={state === 'transcribing'}
        aria-label={recording ? 'Stop recording' : 'Ask with your voice'}
        className={cn(
          'flex h-9 w-9 items-center justify-center rounded-full border transition-colors',
          recording
            ? 'animate-pulse border-accent bg-accent/15 text-accent'
            : 'border-line text-ink-2 hover:border-line-strong hover:text-ink',
        )}
      >
        {state === 'transcribing' ? (
          <LoaderCircle className="h-4 w-4 animate-spin" />
        ) : recording ? (
          <Square className="h-3.5 w-3.5" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </button>
      {recording && <span className="text-xs text-accent">Listening… tap to stop</span>}
      {state === 'transcribing' && <span className="text-xs text-ink-3">Transcribing…</span>}
      {error && <span className="text-xs text-negative">{error}</span>}
    </div>
  );
}
