import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchDeals, dismissDeal, restoreDeal } from '../api/client'
import { PageHeader, EmptyState, Spinner, Button } from '../components/shared'
import DealCard from '../components/DealCard'

type Tab = 'all' | 'relevant'
type SortKey = 'date' | 'price' | 'rating'

export default function Deals() {
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<Tab>('relevant')
  const [sort, setSort] = useState<SortKey>('date')
  const [limit, setLimit] = useState(30)

  const { data, isLoading, error } = useQuery({
    queryKey: ['deals', tab, limit],
    queryFn: () =>
      fetchDeals({
        relevant: tab === 'relevant' ? true : undefined,
        limit,
      }),
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

  // Client-side sorting (backend returns by relevance/date)
  const sorted = [...deals].sort((a, b) => {
    if (sort === 'price') {
      return (a.price ?? 999999) - (b.price ?? 999999)
    }
    if (sort === 'rating') {
      return (b.deal_rating ?? -999) - (a.deal_rating ?? -999)
    }
    // date (newest first)
    const dateA = a.published_at ? new Date(a.published_at).getTime() : 0
    const dateB = b.published_at ? new Date(b.published_at).getTime() : 0
    return dateB - dateA
  })

  const tabs: { key: Tab; label: string }[] = [
    { key: 'relevant', label: 'Relevant' },
    { key: 'all', label: 'All' },
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
        subtitle="Flight deals from RSS feeds and price monitoring"
      />

      {/* Tabs + sort */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Tab pills */}
        <div className="flex rounded-lg bg-deck-surface border border-deck-border p-0.5">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                tab === t.key
                  ? 'bg-deck-surface-hover text-deck-text-primary font-medium'
                  : 'text-deck-text-muted hover:text-deck-text-secondary'
              }`}
            >
              {t.label}
              {data && t.key === tab && (
                <span className="ml-1.5 text-xs text-deck-text-muted">
                  {data.count}
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

      {!isLoading && !error && sorted.length === 0 && (
        <EmptyState
          icon="🏷️"
          title="No deals yet"
          description={
            tab === 'relevant'
              ? 'No relevant deals found. Try the "All" tab or configure your home airport in Settings.'
              : 'No deals found. RSS feeds may not have been ingested yet.'
          }
        />
      )}

      {sorted.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {sorted.map((deal) => (
              <DealCard
                key={deal.id}
                deal={deal}
                onDismiss={(id) => dismiss.mutate(id)}
                onRestore={(id) => restore.mutate(id)}
              />
            ))}
          </div>

          {/* Load more */}
          {data && data.count >= limit && (
            <div className="flex justify-center pt-4">
              <Button
                variant="secondary"
                onClick={() => setLimit((prev) => prev + 30)}
              >
                Load more deals
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
