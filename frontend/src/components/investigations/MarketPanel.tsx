import type { InvestigationResult } from '@/types/api';
import {
  CandlestickChart,
  MacroSparkline,
  MarketComparisonChart,
  NewsVolumeChart,
  SentimentTimeline,
} from '@/components/charts';
import { Card, CardBody, CardHeader, Stat } from '@/components/ui/card';
import { Change } from '@/components/ui/change';
import { formatPct, formatPrice } from '@/lib/formatting';
import { EventTimeline } from './EventTimeline';

export function MarketPanel({ result }: { result: InvestigationResult }) {
  const market = result.market;
  const m = market?.metrics;
  const benchmark = result.macro?.indicators.find((i) => i.id === (m?.benchmark_symbol ?? '^GSPC'));
  return (
    <div className="space-y-5">
      {m && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat
            label="Move"
            value={<Change value={m.move_pct} size="lg" />}
            hint={`as of ${m.as_of ?? '—'}`}
          />
          <Stat
            label="Volume vs 20d"
            value={formatPct(m.volume_change_pct, 0)}
            hint={m.unusual_move ? 'Unusual session' : 'Within normal range'}
          />
          <Stat
            label="Volatility (20d, ann.)"
            value={m.volatility_20d !== null ? `${(m.volatility_20d * 100).toFixed(1)}%` : '—'}
            hint={`z-score ${m.zscore_move?.toFixed(2) ?? '—'}`}
          />
          <Stat
            label="Max drawdown (30d)"
            value={formatPct(m.drawdown_30d, 1, false)}
            hint={`vs benchmark ${formatPct(m.relative_performance_pct)} pp`}
          />
        </div>
      )}
      {market && (
        <Card>
          <CardHeader
            title="Price & volume"
            subtitle={`${m?.symbol} daily candles · ${formatPrice(m?.last_price, m?.currency)} · Market data may be delayed`}
          />
          <CardBody>
            <CandlestickChart
              data={market.history.slice(-90)}
              height={340}
              label={`${m?.symbol} price chart`}
            />
          </CardBody>
        </Card>
      )}
      <div className="grid gap-5 lg:grid-cols-2">
        {market && market.intraday.length > 0 && (
          <Card>
            <CardHeader title="Latest session (intraday)" subtitle="5-minute bars" />
            <CardBody>
              <CandlestickChart data={market.intraday} height={240} mode="line" label="Intraday price" />
            </CardBody>
          </Card>
        )}
        {market && benchmark && (
          <Card>
            <CardHeader
              title="Relative performance"
              subtitle={`${m?.symbol} vs ${benchmark.name}, rebased to 100`}
            />
            <CardBody>
              <MarketComparisonChart
                asset={market.history.slice(-30).map((p) => ({ date: p.time, value: p.close }))}
                benchmark={benchmark.series}
                assetLabel={m?.symbol ?? 'Asset'}
                benchmarkLabel={benchmark.name}
              />
            </CardBody>
          </Card>
        )}
        {result.sentiment && (
          <Card>
            <CardHeader
              title="Sentiment timeline"
              subtitle={`${result.sentiment.label} · change ${result.sentiment.sentiment_change?.toFixed(2) ?? 'n/a'} · ${result.sentiment.agreement} sources`}
            />
            <CardBody>
              <SentimentTimeline data={result.sentiment.timeline} />
              <p className="mt-2 text-[11px] text-ink-3">
                −1 very negative · 0 neutral · +1 very positive. Tone labels are model interpretations of
                headlines.
              </p>
            </CardBody>
          </Card>
        )}
        {result.news && result.news.volume_timeline.length > 0 && (
          <Card>
            <CardHeader title="News volume" subtitle="Articles per hour (GDELT)" />
            <CardBody>
              <NewsVolumeChart data={result.news.volume_timeline} />
            </CardBody>
          </Card>
        )}
        {result.events && (
          <Card>
            <CardHeader
              title="Event timeline"
              subtitle="News, market sessions, filings and uploads in order"
            />
            <CardBody>
              <EventTimeline events={result.events.events} />
            </CardBody>
          </Card>
        )}
      </div>
      {result.macro && result.macro.indicators.length > 0 && (
        <Card>
          <CardHeader title="Market & macro context" subtitle={result.macro.notes.join(' ')} />
          <CardBody>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {result.macro.indicators.map((i) => (
                <li key={i.id} className="rounded-xl border border-line p-3">
                  <p className="text-xs text-ink-3">{i.name}</p>
                  <p className="tabular mt-1 flex items-baseline justify-between text-sm font-semibold text-ink">
                    {i.value?.toLocaleString('en-US', { maximumFractionDigits: 2 })}
                    <Change value={i.change} className="text-xs" />
                  </p>
                  <MacroSparkline indicator={i} />
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
