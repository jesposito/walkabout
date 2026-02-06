import { useQuery } from '@tanstack/react-query'
import { SearchDefinition, fetchPriceStats } from '../api/client'
import { Card, Badge, PriceDisplay, AirportRoute } from './shared'
import PriceChart from './PriceChart'

interface RouteCardProps {
  route: SearchDefinition
}

export default function RouteCard({ route }: RouteCardProps) {
  const { data: stats } = useQuery({
    queryKey: ['stats', route.id],
    queryFn: () => fetchPriceStats(route.id),
  })

  const displayName = route.name || `${route.origin} → ${route.destination}`

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-deck-text-primary">
          {displayName}
        </h3>
        <Badge variant={route.is_active ? 'info' : 'normal'}>
          {route.is_active ? 'Active' : 'Paused'}
        </Badge>
      </div>

      <p className="text-sm text-deck-text-secondary mb-4">
        <AirportRoute origin={route.origin} destination={route.destination} />
        <span className="ml-2">&middot; {route.cabin_class} &middot; {route.stops_filter}</span>
      </p>

      {stats && (
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs text-deck-text-muted uppercase">Current</p>
            {stats.current_price != null ? (
              <PriceDisplay price={stats.current_price} currency={route.currency || 'NZD'} size="lg" />
            ) : (
              <span className="font-mono text-price-lg text-deck-text-muted">N/A</span>
            )}
          </div>
          <div>
            <p className="text-xs text-deck-text-muted uppercase">Average</p>
            {stats.avg_price != null ? (
              <PriceDisplay price={stats.avg_price} currency={route.currency || 'NZD'} size="md" />
            ) : (
              <span className="font-mono text-price-md text-deck-text-muted">N/A</span>
            )}
          </div>
          <div>
            <p className="text-xs text-deck-text-muted uppercase">Lowest</p>
            {stats.min_price != null ? (
              <PriceDisplay price={stats.min_price} currency={route.currency || 'NZD'} size="md" trend="down" />
            ) : (
              <span className="font-mono text-price-md text-deck-text-muted">N/A</span>
            )}
          </div>
          <div>
            <p className="text-xs text-deck-text-muted uppercase">Highest</p>
            {stats.max_price != null ? (
              <PriceDisplay price={stats.max_price} currency={route.currency || 'NZD'} size="md" trend="up" />
            ) : (
              <span className="font-mono text-price-md text-deck-text-muted">N/A</span>
            )}
          </div>
        </div>
      )}

      <PriceChart searchId={route.id} />

      <div className="mt-4 text-xs text-deck-text-muted">
        {stats?.price_count || 0} price points tracked
      </div>
    </Card>
  )
}
