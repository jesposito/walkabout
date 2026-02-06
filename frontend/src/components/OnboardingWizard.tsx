import { useState, useCallback, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  updateSettings,
  searchAirports,
  AirportSearchResult,
  UserSettings,
} from '../api/client'
import { Button, Card } from './shared'

// --- Airport Picker for Onboarding ---

function AirportPicker({
  selected,
  onChange,
  placeholder,
}: {
  selected: string[]
  onChange: (codes: string[]) => void
  placeholder: string
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
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {selected.map((code) => (
            <span
              key={code}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-mono bg-accent-primary/20 text-accent-primary border border-accent-primary/30"
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
          placeholder={placeholder}
          className="w-full px-4 py-3 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary font-mono"
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
                  className="w-full text-left px-4 py-2.5 text-sm hover:bg-deck-surface-hover text-deck-text-primary"
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

// --- Step Components ---

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-1.5 flex-1 rounded-full transition-colors ${
            i <= current ? 'bg-accent-primary' : 'bg-deck-border'
          }`}
        />
      ))}
    </div>
  )
}

interface WizardState {
  homeAirports: string[]
  homeRegion: string
  currency: string
  watchedDestinations: string[]
  notificationsEnabled: boolean
  notificationProvider: string
  ntfyTopic: string
}

const REGIONS = [
  'Oceania', 'North America', 'Europe', 'Asia', 'South America', 'Africa',
]

const CURRENCIES = [
  { value: 'NZD', label: 'NZD - New Zealand Dollar' },
  { value: 'AUD', label: 'AUD - Australian Dollar' },
  { value: 'USD', label: 'USD - US Dollar' },
  { value: 'EUR', label: 'EUR - Euro' },
  { value: 'GBP', label: 'GBP - British Pound' },
  { value: 'SGD', label: 'SGD - Singapore Dollar' },
  { value: 'JPY', label: 'JPY - Japanese Yen' },
  { value: 'CAD', label: 'CAD - Canadian Dollar' },
]

// --- Main Wizard ---

interface OnboardingWizardProps {
  onComplete: () => void
}

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(0)
  const [state, setState] = useState<WizardState>({
    homeAirports: [],
    homeRegion: 'Oceania',
    currency: 'NZD',
    watchedDestinations: [],
    notificationsEnabled: false,
    notificationProvider: 'none',
    ntfyTopic: '',
  })

  const saveMutation = useMutation({
    mutationFn: (settings: Partial<UserSettings>) => updateSettings(settings),
    onSuccess: () => onComplete(),
  })

  const handleFinish = () => {
    saveMutation.mutate({
      home_airports: state.homeAirports,
      home_region: state.homeRegion,
      preferred_currency: state.currency,
      watched_destinations: state.watchedDestinations,
      notifications_enabled: state.notificationsEnabled,
      notification_provider: state.notificationsEnabled ? state.notificationProvider : 'none',
      notification_ntfy_topic: state.ntfyTopic || null,
    })
  }

  const update = <K extends keyof WizardState>(key: K, value: WizardState[K]) => {
    setState((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="fixed inset-0 bg-deck-bg/95 z-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-accent-primary font-mono tracking-wide">
            Walkabout
          </h1>
          <p className="text-deck-text-secondary mt-1">Let's get you set up</p>
        </div>

        <Card className="!p-6">
          <StepIndicator current={step} total={3} />

          {/* Step 1: Home Airport */}
          {step === 0 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-deck-text-primary">Where do you fly from?</h2>
                <p className="text-sm text-deck-text-secondary mt-1">
                  Add your home airport(s) so we can find relevant deals.
                </p>
              </div>

              <AirportPicker
                selected={state.homeAirports}
                onChange={(codes) => update('homeAirports', codes)}
                placeholder="Search for your home airport..."
              />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-deck-text-secondary mb-1">Region</label>
                  <select
                    value={state.homeRegion}
                    onChange={(e) => update('homeRegion', e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                  >
                    {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-deck-text-secondary mb-1">Currency</label>
                  <select
                    value={state.currency}
                    onChange={(e) => update('currency', e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                  >
                    {CURRENCIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button onClick={() => setStep(1)} disabled={state.homeAirports.length === 0}>
                  Next
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: Dream Destinations */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-deck-text-primary">Where do you dream of going?</h2>
                <p className="text-sm text-deck-text-secondary mt-1">
                  Add destinations you'd love to fly to. We'll watch for deals.
                </p>
              </div>

              <AirportPicker
                selected={state.watchedDestinations}
                onChange={(codes) => update('watchedDestinations', codes)}
                placeholder="Search for dream destinations..."
              />

              <div className="flex justify-between pt-2">
                <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setStep(2)}>Skip</Button>
                  <Button onClick={() => setStep(2)}>Next</Button>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Notifications */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-deck-text-primary">Stay in the loop</h2>
                <p className="text-sm text-deck-text-secondary mt-1">
                  Get notified when we find great deals. You can always change this later.
                </p>
              </div>

              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={state.notificationsEnabled}
                    onClick={() => update('notificationsEnabled', !state.notificationsEnabled)}
                    className={`relative inline-flex h-6 w-11 shrink-0 rounded-full border-2 border-transparent transition-colors ${
                      state.notificationsEnabled ? 'bg-accent-primary' : 'bg-deck-border'
                    }`}
                  >
                    <span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform transition ${
                      state.notificationsEnabled ? 'translate-x-5' : 'translate-x-0'
                    }`} />
                  </button>
                  <span className="text-sm text-deck-text-primary">Enable notifications</span>
                </label>

                {state.notificationsEnabled && (
                  <>
                    <div>
                      <label className="block text-sm text-deck-text-secondary mb-1">Provider</label>
                      <select
                        value={state.notificationProvider}
                        onChange={(e) => update('notificationProvider', e.target.value)}
                        className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                      >
                        <option value="ntfy_sh">ntfy.sh (easiest)</option>
                        <option value="ntfy_self">ntfy (self-hosted)</option>
                        <option value="discord">Discord webhook</option>
                      </select>
                    </div>

                    {(state.notificationProvider === 'ntfy_sh' || state.notificationProvider === 'ntfy_self') && (
                      <div>
                        <label className="block text-sm text-deck-text-secondary mb-1">ntfy Topic</label>
                        <input
                          type="text"
                          value={state.ntfyTopic}
                          onChange={(e) => update('ntfyTopic', e.target.value)}
                          placeholder="walkabout-deals"
                          className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                        />
                        <p className="text-xs text-deck-text-muted mt-1">
                          Choose a unique topic name. Subscribe at ntfy.sh/{state.ntfyTopic || 'your-topic'}
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>

              <div className="flex justify-between pt-2">
                <Button variant="ghost" onClick={() => setStep(1)}>Back</Button>
                <div className="flex gap-2">
                  {!state.notificationsEnabled && (
                    <Button variant="secondary" onClick={handleFinish} disabled={saveMutation.isPending}>
                      Skip & finish
                    </Button>
                  )}
                  <Button onClick={handleFinish} disabled={saveMutation.isPending}>
                    {saveMutation.isPending ? 'Saving...' : 'Finish setup'}
                  </Button>
                </div>
              </div>

              {saveMutation.isError && (
                <p className="text-sm text-deal-above">
                  Failed to save: {saveMutation.error instanceof Error ? saveMutation.error.message : 'Unknown error'}
                </p>
              )}
            </div>
          )}
        </Card>

        <p className="text-center text-xs text-deck-text-muted mt-4">
          You can change all of these in Settings later.
        </p>
      </div>
    </div>
  )
}
