import { useState, useCallback, useEffect } from 'react'
import { searchAirports, AirportSearchResult } from '../../api/client'

interface AirportInputProps {
  label: string
  value: string
  onChange: (code: string) => void
  placeholder?: string
}

export default function AirportInput({
  label,
  value,
  onChange,
  placeholder = 'Search airports...',
}: AirportInputProps) {
  const [query, setQuery] = useState(value)
  const [results, setResults] = useState<AirportSearchResult[]>([])
  const [showDropdown, setShowDropdown] = useState(false)

  // Sync external value changes
  useEffect(() => {
    setQuery(value)
  }, [value])

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
          placeholder={placeholder}
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
