import { useCallback, useState } from 'react';
import { api } from '@/lib/api';
import { kindForFile, validateFile, type PendingFile } from '@/components/files/FileDropzone';

/** Validates files client-side, uploads them directly to storage and tracks progress. */
export function useUploads(max = 6) {
  const [files, setFiles] = useState<PendingFile[]>([]);

  const update = (id: string, patch: Partial<PendingFile>) =>
    setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, ...patch } : f)));

  const add = useCallback(
    (incoming: File[]) => {
      for (const file of incoming.slice(0, max)) {
        const id = `${file.name}-${file.size}-${Math.random().toString(36).slice(2, 7)}`;
        const kind = kindForFile(file) ?? 'document';
        const error = validateFile(file);
        const entry: PendingFile = {
          id,
          file,
          kind,
          progress: 0,
          status: error ? 'error' : 'uploading',
          error: error ?? undefined,
        };
        setFiles((prev) => [...prev, entry].slice(-max));
        if (error) continue;
        api
          .uploadFile(file, kind, (pct) => update(id, { progress: pct }))
          .then((view) => update(id, { status: 'uploaded', uploadId: view.upload_id, progress: 100 }))
          .catch((err: Error) => update(id, { status: 'error', error: err.message }));
      }
    },
    [max],
  );

  const remove = useCallback((id: string) => setFiles((prev) => prev.filter((f) => f.id !== id)), []);
  const reset = useCallback(() => setFiles([]), []);
  const uploadIds = files
    .filter((f) => f.status === 'uploaded' && f.uploadId)
    .map((f) => f.uploadId as string);
  const uploading = files.some((f) => f.status === 'uploading');

  return { files, add, remove, reset, uploadIds, uploading };
}
