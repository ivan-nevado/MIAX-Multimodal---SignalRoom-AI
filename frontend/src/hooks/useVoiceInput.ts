import { useCallback, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { blobToWav } from '@/lib/audio/wav';
import type { VoiceCommandResult } from '@/types/api';

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error';

/** Push-to-talk voice questions: MediaRecorder → WAV (16 kHz) → /voice/transcribe. */
export function useVoiceInput(onResult: (r: VoiceCommandResult) => void) {
  const [state, setState] = useState<VoiceState>('idle');
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const supported =
    typeof window !== 'undefined' && typeof MediaRecorder !== 'undefined' && Boolean(navigator.mediaDevices);

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunks.current = [];
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setState('transcribing');
        try {
          const wav = await blobToWav(new Blob(chunks.current, { type: rec.mimeType }));
          onResult(await api.transcribeVoice(wav));
          setState('idle');
        } catch (err) {
          setError((err as Error).message || 'Could not transcribe your question.');
          setState('error');
        }
      };
      recorder.current = rec;
      rec.start();
      setState('recording');
      setTimeout(() => rec.state === 'recording' && rec.stop(), 15_000); // max 15 s
    } catch {
      setError('Microphone access was denied.');
      setState('error');
    }
  }, [onResult]);

  const stop = useCallback(() => {
    if (recorder.current?.state === 'recording') recorder.current.stop();
  }, []);

  return { state, error, supported, start, stop };
}
