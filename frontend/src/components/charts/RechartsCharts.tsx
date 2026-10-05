import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MacroIndicator, PricePoint, RiskItem, SeriesPoint } from '@/types/api';
import { axisStyle, shortDate, token } from '@/lib/charts/theme';
import { titleCase } from '@/lib/formatting';
import { ChartFrame } from './ChartFrame';

const tooltipStyle = {
  contentStyle: {
    background: token('elevated'),
    border: `1px solid ${token('line')}`,
    borderRadius: 10,
    fontSize: 12,
    color: token('ink'),
  },
  labelStyle: { color: token('ink-2') },
  cursor: { stroke: token('line') },
};

/** Sentiment timeline in [-1, +1] with a neutral baseline. */
export function SentimentTimeline({
  data,
  height = 220,
  loading,
}: {
  data: SeriesPoint[];
  height?: number;
  loading?: boolean;
}) {
  return (
    <ChartFrame
      loading={loading}
      empty={!data.length}
      emptyLabel="No sentiment data for this period."
      height={height}
      label="Sentiment timeline"
    >
      <ResponsiveContainer width="100%" height={height} minWidth={300}>
        <AreaChart data={data} margin={{ top: 10, right: 12, left: -18, bottom: 0 }}>
          <defs>
            <linearGradient id="sent" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={token('primary')} stopOpacity={0.45} />
              <stop offset="100%" stopColor={token('accent')} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={token('line')} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={axisStyle}
            stroke={token('line')}
            minTickGap={24}
          />
          <YAxis domain={[-1, 1]} ticks={[-1, -0.5, 0, 0.5, 1]} tick={axisStyle} stroke={token('line')} />
          <ReferenceLine y={0} stroke={token('ink-3')} strokeDasharray="4 4" />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(v) => shortDate(String(v))}
            formatter={(v) => [Number(v).toFixed(2), 'Tone']}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={token('primary-soft')}
            strokeWidth={2}
            fill="url(#sent)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function NewsVolumeChart({ data, height = 180 }: { data: SeriesPoint[]; height?: number }) {
  return (
    <ChartFrame
      empty={!data.length}
      emptyLabel="News volume timeline unavailable (GDELT)."
      height={height}
      label="News volume"
    >
      <ResponsiveContainer width="100%" height={height} minWidth={300}>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke={token('line')} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={axisStyle}
            stroke={token('line')}
            minTickGap={24}
          />
          <YAxis tick={axisStyle} stroke={token('line')} />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(v) => shortDate(String(v))}
            formatter={(v) => [v, 'Articles']}
          />
          <Bar dataKey="value" fill={token('primary')} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function VolumeChart({ data, height = 160 }: { data: PricePoint[]; height?: number }) {
  const rows = data.map((p) => ({ date: p.time, volume: p.volume ?? 0, up: p.close >= p.open }));
  return (
    <ChartFrame empty={!rows.length} height={height} label="Volume">
      <ResponsiveContainer width="100%" height={height} minWidth={300}>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={axisStyle}
            stroke={token('line')}
            minTickGap={30}
          />
          <YAxis
            tick={axisStyle}
            stroke={token('line')}
            tickFormatter={(v) => Intl.NumberFormat('en', { notation: 'compact' }).format(Number(v))}
          />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(v) => shortDate(String(v))}
            formatter={(v) => [Intl.NumberFormat('en').format(Number(v)), 'Volume']}
          />
          <Bar dataKey="volume" fill={token('primary')} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

const RISK_SCORE = { LOW: 1, MEDIUM: 2, HIGH: 3 } as const;
const RISK_AXES = [
  'regulatory',
  'valuation',
  'operational',
  'competition',
  'macro',
  'liquidity',
  'concentration',
  'market',
];

/** Qualitative risk levels (LOW=1, MEDIUM=2, HIGH=3) — not probabilities. */
export function RiskRadar({ risks, height = 260 }: { risks: RiskItem[]; height?: number }) {
  const rows = RISK_AXES.map((axis) => {
    const item = risks.find((r) => r.risk === axis);
    return { axis: titleCase(axis), level: item ? RISK_SCORE[item.level] : 0 };
  });
  return (
    <ChartFrame empty={!risks.length} emptyLabel="No assessed risks." height={height} label="Risk radar">
      <ResponsiveContainer width="100%" height={height} minWidth={280}>
        <RadarChart data={rows} outerRadius="72%">
          <PolarGrid stroke={token('line')} />
          <PolarAngleAxis dataKey="axis" tick={{ ...axisStyle, fill: token('ink-2') }} />
          <PolarRadiusAxis domain={[0, 3]} tickCount={4} tick={false} axisLine={false} />
          <Radar dataKey="level" stroke={token('accent')} fill={token('accent')} fillOpacity={0.25} />
          <Tooltip
            {...tooltipStyle}
            formatter={(v) => [['None', 'Low', 'Medium', 'High'][Number(v)], 'Level']}
          />
        </RadarChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

/** Asset vs benchmark, both rebased to 100 at the start of the window. */
export function MarketComparisonChart({
  asset,
  benchmark,
  assetLabel,
  benchmarkLabel,
  height = 220,
}: {
  asset: SeriesPoint[];
  benchmark: SeriesPoint[];
  assetLabel: string;
  benchmarkLabel: string;
  height?: number;
}) {
  const bench = new Map(benchmark.map((p) => [p.date.slice(0, 10), p.value]));
  const aligned = asset.filter((p) => bench.has(p.date.slice(0, 10)));
  const a0 = aligned[0]?.value;
  const b0 = aligned.length ? bench.get(aligned[0].date.slice(0, 10)) : undefined;
  const rows =
    a0 && b0
      ? aligned.map((p) => ({
          date: p.date,
          asset: (p.value / a0) * 100,
          bench: ((bench.get(p.date.slice(0, 10)) as number) / b0) * 100,
        }))
      : [];
  return (
    <ChartFrame
      empty={rows.length < 2}
      emptyLabel="Benchmark comparison unavailable."
      height={height}
      label="Relative performance"
    >
      <ResponsiveContainer width="100%" height={height} minWidth={300}>
        <LineChart data={rows} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
          <CartesianGrid stroke={token('line')} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={shortDate}
            tick={axisStyle}
            stroke={token('line')}
            minTickGap={30}
          />
          <YAxis tick={axisStyle} stroke={token('line')} domain={['auto', 'auto']} />
          <ReferenceLine y={100} stroke={token('ink-3')} strokeDasharray="4 4" />
          <Tooltip
            {...tooltipStyle}
            labelFormatter={(v) => shortDate(String(v))}
            formatter={(v, name) => [Number(v).toFixed(1), name === 'asset' ? assetLabel : benchmarkLabel]}
          />
          <Line type="monotone" dataKey="asset" stroke={token('primary-soft')} dot={false} strokeWidth={2} />
          <Line
            type="monotone"
            dataKey="bench"
            stroke={token('ink-3')}
            dot={false}
            strokeWidth={1.5}
            strokeDasharray="5 4"
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartFrame>
  );
}

export function MacroSparkline({ indicator, height = 40 }: { indicator: MacroIndicator; height?: number }) {
  if (indicator.series.length < 2) return <div style={{ height }} />;
  const rising = indicator.series[indicator.series.length - 1].value >= indicator.series[0].value;
  return (
    <div aria-hidden style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={indicator.series}>
          <Line
            type="monotone"
            dataKey="value"
            stroke={rising ? token('positive') : token('negative')}
            dot={false}
            strokeWidth={1.5}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
