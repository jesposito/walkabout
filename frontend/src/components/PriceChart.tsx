import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { fetchPriceHistory } from '../api/client'

interface PriceChartProps {
  routeId: number
}

export default function PriceChart({ routeId }: PriceChartProps) {
  const { data: prices, isLoading } = useQuery({
    queryKey: ['prices', routeId],
    queryFn: () => fetchPriceHistory(routeId, 30),
  })

  if (isLoading) {
    return (
      <div className="h-40 flex items-center justify-center">
        <div className="animate-pulse bg-gray-200 w-full h-32 rounded"></div>
      </div>
    )
  }

  if (!prices || prices.length === 0) {
    return (
      <div className="h-40 flex items-center justify-center text-gray-400 text-sm">
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
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis 
            tick={{ fontSize: 10 }}
            domain={['dataMin - 100', 'dataMax + 100']}
            tickFormatter={(v) => `$${v}`}
          />
          <Tooltip 
            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Price']}
          />
          <Line 
            type="monotone" 
            dataKey="price" 
            stroke="#2563eb" 
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
