import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import {
  Clapperboard,
  FileText,
  Headphones,
  Image as ImageIcon,
  ImageUp,
  Newspaper,
  Search,
  Sparkles,
  X,
} from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { EmptyState, ErrorState, Spinner } from '@/components/ui/states';
import { useSemanticSearch } from '@/hooks/queries';
import { api } from '@/lib/api';
import { relativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import type { SearchHit, SearchModality, SearchResponse } from '@/types/api';

const FILTERS: { value: SearchModality; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'video', label: 'Video' },
  { value: 'audio', label: 'Calls' },
  { value: 'document', label: 'PDFs' },
  { value: 'image', label: 'Images' },
  { value: 'news', label: 'News' },
  { value: 'analysis', label: 'Analysis' },
];

const SUGGESTIONS = [
  'guidance for next quarter',
  'what did the CFO say about margins',
  'export restrictions',
  'data center revenue',
];

const ICONS: Record<SearchHit['modality'], ReactNode> = {
  video: <Clapperboard className="h-4 w-4" />,
  audio: <Headphones className="h-4 w-4" />,
  document: <FileText className="h-4 w-4" />,
  image: <ImageIcon className="h-4 w-4" />,
  news: <Newspaper className="h-4 w-4" />,
  summary: <Sparkles className="h-4 w-4" />,
  driver: <Sparkles className="h-4 w-4" />,
  claim: <Sparkles className="h-4 w-4" />,
};

