import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Database, Info, ListChecks, ShieldCheck, User } from 'lucide-react';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Dialog } from '@/components/ui/dialog';
import { Field, Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/states';
import {
  useBriefingPreferences,
  useDeleteMyData,
  useHealth,
  useMe,
  useUpdateBriefingPreferences,
} from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import { formatDate } from '@/lib/formatting';
import type { BriefingPreferences } from '@/types/api';

export const FULL_DISCLAIMER =
  'SignalRoom is an educational financial research prototype. Its analysis is generated from available data and AI models and may contain errors. It does not provide personalized investment advice, execute trades, or guarantee the accuracy or completeness of market information.';

const TIMEZONES = [
  'Europe/Madrid',
  'Europe/London',
  'Europe/Berlin',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Asia/Tokyo',
  'Asia/Singapore',
  'UTC',
];

function BriefingSettings() {
  const { data, isLoading } = useBriefingPreferences();
  const update = useUpdateBriefingPreferences();
  const [draft, setDraft] = useState<BriefingPreferences | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => setDraft(data ?? null), [data]);
  if (isLoading || !draft) return <Skeleton className="h-48 w-full" />;
  const set = (patch: Partial<BriefingPreferences>) => {
    setSaved(false);
    setDraft({ ...draft, ...patch });
  };
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-4">
        <label htmlFor="briefing-enabled" className="text-sm text-ink">
          Daily briefing
          <span className="block text-xs text-ink-3">
            A personalised briefing is generated automatically every day.
          </span>
        </label>
        <Switch
          id="briefing-enabled"
          checked={draft.enabled}
          onCheckedChange={(v) => set({ enabled: v })}
          label="Daily briefing"
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Time" htmlFor="briefing-time">
          <Input
            id="briefing-time"
            type="time"
            value={draft.local_time}
            onChange={(e) => set({ local_time: e.target.value })}
            disabled={!draft.enabled}
          />
        </Field>
        <Field label="Timezone" htmlFor="briefing-tz">
          <select
            id="briefing-tz"
            value={draft.timezone}
            onChange={(e) => set({ timezone: e.target.value })}
            disabled={!draft.enabled}
            className="h-10 w-full rounded-lg border border-line bg-elevated/60 px-3 text-sm text-ink focus:border-primary focus:outline-none"
          >
            {[...new Set([draft.timezone, ...TIMEZONES])].map((tz) => (
              <option key={tz}>{tz}</option>
            ))}
          </select>
        </Field>
      </div>
      <div className="flex items-center justify-between gap-4">
        <label htmlFor="briefing-email" className="text-sm text-ink">
          Email me the briefing
          <span className="block text-xs text-ink-3">
            Sent through Amazon SES. Never sent unless you enable it.
          </span>
        </label>
        <Switch
          id="briefing-email"
          checked={draft.email_enabled}
          onCheckedChange={(v) => set({ email_enabled: v })}
          label="Email me the briefing"
        />
      </div>
      <div className="flex items-center justify-between gap-4">
        <label htmlFor="briefing-audio" className="text-sm text-ink">
          Audio briefing
          <span className="block text-xs text-ink-3">Voice: Professional (calm, analytical narration).</span>
        </label>
        <Switch
          id="briefing-audio"
          checked={draft.audio_enabled}
          onCheckedChange={(v) => set({ audio_enabled: v })}
          label="Audio briefing"
        />
      </div>
      <div className="flex items-center gap-3">
        <Button
          onClick={() => update.mutate(draft, { onSuccess: () => setSaved(true) })}
          loading={update.isPending}
        >
          Save briefing settings
        </Button>
        {saved && (
          <span role="status" className="text-sm text-positive">
            Saved ✓
          </span>
        )}
        {update.error && <span className="text-sm text-negative">{(update.error as Error).message}</span>}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const me = useMe();
  const health = useHealth();
  const { signOut } = useAuth();
  const deleteData = useDeleteMyData();
  const navigate = useNavigate();
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Account, notifications, daily briefing, watchlist and data & privacy."
      />
      <Card id="account">
        <CardHeader icon={<User className="h-4 w-4" />} title="Account" />
        <CardBody className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-ink">{me.data?.email ?? '—'}</p>
            <p className="text-xs text-ink-3">
              Member since {formatDate(me.data?.created_at)} · Sign-in:{' '}
              {me.data?.auth_mode === 'cognito' ? 'Amazon Cognito' : me.data?.auth_mode}
            </p>
          </div>
          <Button variant="secondary" onClick={() => void signOut().then(() => navigate('/login'))}>
            Sign out
          </Button>
        </CardBody>
      </Card>
      <Card id="briefing">
        <CardHeader icon={<Bell className="h-4 w-4" />} title="Notifications & daily briefing" />
        <CardBody>
          <BriefingSettings />
        </CardBody>
      </Card>
      <Card>
        <CardHeader icon={<ListChecks className="h-4 w-4" />} title="Watchlist" />
        <CardBody className="flex items-center justify-between gap-3">
          <p className="text-sm text-ink-2">Add, remove and reorder the assets SignalRoom monitors.</p>
          <Button variant="secondary" onClick={() => navigate('/app/watchlist')}>
            Manage watchlist
          </Button>
        </CardBody>
      </Card>
      <Card>
        <CardHeader icon={<ShieldCheck className="h-4 w-4" />} title="Data & privacy" />
        <CardBody className="space-y-3 text-sm text-ink-2">
          <p>
            Uploaded files are stored privately (encrypted S3, presigned URLs only) and are only sent to the
            AI providers needed to analyse them. Logs never contain document contents, transcripts or
            credentials.
          </p>
          <Button variant="danger" onClick={() => setConfirm(true)}>
            Delete my investigations, briefings and files
          </Button>
          {deleteData.isSuccess && <p className="text-positive">Your data was deleted.</p>}
        </CardBody>
      </Card>
      <Card>
        <CardHeader
          icon={<Database className="h-4 w-4" />}
          title="System"
          subtitle="Live provider configuration (no secrets are exposed)"
        />
        <CardBody>
          {health.data ? (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {Object.entries(health.data.providers).map(([k, v]) => (
                  <Badge key={k} tone={v ? 'positive' : 'neutral'}>
                    {v ? '✓' : '○'} {k.replace('_', ' ')}
                  </Badge>
                ))}
              </div>
              <ul className="grid gap-1 text-xs text-ink-3 sm:grid-cols-2">
                {Object.entries(health.data.ai_models).map(([role, m]) => (
                  <li key={role}>
                    <span className="text-ink-2">{role}</span>: {m.model}{' '}
                    <span className="text-ink-3">via {m.provider}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <Skeleton className="h-16 w-full" />
          )}
        </CardBody>
      </Card>
      <Card id="about">
        <CardHeader icon={<Info className="h-4 w-4" />} title="About & disclaimer" />
        <CardBody>
          <p className="text-sm leading-relaxed text-ink-2">{FULL_DISCLAIMER}</p>
        </CardBody>
      </Card>
      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Delete your data?"
        description="This permanently deletes your investigations, briefings, uploaded files and watchlist. Your login stays active."
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(false)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            loading={deleteData.isPending}
            onClick={() => deleteData.mutate(undefined, { onSuccess: () => setConfirm(false) })}
          >
            Delete permanently
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
