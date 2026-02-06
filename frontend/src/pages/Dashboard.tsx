import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCategorizedDeals, dismissDeal, restoreDeal } from '../api/client'
import { PageHeader, EmptyState, Spinner } from '../components/shared'
import DealCard from '../components/DealCard'

export default function Dashboard() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', 'categorized', 'date'],
    queryFn: () => fetchCategorizedDeals({ limit: 20, sort: 'date' }),
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
