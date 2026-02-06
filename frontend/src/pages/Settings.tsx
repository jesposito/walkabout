import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchSettings,
  updateSettings,
  searchAirports,
  testNotification,
  aiReviewSettings,
  aiReviewSettingsEstimate,
  fetchFeedSources,
  UserSettings,
  AirportSearchResult,
  SettingsReviewResult,
} from '../api/client'
import { PageHeader, Card, Button, Input, Spinner, ToggleSwitch, Badge, AIActionButton } from '../components/shared'
import { useAirports, formatAirport } from '../hooks/useAirports'

// --- Collapsible Section ---

function Section({
  title,
  icon,
  children,
  defaultOpen = false,
}: {
  title: string
  icon: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <Card aria-expanded={open}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center justify-between w-full text-left min-h-[44px]"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide">
            {title}
          </h3>
        </div>
        <span
          className={`text-deck-text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        >
          &#9662;
        </span>
      </button>
      {open && <div className="mt-4 space-y-4 border-t border-deck-border pt-4">{children}</div>}
    </Card>
  )
}

// --- Airport Multi-Select ---

function AirportSelect({
  selected,
  onChange,
  label,
}: {
  selected: string[]
  onChange: (codes: string[]) => void
  label: string
}) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AirportSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  useAirports(selected)

  const search = useCallback(
    async (q: string) => {
      if (q.length < 2) {
        setResults([])
        return
      }
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
      {/* Selected badges */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {selected.map((code) => (
            <span
              key={code}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-mono bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
            >
              {formatAirport(code)}
              <button
                type="button"
                onClick={() => onChange(selected.filter((c) => c !== code))}
                className="hover:text-danger min-w-[24px] min-h-[24px] flex items-center justify-center"
                aria-label={`Remove ${code}`}
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      )}
      {/* Search input */}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          placeholder="Search airports..."
          className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary"
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

// --- Select helper ---

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <div>
      <label className="block text-sm text-deck-text-secondary mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

// --- Main Settings Page ---

const REGIONS = [
  { value: 'Oceania', label: 'Oceania' },
  { value: 'North America', label: 'North America' },
  { value: 'Europe', label: 'Europe' },
  { value: 'Asia', label: 'Asia' },
  { value: 'South America', label: 'South America' },
  { value: 'Africa', label: 'Africa' },
]

const CURRENCIES = [
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
  { value: 'GBP', label: 'GBP' },
  { value: 'CAD', label: 'CAD' },
  { value: 'AUD', label: 'AUD' },
  { value: 'NZD', label: 'NZD' },
  { value: 'SGD', label: 'SGD' },
  { value: 'JPY', label: 'JPY' },
]

const PROVIDERS = [
  { value: 'none', label: 'None (in-app only)' },
  { value: 'ntfy_sh', label: 'ntfy.sh (public)' },
  { value: 'ntfy_self', label: 'ntfy (self-hosted)' },
  { value: 'discord', label: 'Discord webhook' },
]

const AI_PROVIDERS = [
  { value: 'none', label: 'None (basic mode)' },
  { value: 'anthropic', label: 'Anthropic (Claude)' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'gemini', label: 'Google (Gemini)' },
  { value: 'ollama', label: 'Ollama (local)' },
  { value: 'openai_compatible', label: 'OpenAI-Compatible' },
]

const TIMEZONES = [
  { value: 'America/New_York', label: 'Eastern (ET)' },
  { value: 'America/Chicago', label: 'Central (CT)' },
  { value: 'America/Denver', label: 'Mountain (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific (PT)' },
  { value: 'Pacific/Honolulu', label: 'Hawaii (HT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST)' },
  { value: 'Pacific/Auckland', label: 'Auckland (NZST)' },
]

export default function Settings() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<Partial<UserSettings>>({})
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [testMsg, setTestMsg] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const initialLoadRef = useRef(true)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchSettings,
  })

  // Sync form state when settings load
  useEffect(() => {
    if (settings) {
      setForm(settings)
      // Mark initial load complete after a tick so the first setForm doesn't trigger auto-save
      setTimeout(() => { initialLoadRef.current = false }, 100)
    }
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: (updates: Partial<UserSettings>) => updateSettings(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    },
    onError: () => {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    },
  })

  // Auto-save with debounce
  const autoSave = useCallback((updatedForm: Partial<UserSettings>) => {
    if (initialLoadRef.current) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    setSaveStatus('saving')
    debounceRef.current = setTimeout(() => {
      saveMutation.mutate(updatedForm)
    }, 800)
  }, [saveMutation])

  const update = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value }
      autoSave(next)
      return next
    })
  }

  const handleTestNotification = async () => {
    setTestMsg('Sending...')
    try {
      const result = await testNotification()
      setTestMsg(result.success ? 'Sent!' : result.message)
    } catch {
      setTestMsg('Failed to send')
    }
    setTimeout(() => setTestMsg(null), 3000)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  const provider = (form.notification_provider as string) || 'none'
  const aiProvider = (form.ai_provider as string) || 'none'

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Configure your preferences"
        actions={
          <span className={`text-sm transition-opacity ${saveStatus === 'idle' ? 'opacity-0' : 'opacity-100'}`} aria-live="polite">
            {saveStatus === 'saving' && <span className="text-deck-text-muted">Saving...</span>}
            {saveStatus === 'saved' && <span className="text-deal-hot">Saved</span>}
            {saveStatus === 'error' && <span className="text-danger">Save failed</span>}
          </span>
        }
      />

      {/* Location */}
      <Section title="Location & Destinations" icon="📍" defaultOpen>
        <AirportSelect
          label="Home Airports"
          selected={form.home_airports || []}
          onChange={(codes) => update('home_airports', codes)}
        />
        <div className="grid grid-cols-2 gap-4">
          <Select
            label="Region"
            value={form.home_region || 'Oceania'}
            onChange={(v) => update('home_region', v)}
            options={REGIONS}
          />
          <Select
            label="Currency"
            value={form.preferred_currency || 'NZD'}
            onChange={(v) => update('preferred_currency', v)}
            options={CURRENCIES}
          />
        </div>
        <AirportSelect
          label="Dream Destinations"
          selected={form.watched_destinations || []}
          onChange={(codes) => update('watched_destinations', codes)}
        />
      </Section>

      {/* Notifications */}
      <Section title="Notifications" icon="🔔">
        <ToggleSwitch
          checked={form.notifications_enabled || false}
          onChange={(v) => update('notifications_enabled', v)}
          label="Enable notifications"
          description="Receive alerts for deals, trip matches, and system events"
        />

        {form.notifications_enabled && (
          <>
            <Select
              label="Provider"
              value={provider}
              onChange={(v) => update('notification_provider', v)}
              options={PROVIDERS}
            />

            {provider === 'ntfy_sh' && (
              <Input
                label="ntfy.sh Topic"
                value={form.notification_ntfy_topic || ''}
                onChange={(e) => update('notification_ntfy_topic', e.target.value)}
                placeholder="walkabout-deals"
              />
            )}
            {provider === 'ntfy_self' && (
              <>
                <Input
                  label="ntfy Server URL"
                  value={form.notification_ntfy_url || ''}
                  onChange={(e) => update('notification_ntfy_url', e.target.value)}
                  placeholder="http://ntfy.example.com"
                />
                <Input
                  label="Topic"
                  value={form.notification_ntfy_topic || ''}
                  onChange={(e) => update('notification_ntfy_topic', e.target.value)}
                  placeholder="walkabout-deals"
                />
              </>
            )}
            {provider === 'discord' && (
              <Input
                label="Discord Webhook URL"
                type="password"
                value={form.notification_discord_webhook || ''}
                onChange={(e) => update('notification_discord_webhook', e.target.value)}
                placeholder="https://discord.com/api/webhooks/..."
              />
            )}

            {provider !== 'none' && (
              <div className="flex items-center gap-2">
                <Button variant="secondary" size="sm" onClick={handleTestNotification}>
                  Test notification
                </Button>
                {testMsg && (
                  <span className="text-xs text-deck-text-secondary">{testMsg}</span>
                )}
              </div>
            )}

            <div className="space-y-3 pt-2">
              <p className="text-xs text-deck-text-muted uppercase tracking-wide">Notify me about</p>
              <ToggleSwitch
                checked={form.notify_deals ?? true}
                onChange={(v) => update('notify_deals', v)}
                label="Deal alerts"
              />
              <ToggleSwitch
                checked={form.notify_trip_matches ?? true}
                onChange={(v) => update('notify_trip_matches', v)}
                label="Trip plan matches"
              />
              <ToggleSwitch
                checked={form.notify_route_updates ?? true}
                onChange={(v) => update('notify_route_updates', v)}
                label="Route price updates"
              />
              <ToggleSwitch
                checked={form.notify_system ?? true}
                onChange={(v) => update('notify_system', v)}
                label="System alerts"
              />
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2">
              <Select
                label="Timezone"
                value={form.timezone || 'America/New_York'}
                onChange={(v) => update('timezone', v)}
                options={TIMEZONES}
              />
              <Select
                label="Cooldown"
                value={String(form.notification_cooldown_minutes ?? 60)}
                onChange={(v) => update('notification_cooldown_minutes', Number(v))}
                options={[
                  { value: '30', label: '30 minutes' },
                  { value: '60', label: '1 hour' },
                  { value: '120', label: '2 hours' },
                  { value: '360', label: '6 hours' },
                  { value: '1440', label: '24 hours' },
                ]}
              />
            </div>
          </>
        )}
      </Section>

      {/* Monitoring */}
      <Section title="Monitoring & Frequency" icon="🔄">
        <p className="text-xs text-deck-text-muted">
          Control how often Walkabout checks for deals and price updates. These apply to notification cooldowns &mdash; how long to wait after sending a notification before sending another for the same category.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Select
            label="Deal alert cooldown"
            value={String(form.deal_cooldown_minutes ?? 60)}
            onChange={(v) => update('deal_cooldown_minutes', Number(v))}
            options={[
              { value: '15', label: '15 minutes' },
              { value: '30', label: '30 minutes' },
              { value: '60', label: '1 hour' },
              { value: '120', label: '2 hours' },
              { value: '360', label: '6 hours' },
              { value: '720', label: '12 hours' },
            ]}
          />
          <Select
            label="Trip match cooldown"
            value={String(form.trip_cooldown_hours ?? 6)}
            onChange={(v) => update('trip_cooldown_hours', Number(v))}
            options={[
              { value: '1', label: '1 hour' },
              { value: '3', label: '3 hours' },
              { value: '6', label: '6 hours' },
              { value: '12', label: '12 hours' },
              { value: '24', label: '24 hours' },
            ]}
          />
          <Select
            label="Route update cooldown"
            value={String(form.route_cooldown_hours ?? 24)}
            onChange={(v) => update('route_cooldown_hours', Number(v))}
            options={[
              { value: '6', label: '6 hours' },
              { value: '12', label: '12 hours' },
              { value: '24', label: '24 hours' },
              { value: '48', label: '2 days' },
              { value: '168', label: '1 week' },
            ]}
          />
        </div>

        <div className="border-t border-deck-border pt-4 space-y-3">
          <ToggleSwitch
            checked={form.daily_digest_enabled ?? false}
            onChange={(v) => update('daily_digest_enabled', v)}
            label="Daily digest"
            description="Receive a summary of deals and price changes once a day instead of instant alerts"
          />
          {form.daily_digest_enabled && (
            <Select
              label="Send digest at"
              value={String(form.daily_digest_hour ?? 8)}
              onChange={(v) => update('daily_digest_hour', Number(v))}
              options={[
                { value: '6', label: '6:00 AM' },
                { value: '7', label: '7:00 AM' },
                { value: '8', label: '8:00 AM' },
                { value: '9', label: '9:00 AM' },
                { value: '12', label: '12:00 PM' },
                { value: '18', label: '6:00 PM' },
                { value: '20', label: '8:00 PM' },
              ]}
            />
          )}
        </div>
      </Section>

      {/* Feed Sources */}
      <FeedSourcesSection
        enabledSources={form.enabled_feed_sources ?? null}
        onChange={(sources) => update('enabled_feed_sources', sources)}
      />

      {/* API Keys */}
      <Section title="AI & API Keys" icon="🔑">
        <Select
          label="AI Provider"
          value={aiProvider}
          onChange={(v) => update('ai_provider', v)}
          options={AI_PROVIDERS}
        />

        {aiProvider !== 'none' && aiProvider !== 'ollama' && (
          <Input
            label="AI API Key"
            type="password"
            value={form.ai_api_key || ''}
            onChange={(e) => update('ai_api_key', e.target.value)}
            placeholder="sk-..."
          />
        )}
        {(aiProvider === 'ollama' || aiProvider === 'openai_compatible') && (
          <Input
            label="API URL"
            value={form.ai_ollama_url || ''}
            onChange={(e) => update('ai_ollama_url', e.target.value)}
            placeholder="http://localhost:11434"
          />
        )}
        {aiProvider !== 'none' && (
          <Input
            label="Model"
            value={form.ai_model || ''}
            onChange={(e) => update('ai_model', e.target.value)}
            placeholder={
              aiProvider === 'anthropic' ? 'claude-3-haiku' :
              aiProvider === 'openai' ? 'gpt-4o-mini' :
              aiProvider === 'gemini' ? 'gemini-1.5-flash' :
              aiProvider === 'ollama' ? 'llama3.2' : 'model-name'
            }
          />
        )}

        <div className="border-t border-deck-border pt-4 space-y-4">
          <p className="text-xs text-deck-text-muted uppercase tracking-wide">Data source API keys</p>
          <Input
            label="Seats.aero API Key (Award Flights)"
            type="password"
            value={form.seats_aero_api_key || ''}
            onChange={(e) => update('seats_aero_api_key', e.target.value)}
            placeholder="Partner API key"
          />
          <Input
            label="SerpAPI Key (Google Flights)"
            type="password"
            value={form.serpapi_key || ''}
            onChange={(e) => update('serpapi_key', e.target.value)}
            placeholder="API key"
          />
          <Input
            label="Amadeus Client ID"
            type="password"
            value={form.amadeus_client_id || ''}
            onChange={(e) => update('amadeus_client_id', e.target.value)}
            placeholder="Client ID"
          />
          <Input
            label="Amadeus Client Secret"
            type="password"
            value={form.amadeus_client_secret || ''}
            onChange={(e) => update('amadeus_client_secret', e.target.value)}
            placeholder="Client secret"
          />
        </div>
      </Section>

      {/* AI Settings Review */}
      <SettingsReview />
    </div>
  )
}

// --- Feed Source Labels ---

const FEED_SOURCE_LABELS: Record<string, string> = {
  secret_flying: 'Secret Flying',
  omaat: 'OMAAT',
  the_points_guy: 'The Points Guy',
  the_flight_deal: 'The Flight Deal',
  fly4free: 'Fly4Free',
  travel_free: 'Travel Free',
  holiday_pirates: 'Holiday Pirates',
  australian_frequent_flyer: 'Aus Frequent Flyer',
  point_hacks: 'Point Hacks',
  ozbargain: 'OzBargain',
  cheapies_nz: 'Cheapies NZ',
  beat_that_flight: 'Beat That Flight',
}

const FEED_REGION_COLORS: Record<string, string> = {
  Global: 'text-accent-primary',
  US: 'text-blue-400',
  'AU/NZ': 'text-green-400',
  AU: 'text-green-400',
  NZ: 'text-green-400',
}

function FeedSourcesSection({
  enabledSources,
  onChange,
}: {
  enabledSources: string[] | null
  onChange: (sources: string[] | null) => void
}) {
  const { data: feedData } = useQuery({
    queryKey: ['feed-sources'],
    queryFn: fetchFeedSources,
  })

  if (!feedData) return null

  const isAuto = enabledSources === null
  const currentEnabled = isAuto
    ? new Set(feedData.sources.filter(s => s.enabled).map(s => s.id))
    : new Set(enabledSources)

  const toggleSource = (id: string) => {
    const next = new Set(currentEnabled)
    if (next.has(id)) {
      next.delete(id)
    } else {
      next.add(id)
    }
    onChange(Array.from(next))
  }

  const resetToAuto = () => {
    onChange(null as unknown as string[])
  }

  return (
    <Section title="Feed Sources" icon="📡">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs text-deck-text-muted">
          {isAuto
            ? `Auto-selected for ${feedData.user_region || 'your region'}`
            : `${currentEnabled.size} of ${feedData.sources.length} feeds enabled`}
        </p>
        {!isAuto && (
          <button
            type="button"
            onClick={resetToAuto}
            className="text-xs text-accent-primary hover:underline"
          >
            Reset to recommended
          </button>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {feedData.sources.map((source) => (
          <label
            key={source.id}
            className="flex items-center gap-2 p-2 rounded-lg hover:bg-deck-surface-hover cursor-pointer"
          >
            <input
              type="checkbox"
              checked={currentEnabled.has(source.id)}
              onChange={() => toggleSource(source.id)}
              className="rounded border-deck-border text-accent-primary focus:ring-accent-primary/50"
            />
            <span className="text-sm text-deck-text-primary">
              {FEED_SOURCE_LABELS[source.id] || source.id}
            </span>
            <span className={`text-[10px] ml-auto ${FEED_REGION_COLORS[source.region] || 'text-deck-text-muted'}`}>
              {source.region}
            </span>
          </label>
        ))}
      </div>
    </Section>
  )
}

function scoreToVariant(score: number): 'hot' | 'good' | 'decent' | 'normal' {
  if (score >= 8) return 'hot'
  if (score >= 6) return 'good'
  if (score >= 4) return 'decent'
  return 'normal'
}

function SettingsReview() {
  return (
    <Card className="space-y-3">
      <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide">
        AI Configuration Review
      </h3>
      <AIActionButton<SettingsReviewResult>
        label="Review my setup"
        action={aiReviewSettings}
        fetchEstimate={aiReviewSettingsEstimate}
        renderResult={(r) => (
          <div className="space-y-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={scoreToVariant(r.score)}>
                Score: {r.score}/10
              </Badge>
              <p className="text-sm text-deck-text-primary break-words min-w-0 flex-1">{r.assessment}</p>
            </div>
            {r.suggestions.length > 0 && (
              <div className="space-y-2">
                {r.suggestions.map((s: { title: string; description: string }, i: number) => (
                  <div key={i} className="p-2 rounded bg-deck-bg">
                    <p className="text-sm font-medium text-deck-text-primary">{s.title}</p>
                    <p className="text-xs text-deck-text-secondary mt-0.5 break-words">{s.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      />
    </Card>
  )
}
