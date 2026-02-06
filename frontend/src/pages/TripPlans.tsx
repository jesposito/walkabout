import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchTripPlans,
  createTripPlan,
  deleteTripPlan,
  toggleTripPlan,
  searchTripPlan,
  fetchTripPlanMatches,
  searchAirports,
  TripPlan,
  TripPlanCreate,
  TripPlanMatch,
  AirportSearchResult,
} from '../api/client'
import { PageHeader, Card, Button, Input, EmptyState, Spinner, Badge, PriceDisplay } from '../components/shared'

// --- Multi-Airport Picker ---

function MultiAirportPicker({
  label,
  selected,
  onChange,
}: {
  label: string
  selected: string[]
  onChange: (codes: string[]) => void
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AirportSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  const search = useCallback(
    async (q: string) => {
      if (q.length < 2) { setResults([]); return }
      const data = await searchAirports(q)
      setResults(data.filter((a) => !selected.includes(a.code)))
    },
    [selected]
  )

  useEffect(() => {
    const timer = setTimeout(() => search(query), 200)
    return () => clearTimeout(timer)
  }, [query, search])

  return (
    <div>
      <label className="block text-sm text-deck-text-secondary mb-1">{label}</label>
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selected.map((code) => (
            <span
              key={code}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
            >
              {code}
              <button
                type="button"
                onClick={() => onChange(selected.filter((c) => c !== code))}
                className="hover:text-deal-above"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => { setQuery(e.target.value.toUpperCase()); setShowDropdown(true) }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder="Search airports..."
          className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 font-mono"
        />
        {showDropdown && results.length > 0 && (
          <ul className="absolute z-10 w-full mt-1 bg-deck-surface border border-deck-border rounded-lg shadow-lg max-h-48 overflow-y-auto">
            {results.map((airport) => (
              <li key={airport.code}>
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange([...selected, airport.code])
                    setQuery('')
                    setResults([])
                  }}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-deck-surface-hover text-deck-text-primary"
                >
                  <span className="font-mono font-semibold">{airport.code}</span>
                  <span className="text-deck-text-secondary ml-2">{airport.city}, {airport.country}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

// --- Add Trip Plan Form ---

function AddTripPlanForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: TripPlanCreate) => void
  onCancel: () => void
}) {
  const [name, setName] = useState('')
  const [origins, setOrigins] = useState<string[]>([])
  const [destinations, setDestinations] = useState<string[]>([])
  const [budgetMax, setBudgetMax] = useState('')
  const [budgetCurrency, setBudgetCurrency] = useState('NZD')
  const [adults, setAdults] = useState(2)
  const [children, setChildren] = useState(0)
  const [durationMin, setDurationMin] = useState(3)
  const [durationMax, setDurationMax] = useState(14)
  const [availableFrom, setAvailableFrom] = useState('')
  const [availableTo, setAvailableTo] = useState('')
  const [notes, setNotes] = useState('')

  const canSubmit = name.trim().length > 0 && (origins.length > 0 || destinations.length > 0)

  return (
    <Card>
      <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-4">
        New Trip Plan
      </h3>
      <div className="space-y-4">
        <Input
          label="Trip Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Japan Cherry Blossom 2026"
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <MultiAirportPicker label="From (origins)" selected={origins} onChange={setOrigins} />
          <MultiAirportPicker label="To (destinations)" selected={destinations} onChange={setDestinations} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Adults</label>
            <input
              type="number" min={1} max={9} value={adults}
              onChange={(e) => setAdults(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Children</label>
            <input
              type="number" min={0} max={9} value={children}
              onChange={(e) => setChildren(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Min days</label>
            <input
              type="number" min={1} max={90} value={durationMin}
              onChange={(e) => setDurationMin(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Max days</label>
            <input
              type="number" min={1} max={90} value={durationMax}
              onChange={(e) => setDurationMax(Number(e.target.value))}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Available from"
            type="date"
            value={availableFrom}
            onChange={(e) => setAvailableFrom(e.target.value)}
          />
          <Input
            label="Available to"
            type="date"
            value={availableTo}
            onChange={(e) => setAvailableTo(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Input
            label="Budget max"
            type="number"
            value={budgetMax}
            onChange={(e) => setBudgetMax(e.target.value)}
            placeholder="Optional"
          />
          <div>
            <label className="block text-sm text-deck-text-secondary mb-1">Currency</label>
            <select
              value={budgetCurrency}
              onChange={(e) => setBudgetCurrency(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              {['NZD','AUD','USD','EUR','GBP','SGD','JPY','CAD'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <Input
          label="Notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any additional details..."
        />

        <div className="flex gap-2 pt-2">
          <Button
            onClick={() => onSubmit({
              name: name.trim(),
              origins,
              destinations,
              travelers_adults: adults,
              travelers_children: children,
              trip_duration_min: durationMin,
              trip_duration_max: durationMax,
              available_from: availableFrom || null,
              available_to: availableTo || null,
              budget_max: budgetMax ? Number(budgetMax) : null,
              budget_currency: budgetCurrency,
              notes: notes || null,
            })}
            disabled={!canSubmit}
          >
            Create Trip Plan
          </Button>
          <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        </div>
      </div>
    </Card>
  )
}

// --- Match Card ---

function MatchCard({ match }: { match: TripPlanMatch }) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <div className="font-mono text-sm font-semibold text-deck-text-primary">
          {match.origin} &rarr; {match.destination}
        </div>
        <Badge variant={match.match_score >= 70 ? 'hot' : match.match_score >= 40 ? 'good' : 'decent'}>
          {Math.round(match.match_score)}% match
        </Badge>
      </div>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs text-deck-text-secondary">
            {match.departure_date}
            {match.return_date && ` - ${match.return_date}`}
          </p>
          {match.airline && (
            <p className="text-xs text-deck-text-muted">{match.airline} &middot; {match.stops === 0 ? 'Nonstop' : `${match.stops} stop${match.stops > 1 ? 's' : ''}`}</p>
          )}
          <p className="text-xs text-deck-text-muted capitalize">{match.source.replace(/_/g, ' ')}</p>
        </div>
        <div className="text-right">
          <PriceDisplay price={match.price_nzd} size="lg" />
          {match.booking_url && (
            <a
              href={match.booking_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent-primary hover:underline mt-1 block"
            >
              Book &rarr;
            </a>
          )}
        </div>
      </div>
    </Card>
  )
}

// --- Trip Plan Card ---

function TripPlanCard({
  plan,
  onDelete,
  onToggle,
  onSearch,
}: {
  plan: TripPlan
  onDelete: (id: number) => void
  onToggle: (id: number) => void
  onSearch: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [searching, setSearching] = useState(plan.search_in_progress)

  const { data: matches } = useQuery({
    queryKey: ['tripMatches', plan.id],
    queryFn: () => fetchTripPlanMatches(plan.id),
    enabled: expanded,
  })

  const handleSearch = async () => {
    setSearching(true)
    await onSearch(plan.id)
    setTimeout(() => setSearching(false), 3000)
  }

  return (
    <div>
      <Card interactive onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-deck-text-primary truncate">{plan.name}</h3>
              <Badge variant={plan.is_active ? 'info' : 'normal'}>
                {plan.is_active ? 'Active' : 'Paused'}
              </Badge>
              {plan.match_count > 0 && (
                <Badge variant="hot">{plan.match_count} matches</Badge>
              )}
            </div>
            <p className="text-sm text-deck-text-secondary mt-1">
              {plan.origins.length > 0 && (
                <span className="font-mono">{plan.origins.join(', ')}</span>
              )}
              {plan.origins.length > 0 && plan.destinations.length > 0 && (
                <span className="text-deck-text-muted mx-1">&rarr;</span>
              )}
              {plan.destinations.length > 0 && (
                <span className="font-mono">{plan.destinations.join(', ')}</span>
              )}
              {plan.budget_max && (
                <span className="text-deck-text-muted ml-2">
                  &middot; Budget: {plan.budget_currency} {plan.budget_max.toLocaleString()}
                </span>
              )}
            </p>
          </div>
          <span className={`text-deck-text-muted transition-transform ${expanded ? 'rotate-180' : ''}`}>
            &#9662;
          </span>
        </div>
      </Card>

      {expanded && (
        <div className="ml-4 mt-2 space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-deck-text-muted uppercase">Travelers</p>
              <p className="text-deck-text-primary">
                {plan.travelers_adults} adult{plan.travelers_adults !== 1 ? 's' : ''}
                {plan.travelers_children > 0 && `, ${plan.travelers_children} child${plan.travelers_children !== 1 ? 'ren' : ''}`}
              </p>
            </div>
            <div>
              <p className="text-xs text-deck-text-muted uppercase">Duration</p>
              <p className="text-deck-text-primary">{plan.trip_duration_min}-{plan.trip_duration_max} days</p>
            </div>
            {plan.available_from && (
              <div>
                <p className="text-xs text-deck-text-muted uppercase">Window</p>
                <p className="text-deck-text-primary">
                  {new Date(plan.available_from).toLocaleDateString('en-NZ', { month: 'short', day: 'numeric' })}
                  {plan.available_to && ` - ${new Date(plan.available_to).toLocaleDateString('en-NZ', { month: 'short', day: 'numeric' })}`}
                </p>
              </div>
            )}
            {plan.notes && (
              <div className="col-span-2 sm:col-span-4">
                <p className="text-xs text-deck-text-muted uppercase">Notes</p>
                <p className="text-deck-text-secondary">{plan.notes}</p>
              </div>
            )}
          </div>

          {/* Matches */}
          {matches && matches.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-deck-text-muted uppercase tracking-wide">Best Matches</p>
              {matches.slice(0, 5).map((match) => (
                <MatchCard key={match.id} match={match} />
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={handleSearch} disabled={searching}>
              {searching ? 'Searching...' : 'Search now'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onToggle(plan.id)}>
              {plan.is_active ? 'Pause' : 'Resume'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(plan.id)}
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

// --- Main Trip Plans Page ---

export default function TripPlans() {
  const queryClient = useQueryClient()
  const [showAddForm, setShowAddForm] = useState(false)

  const { data: plans, isLoading } = useQuery({
    queryKey: ['tripPlans'],
    queryFn: () => fetchTripPlans(),
  })

  const createMutation = useMutation({
    mutationFn: (data: TripPlanCreate) => createTripPlan(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tripPlans'] })
      setShowAddForm(false)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteTripPlan,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tripPlans'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: toggleTripPlan,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tripPlans'] }),
  })

  const handleSearch = (id: number) => {
    searchTripPlan(id)
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['tripMatches', id] })
      queryClient.invalidateQueries({ queryKey: ['tripPlans'] })
    }, 5000)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trip Plans"
        subtitle="Dream trips with flexible criteria"
        actions={
          <Button onClick={() => setShowAddForm(true)}>+ New trip plan</Button>
        }
      />

      {showAddForm && (
        <AddTripPlanForm
          onSubmit={(data) => createMutation.mutate(data)}
          onCancel={() => setShowAddForm(false)}
        />
      )}

      {createMutation.isError && (
        <p className="text-sm text-deal-above">
          Failed to create trip plan: {createMutation.error instanceof Error ? createMutation.error.message : 'Unknown error'}
        </p>
      )}

      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner size="lg" />
        </div>
      )}

      {!isLoading && (!plans || plans.length === 0) && !showAddForm && (
        <EmptyState
          icon="🗺️"
          title="No trip plans yet"
          description="Create a trip plan with flexible dates and destinations to find the best flights."
          actionLabel="New trip plan"
          onAction={() => setShowAddForm(true)}
        />
      )}

      {plans && plans.length > 0 && (
        <div className="space-y-3">
          {plans.map((plan) => (
            <TripPlanCard
              key={plan.id}
              plan={plan}
              onDelete={(id) => deleteMutation.mutate(id)}
              onToggle={(id) => toggleMutation.mutate(id)}
              onSearch={handleSearch}
            />
          ))}
        </div>
      )}
    </div>
  )
}
