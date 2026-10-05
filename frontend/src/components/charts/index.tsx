export { CandlestickChart } from './CandlestickChart';
export { DriverContributionBars, ContributionLabel } from './DriverContributionBars';
export {
  MacroSparkline,
  MarketComparisonChart,
  NewsVolumeChart,
  RiskRadar,
  SentimentTimeline,
  VolumeChart,
} from './RechartsCharts';

import { CandlestickChart } from './CandlestickChart';
import type { ComponentProps } from 'react';

/** Close-price line chart (same engine as the candlesticks). */
export function PriceChart(props: Omit<ComponentProps<typeof CandlestickChart>, 'mode'>) {
  return <CandlestickChart {...props} mode="line" />;
}
