import type { ModelUsage } from '@/types/api';

/** Model usage is observable per investigation: model, provider, tokens, latency, cost. */
export function ModelUsagePanel({ usage }: { usage: ModelUsage[] }) {
  if (!usage.length) return <p className="text-sm text-ink-3">No model calls were needed.</p>;
  const total = usage.reduce((sum, u) => sum + (u.cost_usd ?? 0), 0);
  const models = new Set(usage.map((u) => u.model));
  return (
    <div>
      <p className="mb-3 text-xs text-ink-3">
        {usage.length} calls · {models.size} specialised models · total cost ≈ ${total.toFixed(4)}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-xs">
          <thead>
            <tr className="text-left text-ink-3">
              <th className="pb-2 font-medium">Agent</th>
              <th className="pb-2 font-medium">Purpose</th>
              <th className="pb-2 font-medium">Model</th>
              <th className="pb-2 text-right font-medium">Tokens in/out</th>
              <th className="pb-2 text-right font-medium">Latency</th>
              <th className="pb-2 text-right font-medium">Cost</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {usage.map((u, i) => (
              <tr key={i} className="border-t border-line/70 text-ink-2">
                <td className="py-1.5">{u.agent}</td>
                <td className="py-1.5">{u.purpose}</td>
                <td className="py-1.5 text-ink">{u.model}</td>
                <td className="py-1.5 text-right">
                  {u.input_tokens ?? '—'} / {u.output_tokens ?? '—'}
                </td>
                <td className="py-1.5 text-right">{(u.latency_ms / 1000).toFixed(1)}s</td>
                <td className="py-1.5 text-right">
                  {u.cost_usd !== null ? `$${u.cost_usd.toFixed(5)}` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
