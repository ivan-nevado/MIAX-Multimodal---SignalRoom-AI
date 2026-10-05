import { useState, type FormEvent } from 'react';
import { LoaderCircle, MessageSquare, Send } from 'lucide-react';
import type { FollowUp, Source } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

const SUGGESTIONS = [
  'What would invalidate this explanation?',
  "Compare today's move with the last earnings report.",
  'Does this change the thesis?',
];

/** Follow-ups reuse the investigation context (minimal new work), not a generic chatbot. */
export function FollowUpPanel({
  followups,
  sources,
  onAsk,
  disabled,
  pending,
}: {
  followups: FollowUp[];
  sources: Source[];
  onAsk: (q: string) => void;
  disabled?: boolean;
  pending?: boolean;
}) {
  const [q, setQ] = useState('');
  const byId = new Map(sources.map((s) => [s.id, s]));
  const busy = pending || followups.some((f) => f.status === 'queued' || f.status === 'running');
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (q.trim().length < 3 || busy) return;
    onAsk(q.trim());
    setQ('');
  };
  return (
    <Card>
      <CardHeader
        icon={<MessageSquare className="h-4 w-4" />}
        title="Ask a follow-up"
        subtitle="Answers use this investigation's evidence; new data is fetched only if needed."
      />
      <CardBody className="space-y-4">
        {followups.map((f) => (
          <div key={f.followup_id} className="space-y-2">
            <p className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-primary/15 px-3.5 py-2 text-sm text-ink">
              {f.question}
            </p>
            {f.status === 'completed' ? (
              <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-line bg-elevated/50 px-3.5 py-2.5 text-sm leading-relaxed text-ink-2">
                {f.answer}
                {f.evidence_ids.length > 0 && (
                  <p className="mt-2 text-xs text-ink-3">
                    Evidence: {f.evidence_ids.map((id) => byId.get(id)?.publisher ?? id).join(' · ')}
                  </p>
                )}
                {f.agents_run.length > 0 && (
                  <p className="mt-1 text-xs text-ink-3">Agents re-run: {f.agents_run.join(', ')}</p>
                )}
              </div>
            ) : (
              <p className="flex items-center gap-2 text-sm text-ink-3">
                <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden /> Reviewing the evidence…
              </p>
            )}
          </div>
        ))}
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              type="button"
              disabled={disabled || busy}
              onClick={() => setQ(s)}
              className="rounded-full border border-line px-3 py-1 text-xs text-ink-2 hover:border-line-strong hover:text-ink disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="flex gap-2">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="What would invalidate this explanation?"
            aria-label="Follow-up question"
            disabled={disabled}
          />
          <Button
            type="submit"
            disabled={disabled || busy || q.trim().length < 3}
            aria-label="Send follow-up"
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
