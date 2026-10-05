import { useEffect, useRef, useState } from 'react';
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { PricePoint } from '@/types/api';
import { token, toUnixSeconds } from '@/lib/charts/theme';
import { ChartFrame } from './ChartFrame';

interface Props {
  data: PricePoint[];
  height?: number;
  loading?: boolean;
  error?: string | null;
  mode?: 'candles' | 'line';
  showVolume?: boolean;
  label?: string;
}

/** OHLC candlesticks (or price line) with a volume histogram — TradingView Lightweight Charts. */
export function CandlestickChart({
  data,
  height = 320,
  loading,
  error,
  mode = 'candles',
  showVolume = true,
  label = 'Price chart',
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!ref.current || !data.length) return;
    let chart: IChartApi;
    try {
      chart = createChart(ref.current, {
        height,
        autoSize: true,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: token('ink-3'),
          fontFamily: 'Inter, sans-serif',
          attributionLogo: false,
        },
        grid: { vertLines: { color: token('line') + '55' }, horzLines: { color: token('line') + '55' } },
        rightPriceScale: { borderColor: token('line') },
        timeScale: {
          borderColor: token('line'),
          timeVisible: data[0]?.time.length > 10,
          secondsVisible: false,
        },
        crosshair: { mode: CrosshairMode.Normal },
        localization: { locale: 'en-US' },
      });
    } catch {
      setFailed(true);
      return;
    }
    chartRef.current = chart;
    const points = data.map((p) => ({ ...p, t: toUnixSeconds(p.time) as UTCTimestamp }));
    if (mode === 'candles') {
      const candles = chart.addSeries(CandlestickSeries, {
        upColor: token('positive'),
        downColor: token('negative'),
        borderVisible: false,
        wickUpColor: token('positive'),
        wickDownColor: token('negative'),
      });
      candles.setData(
        points.map((p) => ({ time: p.t, open: p.open, high: p.high, low: p.low, close: p.close })),
      );
    } else {
      const line = chart.addSeries(LineSeries, { color: token('primary-soft'), lineWidth: 2 });
      line.setData(points.map((p) => ({ time: p.t, value: p.close })));
    }
    if (showVolume) {
      const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '' });
      volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
      volume.setData(
        points
          .filter((p) => p.volume)
          .map((p) => ({
            time: p.t,
            value: p.volume as number,
            color: (p.close >= p.open ? token('positive') : token('negative')) + '55',
          })),
      );
    }
    chart.timeScale().fitContent();
    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [data, height, mode, showVolume]);

  return (
    <ChartFrame
      loading={loading}
      error={error ?? (failed ? 'Your browser could not render this chart.' : null)}
      empty={!data.length}
      height={height}
      label={label}
    >
      <div ref={ref} style={{ height }} className="w-full min-w-[320px]" />
    </ChartFrame>
  );
}
