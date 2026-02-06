import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchPriceHistory } from '../api/client'
import { Spinner } from './shared'

interface PriceChartProps {
  searchId: number
}

function getChartColors() {
  const style = getComputedStyle(document.documentElement)
  return {
    line: style.getPropertyValue('--chart-line').trim() || '#34d399',
    grid: style.getPropertyValue('--chart-grid').trim() || '#334155',
    tick: style.getPropertyValue('--chart-tick').trim() || '#94a3b8',
    tooltipBg: style.getPropertyValue('--chart-tooltip-bg').trim() || '#1e293b',
    tooltipBorder: style.getPropertyValue('--chart-tooltip-border').trim() || '#334155',
    tooltipText: style.getPropertyValue('--chart-tooltip-text').trim() || '#f1f5f9',
  }
}

export default function PriceChart({ searchId }: PriceChartProps) {
  const { data: prices, isLoading } = useQuery({
    queryKey: ['prices', searchId],
    queryFn: () => fetchPriceHistory(searchId, 30),
  })

  if (isLoading) {
    return (
      <div className="h-40 flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  if (!prices || prices.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-deck-text-muted text-sm">
        No price data yet
      </div>
    )
  }

  const chartData = prices
    .slice()
    .reverse()
    .map((p) => ({
      date: new Date(p.scraped_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      }),
      price: Number(p.price_nzd),
    }))

  const colors = getChartColors()

  return (
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: colors.tick }}
            stroke={colors.grid}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: colors.tick }}
            stroke={colors.grid}
            domain={['dataMin - 100', 'dataMax + 100']}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: colors.tooltipBg,
              border: `1px solid ${colors.tooltipBorder}`,
              borderRadius: '8px',
              color: colors.tooltipText,
            }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Price']}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke={colors.line}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
