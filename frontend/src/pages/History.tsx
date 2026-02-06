import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  fetchSearchDefinitions,
  fetchPriceStats,
  fetchFlightOptions,
  SearchDefinition,
  PriceStats,
} from '../api/client'
import PriceChart from '../components/PriceChart'
import { PageHeader, Card, EmptyState, Spinner, Badge } from '../components/shared'

function TrendArrow({ trend }: { trend: string | null }) {
  if (!trend) return null
  if (trend === 'down') return <span className="text-deal-hot">&#8595;</span>
  if (trend === 'up') return <span className="text-deal-above">&#8593;</span>
  return <span className="text-deck-text-muted">&#8594;</span>
}

function StatsPanel({ stats, currency }: { stats: PriceStats; currency: string }) {
  const fmt = (v: number | null) =>
    v != null
      ? new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency,
          minimumFractionDigits: 0,
          maximumFractionDigits: 0,
        }).format(v)
      : '—'

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div className="text-center">
        <p className="text-xs text-deck-text-muted uppercase">Current</p>
        <p className="text-lg font-mono text-deck-text-primary">
          {fmt(stats.current_price)} <TrendArrow trend={stats.price_trend} />
        </p>
      </div>
      <div className="text-center">
        <p className="text-xs text-deck-text-muted uppercase">Average</p>
        <p className="text-lg font-mono text-deck-text-secondary">{fmt(stats.avg_price)}</p>
      </div>
      <div className="text-center">
        <p className="text-xs text-deck-text-muted uppercase">Min</p>
        <p className="text-lg font-mono text-deal-hot">{fmt(stats.min_price)}</p>
      </div>
      <div className="text-center">
        <p className="text-xs text-deck-text-muted uppercase">Max</p>
        <p className="text-lg font-mono text-deck-text-muted">{fmt(stats.max_price)}</p>
      </div>
    </div>
  )
}

interface FlightOption {
  airline: string | null
  stops: number
  price_nzd: number
  duration_minutes: number | null
  departure_date: string
  return_date: string | null
}

function OptionsTable({ options, currency }: { options: FlightOption[]; currency: string }) {
  if (!options || options.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-deck-text-muted uppercase border-b border-deck-border">
            <th className="text-left py-2 pr-4">Airline</th>
            <th className="text-left py-2 pr-4">Stops</th>
            <th className="text-right py-2 pr-4">Price</th>
            <th className="text-right py-2 pr-4">Duration</th>
            <th className="text-left py-2">Dates</th>
          </tr>
        </thead>
        <tbody>
          {options.map((opt, i) => (
            <tr key={i} className="border-b border-deck-border/50">
              <td className="py-2 pr-4 text-deck-text-primary">{opt.airline || 'Unknown'}</td>
              <td className="py-2 pr-4 text-deck-text-secondary">
                {opt.stops === 0 ? 'Nonstop' : `${opt.stops} stop${opt.stops !== 1 ? 's' : ''}`}
              </td>
              <td className="py-2 pr-4 text-right font-mono text-deck-text-primary">
                {new Intl.NumberFormat('en-US', {
                  style: 'currency',
                  currency,
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                }).format(opt.price_nzd)}
              </td>
              <td className="py-2 pr-4 text-right text-deck-text-secondary">
                {opt.duration_minutes
                  ? `${Math.floor(opt.duration_minutes / 60)}h ${opt.duration_minutes % 60}m`
                  : '—'}
              </td>
              <td className="py-2 text-deck-text-muted text-xs">
                {new Date(opt.departure_date).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                })}
                {opt.return_date &&
                  ` - ${new Date(opt.return_date).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                  })}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RouteHistoryCard({ route }: { route: SearchDefinition }) {
  const { data: stats } = useQuery({
    queryKey: ['price-stats', route.id],
    queryFn: () => fetchPriceStats(route.id),
  })

  const { data: optionsData } = useQuery({
    queryKey: ['flight-options', route.id],
    queryFn: () => fetchFlightOptions(route.id, 5),
  })

  const currency = route.currency || 'USD'
  const options = (optionsData?.options || []) as FlightOption[]

  return (
    <Card className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-deck-text-primary">
            {route.origin} &#8594; {route.destination}
          </h3>
          <p className="text-xs text-deck-text-muted">
            {route.cabin_class} &middot; {route.adults} adult{route.adults !== 1 ? 's' : ''}
            {route.children > 0 && ` + ${route.children} child${route.children !== 1 ? 'ren' : ''}`}
            {route.stops_filter !== 'any' && ` &middot; ${route.stops_filter}`}
          </p>
        </div>
        <Badge variant={route.is_active ? 'good' : 'normal'}>
          {route.is_active ? 'Active' : 'Paused'}
        </Badge>
      </div>

      {/* Price chart */}
      <PriceChart searchId={route.id} />

      {/* Stats */}
      {stats && stats.price_count > 0 && (
        <StatsPanel stats={stats} currency={currency} />
      )}

      {/* Cheapest options */}
      {options.length > 0 && (
        <div>
          <p className="text-xs text-deck-text-muted uppercase mb-2">Cheapest Options</p>
          <OptionsTable options={options} currency={currency} />
        </div>
      )}
    </Card>
  )
}

export default function History() {
  const [selectedRoute, setSelectedRoute] = useState<number | 'all'>('all')

  const { data: routes, isLoading } = useQuery({
    queryKey: ['search-definitions'],
    queryFn: () => fetchSearchDefinitions(false),
  })

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!routes || routes.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="History" subtitle="Price history and trends" />
        <EmptyState
          icon="📈"
          title="No routes tracked"
          description="Add routes on the Watchlist page to see price history here."
        />
      </div>
    )
  }

  const filtered =
    selectedRoute === 'all' ? routes : routes.filter((r) => r.id === selectedRoute)

  return (
    <div className="space-y-6">
      <PageHeader
        title="History"
        subtitle="Price history and trends"
        actions={
          routes.length > 1 ? (
            <select
              value={selectedRoute}
              onChange={(e) =>
                setSelectedRoute(e.target.value === 'all' ? 'all' : Number(e.target.value))
              }
              className="px-3 py-1.5 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              <option value="all">All routes ({routes.length})</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.origin} → {r.destination}
                </option>
              ))}
            </select>
          ) : undefined
        }
      />

      <div className="space-y-6">
        {filtered.map((route) => (
          <RouteHistoryCard key={route.id} route={route} />
        ))}
      </div>
    </div>
  )
}
