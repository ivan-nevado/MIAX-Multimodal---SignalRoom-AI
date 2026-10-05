import { useMemo, useState } from 'react';
import {
  Background,
  Controls,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { Driver, Source } from '@/types/api';
import { Dialog } from '@/components/ui/dialog';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { formatPct } from '@/lib/formatting';
import { token } from '@/lib/charts/theme';
import { SOURCE_ICONS, SourceCard } from './SourceCard';

type RootData = { label: string; move: number | null };
type DriverData = { label: string; score: number };
type SourceData = { source: Source };

function RootNode({ data }: NodeProps<Node<RootData>>) {
  return (
    <div className="glow rounded-xl border border-primary/40 bg-elevated px-4 py-3 text-center">
      <p className="font-display text-sm font-semibold text-ink">{data.label}</p>
      <p
        className={`tabular text-lg font-semibold ${data.move !== null && data.move < 0 ? 'text-negative' : 'text-positive'}`}
      >
        {formatPct(data.move)}
      </p>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
}

function DriverNode({ data }: NodeProps<Node<DriverData>>) {
  return (
    <div className="w-48 rounded-xl border border-line bg-surface px-3 py-2.5">
      <Handle type="target" position={Position.Top} className="!bg-primary" />
      <p className="line-clamp-2 text-[13px] font-medium text-ink">{data.label}</p>
      <p className="tabular mt-0.5 text-xs text-primary-soft">{data.score.toFixed(0)}% evidence-weighted</p>
      <Handle type="source" position={Position.Bottom} className="!bg-primary" />
    </div>
  );
}

function SourceNode({ data }: NodeProps<Node<SourceData>>) {
  const Icon = SOURCE_ICONS[data.source.source_type];
  return (
    <button
      type="button"
      className="w-40 rounded-lg border border-line bg-elevated px-2.5 py-2 text-left hover:border-primary/60"
    >
      <Handle type="target" position={Position.Top} className="!bg-ink-3" />
      <span className="flex items-center gap-1.5 text-[11px] text-ink-3">
        <Icon className="h-3 w-3" aria-hidden />
        {data.source.publisher}
      </span>
      <span className="mt-0.5 line-clamp-2 block text-[11px] leading-snug text-ink-2">
        {data.source.title}
      </span>
    </button>
  );
}

const nodeTypes = { root: RootNode, driver: DriverNode, source: SourceNode };

export function buildEvidenceGraph(
  rootLabel: string,
  move: number | null,
  drivers: Driver[],
  sources: Source[],
) {
  const byId = new Map(sources.map((s) => [s.id, s]));
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const driverGap = 230;
  const width = Math.max(drivers.length - 1, 0) * driverGap;
  nodes.push({
    id: 'root',
    type: 'root',
    position: { x: width / 2 - 60, y: 0 },
    data: { label: rootLabel, move },
  });
  const placed = new Map<string, Node>();
  let column = 0;
  drivers.forEach((d, i) => {
    const x = i * driverGap;
    nodes.push({
      id: d.driver_id,
      type: 'driver',
      position: { x, y: 130 },
      data: { label: d.name, score: d.contribution_score },
    });
    edges.push({
      id: `root-${d.driver_id}`,
      source: 'root',
      target: d.driver_id,
      animated: i === 0,
      style: { stroke: token('primary'), strokeWidth: 1 + d.contribution_score / 30 },
    });
    d.evidence_ids.slice(0, 3).forEach((sid) => {
      const src = byId.get(sid);
      if (!src) return;
      if (!placed.has(sid)) {
        const node: Node = {
          id: sid,
          type: 'source',
          position: { x: column * 175 - 20, y: 270 + (column % 2) * 70 },
          data: { source: src },
        };
        placed.set(sid, node);
        nodes.push(node);
        column += 1;
      }
      edges.push({
        id: `${d.driver_id}-${sid}`,
        source: d.driver_id,
        target: sid,
        style: { stroke: token('line-strong') },
      });
    });
  });
  return { nodes, edges };
}

/** Visual evidence graph: asset move → likely drivers → supporting sources (click to open). */
export function EvidenceGraph({
  rootLabel,
  move,
  drivers,
  sources,
}: {
  rootLabel: string;
  move: number | null;
  drivers: Driver[];
  sources: Source[];
}) {
  const isMobile = useMediaQuery('(max-width: 767px)');
  const [selected, setSelected] = useState<Source | null>(null);
  const { nodes, edges } = useMemo(
    () => buildEvidenceGraph(rootLabel, move, drivers, sources),
    [rootLabel, move, drivers, sources],
  );
  const byId = useMemo(() => new Map(sources.map((s) => [s.id, s])), [sources]);

  if (!drivers.length) return <p className="text-sm text-ink-3">No supporting source was found.</p>;

  if (isMobile) {
    // Stacked, simplified graph on small screens.
    return (
      <ol className="space-y-4" aria-label="Evidence graph">
        {drivers.map((d) => (
          <li key={d.driver_id} className="rounded-xl border border-line p-3">
            <p className="text-sm font-medium text-ink">
              {d.name} <span className="tabular text-primary-soft">· {d.contribution_score.toFixed(0)}%</span>
            </p>
            <div className="mt-2 space-y-2 border-l border-line pl-3">
              {d.evidence_ids
                .map((id) => byId.get(id))
                .filter(Boolean)
                .slice(0, 3)
                .map((s) => (
                  <SourceCard key={s!.id} source={s!} compact />
                ))}
            </div>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <>
      <div
        className="h-[460px] w-full overflow-hidden rounded-xl border border-line bg-background"
        aria-label="Evidence graph"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          nodesDraggable
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => node.type === 'source' && setSelected((node.data as SourceData).source)}
          colorMode="dark"
        >
          <Background color={token('line')} gap={22} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <Dialog
        open={Boolean(selected)}
        onOpenChange={(o) => !o && setSelected(null)}
        title="Source"
        description="Every conclusion links back to its evidence."
      >
        {selected && <SourceCard source={selected} />}
      </Dialog>
    </>
  );
}
