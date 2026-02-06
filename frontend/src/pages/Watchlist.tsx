import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchSearchDefinitions,
  createSearchDefinition,
  deleteSearchDefinition,
  refreshPrices,
  searchAirports,
  SearchDefinition,
  AirportSearchResult,
} from '../api/client'
import { PageHeader, Card, Button, Input, EmptyState, Spinner, Badge } from '../components/shared'
import RouteCard from '../components/RouteCard'

// --- Airport Autocomplete ---

function AirportInput({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (code: string) => void
}) {
  const [query, setQuery] = useState(value)
  const [results, setResults] = useState<AirportSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  const search = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([])
      return
    }
    const data = await searchAirports(q)
    setResults(data)
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => search(query), 200)
    return () => clearTimeout(timer)
  }, [query, search])

  return (
    <div>
      <label className="block text-sm text-deck-text-secondary mb-1">{label}</label>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value.toUpperCase())
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder="Search airports..."
          className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary font-mono"
        />
        {showDropdown && results.length > 0 && (
          <ul className="absolute z-10 w-full mt-1 bg-deck-surface border border-deck-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {results.map((airport) => (
              <li key={airport.code}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange(airport.code)
                    setQuery(airport.code)
                    setResults([])
                    setShowDropdown(false)
                  }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-deck-surface-hover text-deck-text-primary"
                >
                  <span className="font-mono font-semibold">{airport.code}</span>
                  <span className="text-deck-text-secondary ml-2">
                    {airport.city}, {airport.country}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// --- Add Route Form ---

const CABIN_OPTIONS = [
  { value: 'economy', label: 'Economy' },
  { value: 'premium_economy', label: 'Premium Economy' },
  { value: 'business', label: 'Business' },
  { value: 'first', label: 'First' },
]

const STOPS_OPTIONS = [
  { value: 'any', label: 'Any stops' },
  { value: 'nonstop', label: 'Nonstop only' },
  { value: 'one_stop', label: '1 stop max' },
  { value: 'two_plus', label: '2+ stops' },
]

function AddRouteForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: Partial<SearchDefinition>) => void
  onCancel: () => void
}) {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [name, setName] = useState('')
  const [cabinClass, setCabinClass] = useState('economy')
  const [stopsFilter, setStopsFilter] = useState('any')
  const [adults, setAdults] = useState(2)
  const [children, setChildren] = useState(0)
  const [tripType, setTripType] = useState('round_trip')

  const canSubmit = origin.length === 3 && destination.length === 3

  return (
    <Card>
      <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-4">
        Add Route
      </h3>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <AirportInput label="Origin" value={origin} onChange={setOrigin} />
          <AirportInput label="Destination" value={destination} onChange={setDestination} />
        </div>

        <Input
          label="Name (optional)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Summer Japan trip"
        />

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Trip Type</label>
            <select
              value={tripType}
              onChange={(e) => setTripType(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              <option value="round_trip">Round trip</option>
              <option value="one_way">One way</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Cabin</label>
            <select
              value={cabinClass}
              onChange={(e) => setCabinClass(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              {CABIN_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Stops</label>
            <select
              value={stopsFilter}
              onChange={(e) => setStopsFilter(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              {STOPS_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Adults</label>
            <input
              type="number"
              min={1}
              max={9}
              value={adults}
              onChange={(e) => setAdults(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Children</label>
            <input
              type="number"
              min={0}
              max={9}
              value={children}
              onChange={(e) => setChildren(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <Button onClick={() => onSubmit({
            origin,
            destination,
            name: name || undefined,
            trip_type: tripType,
            cabin_class: cabinClass,
            stops_filter: stopsFilter,
            adults,
            children,
          })} disabled={!canSubmit}>
            Add Route
          </Button>
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
    </Card>
  )
}

// --- Watchlist Route Item ---

function WatchlistItem({
  route,
  onDelete,
  onRefresh,
}: {
  route: SearchDefinition
  onDelete: (id: number) => void
  onRefresh: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await onRefresh(route.id)
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div>
      <Card interactive onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="text-lg font-mono font-semibold text-deck-text-primary">
              {route.origin}
              <span className="text-deck-text-muted mx-1">&rarr;</span>
              {route.destination}
            </div>
            <Badge variant={route.is_active ? 'info' : 'normal'}>
              {route.is_active ? 'Active' : 'Paused'}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-deck-text-muted">
              {route.cabin_class} &middot; {route.stops_filter === 'any' ? 'Any stops' : route.stops_filter}
            </span>
            <span className={`text-deck-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}>
              &#9662;
            </span>
          </div>
        </div>
        {route.name && (
          <p className="text-sm text-deck-text-secondary mt-1">{route.name}</p>
        )}
      </Card>

      {expanded && (
        <div className="ml-4 mt-2 space-y-3">
          <RouteCard route={route} />
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={(e) => { e.stopPropagation(); handleRefresh() }}
              disabled={refreshing}
            >
              {refreshing ? 'Refreshing...' : 'Refresh prices'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => { e.stopPropagation(); onDelete(route.id) }}
              className="text-deal-above hover:text-deal-above"
            >
              Delete
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Main Watchlist Page ---

export default function Watchlist() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)
  const [showAll, setShowAll] = useState(false)

  const { data: routes, isLoading } = useQuery({
    queryKey: ['searchDefinitions', showAll],
    queryFn: () => fetchSearchDefinitions(!showAll),
  })

  const createMutation = useMutation({
    mutationFn: (data: Partial<SearchDefinition>) => createSearchDefinition(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['searchDefinitions'] })
      setShowAddForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSearchDefinition,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['searchDefinitions'] }),
  })

  const handleRefresh = (id: number) => {
    refreshPrices(id).then(() => {
      queryClient.invalidateQueries({ queryKey: ['stats', id] })
      queryClient.invalidateQueries({ queryKey: ['prices', id] })
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Watchlist"
        subtitle="Routes you're monitoring"
        actions={
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-deck-text-secondary">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
                className="rounded border-deck-border bg-deck-bg"
              />
              Show paused
            </label>
            <Button onClick={() => setShowAddForm(true)}>
              + Add route
            </Button>
          </div>
        }
      />

      {showAddForm && (
        <AddRouteForm
          onSubmit={(data) => createMutation.mutate(data)}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {createMutation.isError && (
        <p className="text-sm text-deal-above">
          Failed to create route: {createMutation.error instanceof Error ? createMutation.error.message : 'Unknown error'}
        </p>
      )}

      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {!isLoading && (!routes || routes.length === 0) && !showAddForm && (
        <EmptyState
          icon="👀"
          title="Nothing tracked yet"
          description="Add your first route to start monitoring prices."
          actionLabel="Add a route"
          onAction={() => setShowAddForm(true)}
        />
      )}

      {routes && routes.length > 0 && (
        <div className="space-y-3">
          {routes.map((route) => (
            <WatchlistItem
              key={route.id}
              route={route}
              onDelete={(id) => deleteMutation.mutate(id)}
              onRefresh={handleRefresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}
