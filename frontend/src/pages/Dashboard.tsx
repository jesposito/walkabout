import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDeals, dismissDeal, restoreDeal } from '../api/client'
import { PageHeader, EmptyState, Spinner } from '../components/shared'
import DealCard from '../components/DealCard'

export default function Dashboard() {
  const queryClient = useQueryClient()

  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', 'dashboard'],
    queryFn: () => fetchDeals({ relevant: true, limit: 20 }),
  })

  const dismiss = useMutation({
    mutationFn: dismissDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  const restore = useMutation({
    mutationFn: restoreDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  const deals = data?.deals ?? []

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

      {!isLoading && !error && deals.length === 0 && (
        <EmptyState
          icon="📡"
          title="Flight radar warming up"
          description="Deals will appear here as RSS feeds are ingested and prices are monitored."
          actionLabel="Browse all deals"
          onAction={() => window.location.href = '/deals'}
        />
      )}

      {deals.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {deals.map((deal) => (
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
