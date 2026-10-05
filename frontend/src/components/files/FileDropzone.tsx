import { useRef, useState, type DragEvent } from 'react';
import {
  CircleCheck,
  CircleX,
  FileText,
  Headphones,
  Image as ImageIcon,
  LoaderCircle,
  Clapperboard,
  Upload,
  X,
} from 'lucide-react';
import type { UploadKind } from '@/lib/api';
import { cn } from '@/lib/utils';

export interface PendingFile {
  id: string;
  file: File;
  kind: UploadKind;
  progress: number;
  status: 'uploading' | 'uploaded' | 'error';
  uploadId?: string;
  error?: string;
}

const ACCEPT: Record<UploadKind, { exts: string[]; maxMb: number; icon: typeof FileText; label: string }> = {
  document: { exts: ['.pdf'], maxMb: 25, icon: FileText, label: 'PDF' },
  image: { exts: ['.png', '.jpg', '.jpeg', '.webp'], maxMb: 10, icon: ImageIcon, label: 'Image' },
  audio: { exts: ['.mp3', '.wav', '.m4a', '.ogg', '.flac'], maxMb: 50, icon: Headphones, label: 'Audio' },
  video: { exts: ['.mp4', '.webm', '.mov'], maxMb: 40, icon: Clapperboard, label: 'Video' },
};

export function kindForFile(file: File): UploadKind | null {
  const name = file.name.toLowerCase();
  for (const [kind, cfg] of Object.entries(ACCEPT) as [UploadKind, (typeof ACCEPT)[UploadKind]][]) {
    if (cfg.exts.some((e) => name.endsWith(e))) return kind;
  }
  return null;
}

export function validateFile(file: File): string | null {
  const kind = kindForFile(file);
  if (!kind) return 'Unsupported file type. Use PDF, PNG/JPG/WebP, MP3/WAV/M4A/OGG/FLAC or MP4/WebM/MOV.';
  if (file.size > ACCEPT[kind].maxMb * 1024 * 1024)
    return `${ACCEPT[kind].label} files must be under ${ACCEPT[kind].maxMb} MB.`;
  return null;
}

/** Drag & drop + "+ Add PDF / image / audio / video". Files go straight to private storage via presigned URLs. */
export function FileDropzone({
  files,
  onAdd,
  onRemove,
}: {
  files: PendingFile[];
  onAdd: (files: File[]) => void;
  onRemove: (id: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [accept, setAccept] = useState('');

  const open = (kind?: UploadKind) => {
    setAccept(
      kind
        ? ACCEPT[kind].exts.join(',')
        : Object.values(ACCEPT)
            .flatMap((a) => a.exts)
            .join(','),
    );
    setTimeout(() => input.current?.click(), 0);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    onAdd(Array.from(e.dataTransfer.files));
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
        className={cn(
          'rounded-xl border border-dashed p-4 transition-colors',
          drag ? 'border-primary bg-primary/5' : 'border-line',
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          {(Object.keys(ACCEPT) as UploadKind[]).map((kind) => {
            const Icon = ACCEPT[kind].icon;
            return (
              <button
                key={kind}
                type="button"
                onClick={() => open(kind)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-elevated/60 px-3 py-1.5 text-xs font-medium text-ink-2 hover:border-line-strong hover:text-ink"
              >
                <Icon className="h-3.5 w-3.5" aria-hidden /> Add{' '}
                {ACCEPT[kind].label === 'PDF' ? 'PDF' : ACCEPT[kind].label.toLowerCase()}
              </button>
            );
          })}
          <span className="ml-auto hidden items-center gap-1.5 text-xs text-ink-3 sm:inline-flex">
            <Upload className="h-3.5 w-3.5" aria-hidden /> or drop files here
          </span>
        </div>
        <input
          ref={input}
          type="file"
          multiple
          accept={accept}
          className="hidden"
          aria-label="Upload files"
          onChange={(e) => {
            onAdd(Array.from(e.target.files ?? []));
            e.target.value = '';
          }}
        />
      </div>
      {files.length > 0 && (
        <ul className="mt-3 space-y-2" aria-label="Attached files">
          {files.map((f) => {
            const Icon = ACCEPT[f.kind].icon;
            return (
              <li
                key={f.id}
                className="flex items-center gap-3 rounded-lg border border-line bg-surface px-3 py-2 text-sm"
              >
                <Icon className="h-4 w-4 shrink-0 text-primary-soft" aria-hidden />
                <span className="min-w-0 flex-1 truncate text-ink">{f.file.name}</span>
                {f.status === 'uploading' && (
                  <span className="tabular flex items-center gap-1 text-xs text-ink-3">
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden /> {f.progress}%
                  </span>
                )}
                {f.status === 'uploaded' && (
                  <CircleCheck className="h-4 w-4 text-positive" aria-label="Uploaded" />
                )}
                {f.status === 'error' && (
                  <span className="flex items-center gap-1 text-xs text-negative">
                    <CircleX className="h-3.5 w-3.5" aria-hidden /> {f.error}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => onRemove(f.id)}
                  aria-label={`Remove ${f.file.name}`}
                  className="text-ink-3 hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
