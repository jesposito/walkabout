import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  fetchCategorizedDeals,
  fetchSystemStatus,
  fetchTripPlans,
  fetchSearchDefinitions,
  fetchAwardSearches,
  aiDealDigest,
  aiDealDigestEstimate,
} from '../api/client'
import type { SystemStatus, Deal, TripPlan, DealDigestResult } from '../api/client'
import { PageHeader, Spinner, Badge, PriceDisplay, AirportRoute, Card, AIActionButton } from '../components/shared'
import { useAirports, formatAirport } from '../hooks/useAirports'

function SourceDot({ available }: { available: boolean }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${available ? 'bg-deal-hot' : 'bg-deck-text-muted'}`} />
  )
}

function timeAgo(iso: string | null): string {
  if (!iso) return 'never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function TripPlanRoute({ plan }: { plan: TripPlan }) {
  const codes = [...plan.origins, ...plan.destinations]
  useAirports(codes)
  return (
    <p className="text-xs text-deck-text-muted mt-0.5">
      {plan.origins.length > 0 && (
        <span className="font-mono">{plan.origins.map((c) => formatAirport(c)).join(', ')}</span>
      )}
      {plan.origins.length > 0 && (plan.destinations.length > 0 || plan.destination_types.length > 0) && ' \u2192 '}
      {plan.destinations.length > 0 && (
        <span className="font-mono">{plan.destinations.map((c) => formatAirport(c)).join(', ')}</span>
      )}
      {plan.destination_types.length > 0 && (
        <span>{plan.destinations.length > 0 ? ' + ' : ''}{plan.destination_types.map((t) => t.replace(/_/g, ' ')).join(', ')}</span>
      )}
    </p>
  )
}

function StatusBar({ status }: { status: SystemStatus }) {
  const sourceEntries = Object.entries(status.data_sources)
  const apiSources = sourceEntries.filter(([, v]) => v.type === 'api')
  const scraperSources = sourceEntries.filter(([, v]) => v.type === 'scraper')

  return (
    <Card className="!p-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs" aria-live="polite">
        <div className="flex items-center gap-2">
          <span className="text-deck-text-muted font-medium uppercase tracking-wider">Sources</span>
          {apiSources.map(([name, info]) => (
            <span key={name} className="flex items-center gap-1.5 text-deck-text-secondary">
              <SourceDot available={info.available} />
              <span className="capitalize">{name}</span>
            </span>
          ))}
          {scraperSources.map(([name, info]) => (
            <span key={name} className="flex items-center gap-1.5 text-deck-text-secondary">
              <SourceDot available={info.available} />
              <span className="capitalize">{name === 'playwright' ? 'Google Flights Scraper' : name}</span>
            </span>
          ))}
          {status.ai_enabled && (
            <span className="flex items-center gap-1.5 text-deck-text-secondary">
              <SourceDot available={true} />
              AI
            </span>
          )}
        </div>

        <span className="hidden sm:block text-deck-border">|</span>

        <div className="flex items-center gap-1.5">
          <SourceDot available={status.scheduler.running} />
          <span className="text-deck-text-secondary">
            Scheduler {status.scheduler.running ? 'running' : 'stopped'}
          </span>
        </div>

        <span className="hidden sm:block text-deck-border">|</span>

        <div className="flex items-center gap-3 text-deck-text-muted">
          <span>{status.stats.active_monitors} monitors</span>
          <span>{status.stats.recent_prices_7d} prices (7d)</span>
          <span>Last scrape: {timeAgo(status.stats.last_scrape_at)}</span>
        </div>
      </div>
    </Card>
  )
}

function StatCard({ label, value, to }: { label: string; value: string | number; to: string }) {
  return (
    <Link to={to}>
      <Card interactive className="text-center !py-4">
        <p className="text-2xl font-semibold font-mono text-deck-text-primary">{value}</p>
        <p className="text-xs text-deck-text-muted uppercase tracking-wide mt-1">{label}</p>
      </Card>
    </Link>
  )
}

function CompactDeal({ deal }: { deal: Deal }) {
  const price = deal.converted_price ?? deal.price
  const currency = deal.converted_price != null ? (deal.preferred_currency || 'NZD') : (deal.currency || 'USD')
  const codes = [deal.origin, deal.destination].filter(Boolean) as string[]
  useAirports(codes)

  return (
    <a
      href={deal.link || '#'}
      target={deal.link ? '_blank' : undefined}
      rel={deal.link ? 'noopener noreferrer' : undefined}
      className="block"
    >
      <div className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-deck-surface-hover transition-colors group">
        <div className="flex items-center gap-3 min-w-0">
          {deal.origin && deal.destination ? (
            <AirportRoute origin={deal.origin} destination={deal.destination} />
          ) : (
            <span className="text-sm text-deck-text-primary truncate max-w-[200px]">
              {deal.title.slice(0, 60)}
            </span>
          )}
          {deal.airline && (
            <span className="text-xs text-deck-text-muted hidden sm:inline">{deal.airline}</span>
          )}
          {deal.rating_label && (
            <Badge variant={
              deal.rating_label.toLowerCase().includes('hot') ? 'hot' :
              deal.rating_label.toLowerCase().includes('good') ? 'good' : 'decent'
            }>
              {deal.rating_label}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {price != null && <PriceDisplay price={price} currency={currency} size="sm" />}
          <span className="text-xs text-accent-primary opacity-0 group-hover:opacity-100 transition-opacity">&rarr;</span>
        </div>
      </div>
    </a>
  )
}

function DealDigest() {
  return (
    <AIActionButton<DealDigestResult>
      label="Summarize deals"
      action={aiDealDigest}
      fetchEstimate={aiDealDigestEstimate}
      renderResult={(r) => (
        <div className="space-y-2">
          <p className="text-sm text-deck-text-primary break-words">{r.summary}</p>
          {r.highlights.length > 0 && (
            <ul className="space-y-1">
              {r.highlights.map((h, i) => (
                <li key={i} className="text-xs text-deck-text-secondary flex items-start gap-1.5">
                  <span className="text-accent-primary mt-0.5 shrink-0">--</span>
                  <span className="break-words min-w-0">{h}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    />
  )
}

export default function Dashboard() {
  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: fetchSystemStatus,
    refetchInterval: 60000,
  })

  const { data: deals, isLoading: dealsLoading } = useQuery({
    queryKey: ['deals', 'categorized', 'date'],
    queryFn: () => fetchCategorizedDeals({ limit: 10, sort: 'date' }),
  })

  const { data: tripPlans } = useQuery({
    queryKey: ['tripPlans'],
    queryFn: () => fetchTripPlans(),
  })

  const { data: watchlist } = useQuery({
    queryKey: ['searchDefinitions', true],
    queryFn: () => fetchSearchDefinitions(true),
  })

  const { data: awards } = useQuery({
    queryKey: ['awardSearches'],
    queryFn: () => fetchAwardSearches(),
  })

  const activePlans = tripPlans?.filter((p) => p.is_active) || []
  const activeAwards = awards?.filter((a) => a.is_active) || []

  // Top deals: dedup and take 6
  const topDeals = deals
    ? [...deals.local, ...deals.regional, ...deals.worldwide]
        .filter((deal, idx, arr) => arr.findIndex((d) => d.id === deal.id) === idx)
        .sort((a, b) => {
          const dateA = a.published_at ? new Date(a.published_at).getTime() : 0
          const dateB = b.published_at ? new Date(b.published_at).getTime() : 0
          return dateB - dateA
        })
        .slice(0, 6)
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Your flight monitoring overview"
      />

      {status && <StatusBar status={status} />}

      {/* Quick stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard label="Watchlist" value={watchlist?.length ?? 0} to="/watchlist" />
        <StatCard label="Trip Plans" value={activePlans.length} to="/trips" />
        <StatCard
          label="Deals"
          value={deals ? deals.counts.local + deals.counts.regional + deals.counts.worldwide : 0}
          to="/deals"
        />
        <StatCard label="Award Searches" value={activeAwards.length} to="/awards" />
      </div>

      {/* Two-column layout on desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Trip Plans */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-deck-text-muted uppercase tracking-wide">Active Trip Plans</h2>
            <Link to="/trips" className="text-xs text-accent-primary hover:underline">View all</Link>
          </div>
          {activePlans.length === 0 ? (
            <Card className="text-center !py-6">
              <p className="text-sm text-deck-text-muted">No active trip plans</p>
              <Link to="/trips" className="text-xs text-accent-primary hover:underline mt-1 inline-block">
                Create one
              </Link>
            </Card>
          ) : (
            <div className="space-y-2">
              {activePlans.slice(0, 4).map((plan) => (
                <Link key={plan.id} to="/trips">
                  <Card interactive>
                    <div className="flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-deck-text-primary truncate">{plan.name}</p>
                        <TripPlanRoute plan={plan} />
                      </div>
                      {plan.match_count > 0 && (
                        <Badge variant="hot">{plan.match_count} matches</Badge>
                      )}
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Watchlist */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-deck-text-muted uppercase tracking-wide">Watchlist</h2>
            <Link to="/watchlist" className="text-xs text-accent-primary hover:underline">View all</Link>
          </div>
          {!watchlist || watchlist.length === 0 ? (
            <Card className="text-center !py-6">
              <p className="text-sm text-deck-text-muted">No routes monitored</p>
              <Link to="/watchlist" className="text-xs text-accent-primary hover:underline mt-1 inline-block">
                Add a route
              </Link>
            </Card>
          ) : (
            <div className="space-y-2">
              {watchlist.slice(0, 4).map((route) => (
                <Link key={route.id} to="/watchlist">
                  <Card interactive>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <AirportRoute origin={route.origin} destination={route.destination} />
                        <span className="text-xs text-deck-text-muted capitalize">
                          {route.cabin_class} &middot; {route.stops_filter === 'any' ? 'any stops' : route.stops_filter}
                        </span>
                      </div>
                      <Badge variant={route.is_active ? 'info' : 'normal'}>
                        {route.is_active ? 'Active' : 'Paused'}
                      </Badge>
                    </div>
                    {route.name && (
                      <p className="text-xs text-deck-text-secondary mt-1">{route.name}</p>
                    )}
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Deals */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-medium text-deck-text-muted uppercase tracking-wide">Recent Deals</h2>
          <div className="flex items-center gap-3">
            <DealDigest />
            <Link to="/deals" className="text-xs text-accent-primary hover:underline">View all</Link>
          </div>
        </div>
        {dealsLoading ? (
          <div className="flex justify-center py-8">
            <Spinner size="lg" />
          </div>
        ) : topDeals.length === 0 ? (
          <Card className="text-center !py-6">
            <p className="text-sm text-deck-text-muted">No deals yet. Feeds are being ingested.</p>
          </Card>
        ) : (
          <Card className="!p-1 divide-y divide-deck-border">
            {topDeals.map((deal) => (
              <CompactDeal key={deal.id} deal={deal} />
            ))}
          </Card>
        )}
      </div>
    </div>
  )
}