function useDebounced<T>(value: T, ms = 350): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function Highlight({ text, query }: { text: string; query: string }) {
  const words = query
    .toLowerCase()
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (!words.length) return <>{text}</>;
  const parts = text.split(new RegExp(`(${words.join('|')})`, 'gi'));
  return (
    <>
      {parts.map((p, i) =>
        i % 2 === 1 ? (
          <mark key={i} className="rounded bg-primary/15 px-0.5 text-ink">
            {p}
          </mark>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  );
}

function HitCard({ hit, query }: { hit: SearchHit; query: string }) {
  return (
    <li>
      <Link
        to={`/app/investigation/${hit.investigation_id}`}
        className="block rounded-xl border border-line bg-surface p-4 transition-colors hover:border-line-strong"
      >
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 shrink-0 rounded-lg bg-elevated p-2 text-primary-soft" aria-hidden>
            {ICONS[hit.modality]}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="min-w-0 truncate text-sm font-medium text-ink">{hit.title}</p>
              {hit.location && <Badge>{hit.location}</Badge>}
            </div>
            <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-ink-2">
              <Highlight text={hit.snippet} query={query} />
            </p>
            <p className="mt-2 truncate text-xs text-ink-3">
              {hit.symbol ? `${hit.symbol} · ` : ''}
              {hit.question} · {relativeTime(hit.created_at)}
            </p>
          </div>
          <div className="hidden w-16 shrink-0 text-right sm:block" title="Similarity score">
            <p className="tabular text-xs text-ink-3">{Math.round(hit.score * 100)}%</p>
            <div className="mt-1 h-1.5 rounded-full bg-elevated">
              <div
                className="h-1.5 rounded-full bg-primary"
                style={{ width: `${Math.round(hit.score * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </Link>
    </li>
  );
}

function Results({ data, query }: { data: SearchResponse; query: string }) {
  if (data.indexed_investigations === 0)
    return (
      <EmptyState
        icon={<Search className="h-5 w-5" />}
        title="Nothing indexed yet"
        description="Completed investigations, with their PDFs, calls, videos and images, become searchable automatically."
        action={
          <Link to="/app/research">
            <Button size="sm">Start a research</Button>
          </Link>
        }
      />
    );
  if (data.hits.length === 0)
    return (
      <EmptyState
        icon={<Search className="h-5 w-5" />}
        title="No matching passages"
        description={`Searched ${data.indexed_investigations} investigation(s). Try other words or another filter.`}
      />
    );
  return (
    <ul className="space-y-3" aria-label="Search results">
      {data.hits.map((h, i) => (
        <HitCard key={`${h.investigation_id}-${i}`} hit={h} query={query} />
      ))}
    </ul>
  );
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [modality, setModality] = useState<SearchModality>('all');
  const [imageQuery, setImageQuery] = useState<{
    name: string;
    result?: SearchResponse;
    error?: string;
  } | null>(null);
  const [imageLoading, setImageLoading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const debounced = useDebounced(q);
  const textSearch = useSemanticSearch(imageQuery ? '' : debounced, modality);

  const searchImage = async (file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      setImageQuery({ name: file.name, error: 'Query image must be under 5 MB.' });
      return;
    }
    setImageQuery({ name: file.name });
    setImageLoading(true);
    try {
      const result = await api.searchByImage(file, modality);
      setImageQuery({ name: file.name, result });
    } catch (e) {
      setImageQuery({ name: file.name, error: e instanceof Error ? e.message : 'Image search failed.' });
    } finally {
      setImageLoading(false);
    }
  };

  const mode = imageQuery?.result?.mode ?? textSearch.data?.mode;

  return (
    <div>
      <PageHeader
        title="Search"
        subtitle="Multimodal semantic search across everything you researched: call and video transcripts, slides, PDFs, charts and news."
      />
      <Card>
        <CardBody className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative min-w-0 flex-1">
              <Search
                className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-ink-3"
                aria-hidden
              />
              <Input
                value={q}
                onChange={(e) => {
                  setImageQuery(null);
                  setQ(e.target.value);
                }}
                placeholder="e.g. what did management say about guidance?"
                aria-label="Search your research"
                className="pl-9"
                maxLength={300}
              />
            </div>
            <Button variant="secondary" onClick={() => fileInput.current?.click()} loading={imageLoading}>
              <ImageUp className="h-4 w-4" aria-hidden /> Search by image
            </Button>
            <input
              ref={fileInput}
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              className="hidden"
              aria-label="Query image"
              onChange={(e) => {
                const f = e.target.files?.[0];
                e.target.value = '';
                if (f) void searchImage(f);
              }}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by modality">
            {FILTERS.map((f) => (
              <button
                key={f.value}
                type="button"
                onClick={() => setModality(f.value)}
                aria-pressed={modality === f.value}
                className={cn(
                  'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                  modality === f.value
                    ? 'border-primary bg-primary/10 text-primary-soft'
                    : 'border-line text-ink-2 hover:border-line-strong hover:text-ink',
                )}
              >
                {f.label}
              </button>
            ))}
            {mode && (
              <span className="ml-auto text-xs text-ink-3">
                {mode === 'keyword'
                  ? 'Keyword match (embeddings unavailable)'
                  : 'Semantic match · Gemini Embedding 2'}
              </span>
            )}
          </div>
        </CardBody>
      </Card>

      <div className="mt-6">
        {imageQuery ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-ink-2">
              <ImageIcon className="h-4 w-4 text-primary-soft" aria-hidden /> Results similar to{' '}
              <span className="font-medium text-ink">{imageQuery.name}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setImageQuery(null)}
                aria-label="Clear image query"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            {imageLoading && <Spinner label="Embedding image" />}
            {imageQuery.error && <ErrorState title="Image search failed" message={imageQuery.error} />}
            {imageQuery.result && <Results data={imageQuery.result} query="" />}
          </div>
        ) : debounced.trim().length < 2 ? (
          <div>
            <p className="text-xs font-semibold tracking-[0.16em] text-ink-3 uppercase">Try</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setQ(s)}
                  className="rounded-lg border border-line bg-elevated/60 px-3 py-1.5 text-sm text-ink-2 hover:border-line-strong hover:text-ink"
                >
                  {s}
                </button>
              ))}
            </div>
            <p className="mt-4 max-w-2xl text-sm text-ink-3">
              Queries are matched by meaning, not just words: text passages and uploaded images share one
              embedding space, so a question can find a chart and a chart can find the call where it was
              discussed.
            </p>
          </div>
        ) : textSearch.isLoading ? (
          <Spinner label="Searching" />
        ) : textSearch.isError ? (
          <ErrorState title="Search failed" message={(textSearch.error as Error).message} />
        ) : textSearch.data ? (
          <Results data={textSearch.data} query={debounced} />
        ) : null}
      </div>
    </div>
  );
}
