import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Headphones, Sparkles, X } from 'lucide-react';
import type { AssetMatch } from '@/types/api';
import { FileDropzone } from '@/components/files/FileDropzone';
import { VoiceButton } from '@/components/files/VoiceButton';
import { AssetSearch } from '@/components/watchlist/AssetSearch';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { useCreateInvestigation } from '@/hooks/queries';
import { useUploads } from '@/hooks/useUploads';

const EXAMPLES = [
  'Why is Tesla down today?',
  "Compare today's move with the latest earnings report.",
  'Does this earnings report change the investment thesis?',
  'Analyze this chart.',
  'Summarize this earnings call and identify the most important risks.',
];

/** Premium research composer — "What do you want to understand?" */
export function ResearchComposer({ initialAsset }: { initialAsset?: AssetMatch | null }) {
  const navigate = useNavigate();
  const [question, setQuestion] = useState('');
  const [asset, setAsset] = useState<AssetMatch | null>(initialAsset ?? null);
  const [audio, setAudio] = useState(true);
  const uploads = useUploads();
  const create = useCreateInvestigation();
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (question.trim().length < 3) return setError('Tell SignalRoom what you want to understand.');
    if (!asset && uploads.uploadIds.length === 0 && !/[A-Za-z]{3,}/.test(question))
      return setError('Pick an asset or attach a file.');
    try {
      const res = await create.mutateAsync({
        asset: asset?.symbol ?? null,
        question: question.trim(),
        upload_ids: uploads.uploadIds,
        generate_audio: audio,
      });
      navigate(`/app/investigation/${res.investigation_id}`);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form onSubmit={submit} className="card glow p-5 sm:p-6" aria-label="New investigation">
      <label htmlFor="question" className="font-display text-xl font-semibold text-ink">
        What do you want to understand?
      </label>
      <div className="relative mt-4">
        <Textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Why did NVIDIA fall today?"
          className="min-h-28 pr-14 text-base"
          maxLength={600}
        />
        <div className="absolute right-3 bottom-3">
          <VoiceButton
            onResult={(r) => {
              setQuestion(r.text);
              if (r.resolved_symbol && !asset)
                setAsset({
                  symbol: r.resolved_symbol,
                  name: r.resolved_name ?? r.resolved_symbol,
                  asset_type: 'equity',
                  exchange: null,
                  source: 'alias',
                });
            }}
          />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setQuestion(ex)}
            className="rounded-full border border-line px-3 py-1 text-xs text-ink-3 hover:border-line-strong hover:text-ink"
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div>
          <p className="mb-1.5 text-xs font-medium text-ink-2">Asset</p>
          {asset ? (
            <div className="flex h-10 items-center justify-between rounded-lg border border-primary/40 bg-primary/10 px-3">
              <span className="text-sm text-ink">
                {asset.name} <Badge tone="primary">{asset.symbol}</Badge>
              </span>
              <button
                type="button"
                onClick={() => setAsset(null)}
                aria-label="Clear asset"
                className="text-ink-3 hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <AssetSearch onSelect={setAsset} placeholder="NVIDIA, Bitcoin, S&P 500, EUR/USD…" />
          )}
        </div>
        <div className="flex items-end">
          <label
            htmlFor="audio-toggle"
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-line px-3 py-2"
          >
            <span className="flex items-center gap-2 text-sm text-ink-2">
              <Headphones className="h-4 w-4 text-primary-soft" aria-hidden /> Narrated audio briefing
            </span>
            <Switch
              id="audio-toggle"
              checked={audio}
              onCheckedChange={setAudio}
              label="Generate narrated audio briefing"
            />
          </label>
        </div>
      </div>

      <div className="mt-4">
        <FileDropzone files={uploads.files} onAdd={uploads.add} onRemove={uploads.remove} />
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-negative">
          {error}
        </p>
      )}
      <div className="mt-5 flex flex-col-reverse items-stretch justify-between gap-3 sm:flex-row sm:items-center">
        <p className="text-xs text-ink-3">The orchestrator only runs the agents your question needs.</p>
        <Button
          type="submit"
          variant="gradient"
          size="lg"
          loading={create.isPending}
          disabled={uploads.uploading}
        >
          <Sparkles className="h-4 w-4" /> Investigate
        </Button>
      </div>
    </form>
  );
}
