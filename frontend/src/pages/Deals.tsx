import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCategorizedDeals, dismissDeal, restoreDeal } from '../api/client'
import { PageHeader, EmptyState, Spinner } from '../components/shared'
import DealCard from '../components/DealCard'

type Tab = 'local' | 'regional' | 'worldwide'
type SortKey = 'date' | 'price' | 'rating'

export default function Deals() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('local')
  const [sort, setSort] = useState<SortKey>('date')

  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', 'categorized', sort],
    queryFn: () => fetchCategorizedDeals({ limit: 100, sort }),
  })

  const dismiss = useMutation({
    mutationFn: dismissDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  const restore = useMutation({
    mutationFn: restoreDeal,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deals'] }),
  })

  const deals = data ? data[tab] : []
  const counts = data?.counts

  const tabs: { key: Tab; label: string }[] = [
    { key: 'local', label: 'Local' },
    { key: 'regional', label: 'Regional' },
    { key: 'worldwide', label: 'Worldwide' },
  ]

  const sorts: { key: SortKey; label: string }[] = [
    { key: 'date', label: 'Newest' },
    { key: 'price', label: 'Cheapest' },
    { key: 'rating', label: 'Best deal' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Deals"
        subtitle="Flight deals from RSS feeds"
      />

      {/* Tabs + sort */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Tab pills */}
        <div className="flex rounded-lg bg-deck-surface border border-deck-border p-0.5" role="tablist" aria-label="Deal categories">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors min-h-[44px] ${
                tab === t.key
                  ? 'bg-deck-surface-hover text-deck-text-primary font-medium'
                  : 'text-deck-text-muted hover:text-deck-text-secondary'
              }`}
            >
              {t.label}
              {counts && (
                <span className="ml-1.5 text-xs text-deck-text-muted">
                  {counts[t.key]}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Sort pills */}
        <div className="flex items-center gap-1 ml-auto">
          <span className="text-xs text-deck-text-muted mr-1">Sort:</span>
          {sorts.map((s) => (
            <button
              key={s.key}
              onClick={() => setSort(s.key)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                sort === s.key
                  ? 'text-accent-primary font-medium'
                  : 'text-deck-text-muted hover:text-deck-text-secondary'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
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
          icon="🏷️"
          title={`No ${tab} deals`}
          description={
            tab === 'local'
              ? 'No deals from your home airports. Configure them in Settings.'
              : tab === 'regional'
              ? 'No deals from your region yet.'
              : 'No worldwide hub deals yet.'
          }
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
