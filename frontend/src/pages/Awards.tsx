import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchAwardSearches,
  createAwardSearch,
  deleteAwardSearch,
  toggleAwardSearch,
  pollAwardSearch,
  fetchLatestAwardResults,
  type AwardSearch,
  type AwardSearchCreate,
} from '../api/client'
import { PageHeader, Card, Button, Input, Badge, EmptyState, Spinner } from '../components/shared'

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
          <Input
            label="Origin"
            placeholder="AKL"
            value={form.origin}
            onChange={(e) => setForm({ ...form, origin: e.target.value })}
            maxLength={3}
          />
          <Input
            label="Destination"
            placeholder="SYD"
            value={form.destination}
            onChange={(e) => setForm({ ...form, destination: e.target.value })}
            maxLength={3}
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

  const handlePoll = () => {
    setPolling(true)
    onPoll(search.id)
    setTimeout(() => setPolling(false), 5000)
  }

  return (
    <div>
      <Card interactive onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-deck-text-primary truncate">
                {search.name || `${search.origin} → ${search.destination}`}
              </h3>
              <Badge variant={search.is_active ? 'info' : 'normal'}>
                {search.is_active ? 'Active' : 'Paused'}
              </Badge>
              <Badge variant="normal">{search.cabin_class}</Badge>
            </div>
            <p className="text-sm text-deck-text-secondary mt-1">
              <span className="font-mono">{search.origin}</span>
              <span className="text-deck-text-muted mx-1">&rarr;</span>
              <span className="font-mono">{search.destination}</span>
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

          <div className="flex gap-2">
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

  const deleteMutation = useMutation({
    mutationFn: deleteAwardSearch,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['awardSearches'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: toggleAwardSearch,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['awardSearches'] }),
  })

  const handlePoll = (id: number) => {
    pollAwardSearch(id).then(() => {
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ['awardLatest', id] })
        queryClient.invalidateQueries({ queryKey: ['awardSearches'] })
      }, 3000)
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <PageHeader title="Award Tracking" subtitle="Monitor award flight availability via Seats.aero" />
        <Button onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? 'Cancel' : '+ Track Route'}
        </Button>
      </div>

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
