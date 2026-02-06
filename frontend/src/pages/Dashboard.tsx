import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCategorizedDeals, fetchSystemStatus, dismissDeal, restoreDeal } from '../api/client'
import type { SystemStatus } from '../api/client'
import { PageHeader, EmptyState, Spinner } from '../components/shared'
import Card from '../components/shared/Card'
import DealCard from '../components/DealCard'

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

function StatusBar({ status }: { status: SystemStatus }) {
  const sourceEntries = Object.entries(status.data_sources)
  const apiSources = sourceEntries.filter(([, v]) => v.type === 'api')
  const scraperSources = sourceEntries.filter(([, v]) => v.type === 'scraper')

  return (
    <Card className="!p-3">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs">
        {/* Data sources */}
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
              <span className="capitalize">{name}</span>
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

        {/* Scheduler */}
        <div className="flex items-center gap-1.5">
          <SourceDot available={status.scheduler.running} />
          <span className="text-deck-text-secondary">
            Scheduler {status.scheduler.running ? 'running' : 'stopped'}
          </span>
        </div>

        <span className="hidden sm:block text-deck-border">|</span>

        {/* Stats */}
        <div className="flex items-center gap-3 text-deck-text-muted">
          <span>{status.stats.active_monitors} monitors</span>
          <span>{status.stats.recent_prices_7d} prices (7d)</span>
          <span>Last scrape: {timeAgo(status.stats.last_scrape_at)}</span>
        </div>
      </div>
    </Card>
  )
}

export default function Dashboard() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', 'categorized', 'date'],
    queryFn: () => fetchCategorizedDeals({ limit: 20, sort: 'date' }),
  })

  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: fetchSystemStatus,
    refetchInterval: 60000,
  })

  const dismiss = useMutation({
    mutationFn: dismissDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  const restore = useMutation({
    mutationFn: restoreDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  // Merge local + regional + worldwide, dedup, sort by date
  const allDeals = data
    ? [...data.local, ...data.regional, ...data.worldwide]
        .filter((deal, idx, arr) => arr.findIndex((d) => d.id === deal.id) === idx)
        .sort((a, b) => {
          const dateA = a.published_at ? new Date(a.published_at).getTime() : 0
          const dateB = b.published_at ? new Date(b.published_at).getTime() : 0
          return dateB - dateA
        })
        .slice(0, 20)
    : []

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Your morning flight briefing"
      />

      {status && <StatusBar status={status} />}

      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {error && (
        <div className="text-center py-12">
          <p className="text-deal-above text-sm">Failed to load deals</p>
          <p className="text-deck-text-muted text-xs mt-1">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {!isLoading && !error && allDeals.length === 0 && (
        <EmptyState
          icon="📡"
          title="Flight radar warming up"
          description="Deals will appear here as RSS feeds are ingested and prices are monitored."
          actionLabel="Browse all deals"
          onAction={() => window.location.href = '/deals'}
        />
      )}

      {allDeals.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {allDeals.map((deal) => (
            <DealCard
              key={deal.id}
              deal={deal}
              onDismiss={(id) => dismiss.mutate(id)}
              onRestore={(id) => restore.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
