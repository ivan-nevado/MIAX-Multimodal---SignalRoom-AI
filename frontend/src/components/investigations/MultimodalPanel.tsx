import { useState } from 'react';
import { Clapperboard, FileText, Headphones, Image as ImageIcon, Quote } from 'lucide-react';
import type { InvestigationResult } from '@/types/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Spinner } from '@/components/ui/states';
import { useTranscript } from '@/hooks/queries';
import { titleCase } from '@/lib/formatting';

function TranscriptViewer({ investigationId, uploadId }: { investigationId: string; uploadId: string }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading } = useTranscript(investigationId, uploadId, open);
  return (
    <div className="mt-3">
      <Button size="sm" variant="secondary" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        {open ? 'Hide full transcript' : 'Show full transcript'}
      </Button>
      {open && (
        <div className="mt-3 max-h-96 space-y-3 overflow-y-auto rounded-xl border border-line bg-background p-4">
          {isLoading && <Spinner />}
          {data?.segments.map((s, i) => (
            <p key={i} className="text-sm">
              <span className="tabular mr-2 text-xs text-ink-3">{s.start ?? ''}</span>
              <span className="font-medium text-primary-soft">{s.speaker}:</span>{' '}
              <span className="text-ink-2">{s.text}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/** Uploaded PDFs, images, audio and video — what each specialised model extracted. */
export function MultimodalPanel({
  result,
  investigationId,
}: {
  result: InvestigationResult;
  investigationId: string;
}) {
  return (
    <div className="space-y-5">
      {result.audio.map((a) => (
        <Card key={a.upload_id}>
          <CardHeader
            icon={<Headphones className="h-4 w-4" />}
            title={a.filename}
            subtitle={`Audio · ${a.language} · ${a.segment_count} segments · speakers: ${a.speakers.join(', ')}`}
          />
          <CardBody className="space-y-4">
            {a.analysis && (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="primary">Management tone: {a.analysis.management_tone}</Badge>
                </div>
                <p className="text-sm leading-relaxed text-ink-2">{a.analysis.summary}</p>
                <div className="grid gap-4 md:grid-cols-3">
                  {(
                    [
                      ['Key points', a.analysis.key_points],
                      ['Guidance', a.analysis.guidance],
                      ['Risks mentioned', a.analysis.risks],
                    ] as const
                  ).map(([label, items]) => (
                    <div key={label}>
                      <p className="text-xs font-semibold text-ink-3 uppercase">{label}</p>
                      <ul className="mt-2 space-y-1.5">
                        {items.map((k) => (
                          <li key={k} className="text-sm text-ink-2">
                            · {k}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                {a.analysis.notable_quotes.map((q) => (
                  <blockquote
                    key={q}
                    className="flex gap-2 border-l-2 border-accent pl-3 text-sm text-ink italic"
                  >
                    <Quote className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden /> {q}
                  </blockquote>
                ))}
                <p className="text-[11px] text-ink-3">
                  Quotes are verified verbatim against the transcript before display.
                </p>
              </>
            )}
            <div className="space-y-2 rounded-xl bg-background/60 p-3">
              {a.transcript_preview.slice(0, 4).map((s, i) => (
                <p key={i} className="text-sm text-ink-2">
                  <span className="font-medium text-ink">{s.speaker}:</span> {s.text}
                </p>
              ))}
            </div>
            <TranscriptViewer investigationId={investigationId} uploadId={a.upload_id} />
          </CardBody>
        </Card>
      ))}
      {(result.videos ?? []).map((v) => (
        <Card key={v.upload_id}>
          <CardHeader
            icon={<Clapperboard className="h-4 w-4" />}
            title={v.filename}
            subtitle={`Video · ${v.language} · ${v.segment_count} segments · ${v.slides.length} slides · speakers: ${v.speakers.join(', ')}`}
          />
          <CardBody className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="primary">Management tone: {v.management_tone}</Badge>
              <Badge>Speech + on-screen slides read together</Badge>
            </div>
            <p className="text-sm leading-relaxed text-ink-2">{v.summary}</p>
            {v.slides.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink-3 uppercase">Slides & charts shown</p>
                <ol className="mt-2 space-y-2">
                  {v.slides.map((s, i) => (
                    <li key={i} className="rounded-xl border border-line p-3">
                      <p className="text-sm font-medium text-ink">
                        <span className="tabular mr-2 rounded bg-elevated px-1.5 py-0.5 text-xs text-ink-3">
                          {s.timestamp ?? '--:--'}
                        </span>
                        {s.title}
                      </p>
                      {s.description && <p className="mt-1 text-sm text-ink-2">{s.description}</p>}
                      {s.figures.length > 0 && (
                        <dl className="mt-2 grid gap-x-4 gap-y-1 sm:grid-cols-2">
                          {s.figures.map((f, j) => (
                            <div
                              key={j}
                              className="flex min-w-0 justify-between gap-3 border-t border-line/60 pt-1 text-sm"
                            >
                              <dt className="truncate text-ink-3">{f.fact}</dt>
                              <dd className="tabular shrink-0 font-medium text-ink">{f.value}</dd>
                            </div>
                          ))}
                        </dl>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            )}
            <div className="grid gap-4 md:grid-cols-3">
              {(
                [
                  ['Key points', v.key_points],
                  ['Guidance', v.guidance],
                  ['Risks mentioned', v.risks],
                ] as const
              ).map(([label, items]) => (
                <div key={label}>
                  <p className="text-xs font-semibold text-ink-3 uppercase">{label}</p>
                  <ul className="mt-2 space-y-1.5">
                    {items.map((k) => (
                      <li key={k} className="text-sm text-ink-2">
                        · {k}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            {v.notable_quotes.map((q) => (
              <blockquote
                key={q}
                className="flex gap-2 border-l-2 border-accent pl-3 text-sm text-ink italic"
              >
                <Quote className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden /> {q}
              </blockquote>
            ))}
            <TranscriptViewer investigationId={investigationId} uploadId={v.upload_id} />
          </CardBody>
        </Card>
      ))}
      {result.documents.map((d) => (
        <Card key={d.upload_id}>
          <CardHeader
            icon={<FileText className="h-4 w-4" />}
            title={d.filename}
            subtitle={`PDF · ${d.page_count} pages · analysed pages ${d.pages_analyzed.join(', ')}`}
          />
          <CardBody className="space-y-4">
            <p className="text-sm leading-relaxed text-ink-2">{d.summary}</p>
            {d.key_facts.length > 0 && (
              <table className="w-full text-sm">
                <tbody>
                  {d.key_facts.map((f, i) => (
                    <tr key={i} className="border-t border-line/70">
                      <td className="py-2 pr-3 text-ink-2">{f.fact}</td>
                      <td className="tabular py-2 pr-3 text-right font-medium text-ink">{f.value}</td>
                      <td className="py-2 text-right text-xs text-ink-3">{f.page ? `p.${f.page}` : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {d.visual_pages.map((v) => (
              <div key={v.page} className="rounded-xl border border-line p-3">
                <p className="text-xs font-semibold text-ink-3">
                  Page {v.page} · {titleCase(v.content_type)} · read by the vision model
                </p>
                <p className="mt-1 text-sm text-ink-2">{v.description}</p>
              </div>
            ))}
          </CardBody>
        </Card>
      ))}
      {result.images.map((img) => (
        <Card key={img.upload_id}>
          <CardHeader
            icon={<ImageIcon className="h-4 w-4" />}
            title={img.filename}
            subtitle={`Image · ${titleCase(img.image_type)}`}
          />
          <CardBody className="space-y-3">
            <p className="text-sm leading-relaxed text-ink-2">{img.interpretation}</p>
            <div className="grid gap-4 md:grid-cols-3">
              {(
                [
                  ['Observations', img.observations],
                  ['Relevant levels', img.relevant_levels],
                  ['Uncertainties', img.uncertainties],
                ] as const
              ).map(([label, items]) => (
                <div key={label}>
                  <p className="text-xs font-semibold text-ink-3 uppercase">{label}</p>
                  <ul className="mt-2 space-y-1.5">
                    {items.map((k) => (
                      <li key={k} className="text-sm text-ink-2">
                        · {k}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
