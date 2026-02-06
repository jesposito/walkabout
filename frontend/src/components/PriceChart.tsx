import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchPriceHistory } from '../api/client'
import { Spinner } from './shared'

interface PriceChartProps {
  searchId: number
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
      date: new Date(p.scraped_at).toLocaleDateString('en-NZ', {
        month: 'short',
        day: 'numeric'
      }),
      price: Number(p.price_nzd),
    }))

  return (
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            stroke="#334155"
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            stroke="#334155"
            domain={['dataMin - 100', 'dataMax + 100']}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#252525',
              border: '1px solid #333333',
              borderRadius: '8px',
              color: '#e2e8f0',
            }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Price']}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#34d399"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
