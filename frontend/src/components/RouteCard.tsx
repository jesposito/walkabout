import { useQuery } from '@tanstack/react-query'
import { Route, fetchPriceStats } from '../api/client'
import PriceChart from './PriceChart'

interface RouteCardProps {
  route: Route
}

export default function RouteCard({ route }: RouteCardProps) {
  const { data: stats } = useQuery({
    queryKey: ['stats', route.id],
    queryFn: () => fetchPriceStats(route.id),
  })

  const formatPrice = (price: number | null | undefined) => {
    if (price == null) return 'N/A'
    return `$${price.toLocaleString()}`
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            {route.origin} → {route.destination}
          </h3>
          <span className={`px-2 py-1 text-xs rounded ${
            route.is_active 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-800'
          }`}>
            {route.is_active ? 'Active' : 'Paused'}
          </span>
        </div>

        <p className="text-gray-600 text-sm mb-4">{route.name}</p>

        {stats && (
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500 uppercase">Current</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatPrice(stats.current_price)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Average</p>
              <p className="text-lg text-gray-700">
                {formatPrice(stats.avg_price)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Lowest</p>
              <p className="text-lg text-green-600">
                {formatPrice(stats.min_price)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase">Highest</p>
              <p className="text-lg text-red-600">
                {formatPrice(stats.max_price)}
              </p>
            </div>
          </div>
        )}

        <PriceChart routeId={route.id} />

        <div className="mt-4 text-xs text-gray-400">
          {stats?.price_count || 0} price points tracked
        </div>
      </div>
    </div>
  )
}
