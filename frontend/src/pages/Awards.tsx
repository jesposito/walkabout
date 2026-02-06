import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAwardSearches,
  createAwardSearch,
  deleteAwardSearch,
  toggleAwardSearch,
  pollAwardSearch,
  fetchLatestAwardResults,
  fetchSystemStatus,
  aiFindPatterns,
  aiPatternsEstimate,
  aiMileValue,
  aiMileValueEstimate,
  type AwardSearch,
  type AwardSearchCreate,
  type AwardPatternResult,
  type MileValueResult,
  type MileValueRequest,
  type TokenEstimate,
} from '../api/client'
import { PageHeader, Card, Button, Input, Badge, EmptyState, Spinner, AirportInput, AirportRoute } from '../components/shared'
import { useAirports, formatAirport } from '../hooks/useAirports'
import { useAIAction } from '../hooks/useAIAction'

const CABIN_OPTIONS = [
  { value: 'economy', label: 'Economy' },
  { value: 'premium_economy', label: 'Premium Economy' },
  { value: 'business', label: 'Business' },
  { value: 'first', label: 'First' },
]

const PROGRAM_OPTIONS = [
  { value: '', label: 'All Programs' },
  { value: 'united', label: 'United MileagePlus' },
  { value: 'aeroplan', label: 'Air Canada Aeroplan' },
  { value: 'qantas_ff', label: 'Qantas Frequent Flyer' },
  { value: 'velocity', label: 'Velocity Frequent Flyer' },
  { value: 'flying_blue', label: 'Flying Blue' },
  { value: 'alaska', label: 'Alaska Mileage Plan' },
  { value: 'aadvantage', label: 'American AAdvantage' },
  { value: 'virgin_atlantic', label: 'Virgin Atlantic' },
]

function AddAwardForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<AwardSearchCreate>({
    origin: '',
    destination: '',
    cabin_class: 'business',
    program: null,
    min_seats: 1,
    direct_only: false,
    notify_on_change: true,
    date_start: null,
    date_end: null,
  })

  const createMutation = useMutation({
    mutationFn: createAwardSearch,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['awardSearches'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.origin || !form.destination) return
    createMutation.mutate({
      ...form,
      origin: form.origin.toUpperCase(),
      destination: form.destination.toUpperCase(),
      program: form.program || undefined,
    })
  }

  return (
    <Card>
      <form onSubmit={handleSubmit} className="space-y-4">
        <h3 className="text-base font-semibold text-deck-text-primary">Track Award Availability</h3>

        <div className="grid grid-cols-2 gap-3">
          <AirportInput
            label="Origin"
            placeholder="Search airports..."
            value={form.origin}
            onChange={(code) => setForm({ ...form, origin: code })}
          />
          <AirportInput
            label="Destination"
            placeholder="Search airports..."
            value={form.destination}
            onChange={(code) => setForm({ ...form, destination: code })}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-deck-text-muted uppercase mb-1">Cabin</label>
            <select
              value={form.cabin_class}
              onChange={(e) => setForm({ ...form, cabin_class: e.target.value })}
              className="w-full bg-deck-bg border border-deck-border rounded-md px-3 py-2 text-deck-text-primary text-sm"
            >
              {CABIN_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-deck-text-muted uppercase mb-1">Program</label>
            <select
              value={form.program || ''}
              onChange={(e) => setForm({ ...form, program: e.target.value || null })}
              className="w-full bg-deck-bg border border-deck-border rounded-md px-3 py-2 text-deck-text-primary text-sm"
            >
              {PROGRAM_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Search From"
            type="date"
            value={form.date_start || ''}
            onChange={(e) => setForm({ ...form, date_start: e.target.value || null })}
          />
          <Input
            label="Search To"
            type="date"
            value={form.date_end || ''}
            onChange={(e) => setForm({ ...form, date_end: e.target.value || null })}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Min Seats"
            type="number"
            value={form.min_seats?.toString() || '1'}
            onChange={(e) => setForm({ ...form, min_seats: parseInt(e.target.value) || 1 })}
          />
          <div className="flex items-end gap-4 pb-1">
            <label className="flex items-center gap-2 text-sm text-deck-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={form.direct_only}
                onChange={(e) => setForm({ ...form, direct_only: e.target.checked })}
                className="accent-deck-deal"
              />
              Direct only
            </label>
          </div>
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={createMutation.isPending || !form.origin || !form.destination}>
            {createMutation.isPending ? 'Creating...' : 'Track Route'}
          </Button>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
        </div>
      </form>
    </Card>
  )
}

function AwardResultsList({ searchId }: { searchId: number }) {
  const { data } = useQuery({
    queryKey: ['awardLatest', searchId],
    queryFn: () => fetchLatestAwardResults(searchId),
  })

  if (!data || !data.results || data.results.length === 0) {
    return <p className="text-sm text-deck-text-muted">No results yet. Poll to fetch availability.</p>
  }

  return (
    <div className="space-y-1">
      <p className="text-xs text-deck-text-muted uppercase tracking-wide">
        {data.results.length} options found
        {data.observation && (
          <span> &middot; {new Date(data.observation.observed_at).toLocaleString('en-NZ')}</span>
        )}
      </p>
      <div className="max-h-60 overflow-y-auto space-y-1">
        {(data.results as Array<{
          date: string; program: string; cabin: string;
          miles: number; seats: number; direct: boolean; airline: string;
        }>).slice(0, 20).map((r, i) => (
          <div key={i} className="flex items-center justify-between text-sm py-1 px-2 rounded bg-deck-bg">
            <div className="flex items-center gap-2">
              <span className="text-deck-text-muted text-xs w-20">{r.date}</span>
              <Badge variant="normal">{r.program}</Badge>
              {r.direct && <Badge variant="info">Direct</Badge>}
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-deck-deal font-medium">
                {r.miles?.toLocaleString()} mi
              </span>
              {r.seats > 0 && (
                <span className="text-xs text-deck-text-muted">{r.seats} seat{r.seats !== 1 ? 's' : ''}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AwardSearchTitle({ search }: { search: AwardSearch }) {
  useAirports([search.origin, search.destination])
  return (
    <h3 className="text-base font-semibold text-deck-text-primary truncate">
      {search.name || `${formatAirport(search.origin)} \u2192 ${formatAirport(search.destination)}`}
    </h3>
  )
}

// --- AI Action Button (same pattern as TripPlans) ---

function formatEstimate(estimate: TokenEstimate | null): string {
  if (!estimate) return ''
  const totalTokens = estimate.input_tokens_est + estimate.output_tokens_est
  const cost = estimate.cost_est_usd
  if (cost < 0.001) return `~${totalTokens} tokens`
  return `~${totalTokens} tokens (~$${cost.toFixed(3)})`
}

function AIActionButton<T>({
  label,
  action,
  fetchEstimate,
  onSuccess,
  renderResult,
}: {
  label: string
  action: () => Promise<T>
  fetchEstimate?: () => Promise<TokenEstimate>
  onSuccess?: (result: T) => void
  renderResult: (result: T) => React.ReactNode
}) {
  const ai = useAIAction<T>({ action, fetchEstimate, onSuccess })

  useEffect(() => {
    if (fetchEstimate && !ai.estimate && !ai.estimateLoading) {
      ai.loadEstimate()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={(e) => { e.stopPropagation(); ai.execute() }}
          disabled={ai.loading}
        >
          {ai.loading ? (
            <span className="flex items-center gap-1.5">
              <Spinner size="sm" />
              Thinking...
            </span>
          ) : (
            label
          )}
        </Button>
        {ai.estimate && !ai.result && !ai.loading && (
          <span className="text-xs text-deck-text-muted">
            {formatEstimate(ai.estimate)}
          </span>
        )}
      </div>

      {ai.error && (
        <p className="text-xs text-deal-above">{ai.error}</p>
      )}

      {ai.result && (
        <div className="p-3 rounded-lg bg-deck-bg border border-deck-border space-y-2">
          {renderResult(ai.result)}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); ai.execute() }}
              className="text-xs text-accent-primary hover:underline"
              disabled={ai.loading}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); ai.clear() }}
              className="text-xs text-deck-text-muted hover:text-deck-text-secondary"
            >
              Hide
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// --- Mile Value Form ---

function MileValueForm({ search }: { search: AwardSearch }) {
  const [miles, setMiles] = useState('')
  const [cashPrice, setCashPrice] = useState('')
  const [submitted, setSubmitted] = useState<MileValueRequest | null>(null)

  const program = search.program || 'unknown'

  const handleSubmit = () => {
    if (!miles || parseInt(miles) <= 0) return
    const request: MileValueRequest = {
      origin: search.origin,
      destination: search.destination,
      miles: parseInt(miles),
      program,
      cabin: search.cabin_class,
      cash_price: cashPrice ? parseFloat(cashPrice) : undefined,
    }
    setSubmitted(request)
  }

  if (!submitted) {
    return (
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <Input
            label="Miles required"
            type="number"
            value={miles}
            onChange={(e) => setMiles(e.target.value)}
            placeholder="e.g. 85000"
          />
          <Input
            label="Cash price (USD, optional)"
            type="number"
            value={cashPrice}
            onChange={(e) => setCashPrice(e.target.value)}
            placeholder="e.g. 3500"
          />
        </div>
        <Button variant="secondary" size="sm" onClick={handleSubmit} disabled={!miles || parseInt(miles) <= 0}>
          Evaluate value
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <AIActionButton<MileValueResult>
        label="Evaluate mile value"
        action={() => aiMileValue(submitted)}
        fetchEstimate={() => aiMileValueEstimate(submitted)}
        renderResult={(r) => (
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg font-mono font-bold text-deck-text-primary">
                {r.cents_per_mile.toFixed(1)} cpp
              </span>
              <Badge variant={
                r.rating === 'excellent' ? 'hot'
                : r.rating === 'good' ? 'good'
                : r.rating === 'fair' ? 'decent'
                : 'normal'
              }>
                {r.rating}
              </Badge>
            </div>
            {r.reasoning && <p className="text-xs text-deck-text-secondary">{r.reasoning}</p>}
            {r.benchmark && <p className="text-xs text-deck-text-muted mt-1">{r.benchmark}</p>}
          </div>
        )}
      />
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setSubmitted(null) }}
        className="text-xs text-deck-text-muted hover:text-deck-text-secondary"
      >
        Change inputs
      </button>
    </div>
  )
}

function AwardSearchCard({
  search,
  onDelete,
  onToggle,
  onPoll,
}: {
  search: AwardSearch
  onDelete: (id: number) => void
  onToggle: (id: number) => void
  onPoll: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [polling, setPolling] = useState(false)
  const [pollMsg, setPollMsg] = useState<string | null>(null)

  const handlePoll = async () => {
    setPolling(true)
    setPollMsg(null)
    try {
      const result = await pollAwardSearch(search.id)
      if (result.status === 'error') {
        setPollMsg(result.message || 'Poll failed. Check API key.')
      } else {
        setPollMsg(result.total_options ? `Found ${result.total_options} options` : 'Poll complete')
      }
    } catch {
      setPollMsg('Poll failed. Is the Seats.aero API key configured?')
    } finally {
      setPolling(false)
      onPoll(search.id)
      setTimeout(() => setPollMsg(null), 8000)
    }
  }

  return (
    <div>
      <Card interactive onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <AwardSearchTitle search={search} />
              <Badge variant={search.is_active ? 'info' : 'normal'}>
                {search.is_active ? 'Active' : 'Paused'}
              </Badge>
              <Badge variant="normal">{search.cabin_class}</Badge>
            </div>
            <p className="text-sm text-deck-text-secondary mt-1">
              <AirportRoute origin={search.origin} destination={search.destination} />
              {search.program && (
                <span className="text-deck-text-muted ml-2">&middot; {search.program}</span>
              )}
              {search.min_seats > 1 && (
                <span className="text-deck-text-muted ml-2">&middot; {search.min_seats}+ seats</span>
              )}
              {search.last_polled_at && (
                <span className="text-deck-text-muted ml-2">
                  &middot; Polled {new Date(search.last_polled_at).toLocaleDateString('en-NZ')}
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
          {search.date_start && (
            <div className="text-sm text-deck-text-secondary">
              Searching: {new Date(search.date_start).toLocaleDateString('en-NZ')} - {search.date_end ? new Date(search.date_end).toLocaleDateString('en-NZ') : '?'}
            </div>
          )}

          <AwardResultsList searchId={search.id} />

          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={handlePoll} disabled={polling}>
              {polling ? 'Polling...' : 'Poll now'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onToggle(search.id)}>
              {search.is_active ? 'Pause' : 'Resume'}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onDelete(search.id)}
              className="text-deal-above hover:text-deal-above"
            >
              Delete
            </Button>
            {pollMsg && (
              <span className="text-xs text-deck-text-secondary ml-auto">{pollMsg}</span>
            )}
          </div>

          {/* AI Intelligence */}
          <div className="space-y-2 pt-1">
            <p className="text-xs text-deck-text-muted uppercase tracking-wide">AI Intelligence</p>
            <div className="flex flex-col sm:flex-row gap-3">
              <AIActionButton<AwardPatternResult>
                label="Find sweet spots"
                action={() => aiFindPatterns(search.id)}
                fetchEstimate={() => aiPatternsEstimate(search.id)}
                renderResult={(r) => (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-xs text-deck-text-muted uppercase">Trend</p>
                      <Badge variant={
                        r.trend === 'improving' ? 'hot'
                        : r.trend === 'declining' ? 'normal'
                        : r.trend === 'stable' ? 'good'
                        : 'info'
                      }>
                        {r.trend.replace('_', ' ')}
                      </Badge>
                      {r.best_value_program && (
                        <span className="text-xs text-deck-text-secondary">
                          Best program: <span className="font-medium">{r.best_value_program}</span>
                        </span>
                      )}
                    </div>
                    {r.sweet_spots.length > 0 && (
                      <div>
                        <p className="text-xs text-deck-text-muted uppercase mb-1">Sweet Spots</p>
                        {r.sweet_spots.map((s, i) => (
                          <div key={i} className="text-xs text-deck-text-secondary mb-1">
                            <span className="font-medium text-deck-text-primary">{s.program}</span>: {s.insight}
                          </div>
                        ))}
                      </div>
                    )}
                    {r.timing && (
                      <p className="text-xs text-deck-text-secondary"><span className="font-medium">Timing:</span> {r.timing}</p>
                    )}
                    {r.recommendation && (
                      <p className="text-xs text-deck-text-secondary"><span className="font-medium">Recommendation:</span> {r.recommendation}</p>
                    )}
                  </div>
                )}
              />
            </div>
            <div className="pt-1">
              <p className="text-xs text-deck-text-muted uppercase tracking-wide mb-2">Mile Valuation</p>
              <MileValueForm search={search} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Awards() {
  const [showAdd, setShowAdd] = useState(false)
  const queryClient = useQueryClient()

  const { data: searches, isLoading } = useQuery({
    queryKey: ['awardSearches'],
    queryFn: () => fetchAwardSearches(),
  })

  const { data: status } = useQuery({
    queryKey: ['system-status'],
    queryFn: fetchSystemStatus,
    staleTime: 60000,
  })

  const seatsAeroAvailable = status?.data_sources?.['seats.aero']?.available ?? null

  const deleteMutation = useMutation({
    mutationFn: deleteAwardSearch,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['awardSearches'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: toggleAwardSearch,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['awardSearches'] }),
  })

  const handlePoll = (id: number) => {
    queryClient.invalidateQueries({ queryKey: ['awardLatest', id] })
    queryClient.invalidateQueries({ queryKey: ['awardSearches'] })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Award Tracking" subtitle="Monitor award flight availability via Seats.aero" />
        <Button onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? 'Cancel' : '+ Track Route'}
        </Button>
      </div>

      {seatsAeroAvailable === false && (
        <Card className="!border-deal-above/30 !bg-deal-above/5">
          <div className="flex items-start gap-3">
            <span className="text-deal-above text-lg shrink-0">!</span>
            <div>
              <p className="text-sm font-medium text-deck-text-primary">Seats.aero API key not configured</p>
              <p className="text-xs text-deck-text-secondary mt-0.5">
                Award tracking requires a Seats.aero Pro API key. Set <code className="font-mono bg-deck-bg px-1 rounded">SEATS_AERO_API_KEY</code> in your environment to enable polling.
              </p>
            </div>
          </div>
        </Card>
      )}

      {showAdd && <AddAwardForm onClose={() => setShowAdd(false)} />}

      {isLoading ? (
        <Spinner />
      ) : !searches || searches.length === 0 ? (
        <EmptyState
          title="No award searches"
          description="Track award availability on routes you care about. You'll need a Seats.aero Pro API key."
        />
      ) : (
        <div className="space-y-3">
          {searches.map((s) => (
            <AwardSearchCard
              key={s.id}
              search={s}
              onDelete={(id) => deleteMutation.mutate(id)}
              onToggle={(id) => toggleMutation.mutate(id)}
              onPoll={handlePoll}
            />
          ))}
        </div>
      )}
    </div>
  )
}
