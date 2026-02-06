import { useState, useCallback, useEffect, useRef } from 'react'
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
  const [activeIndex, setActiveIndex] = useState(-1)
  const listRef = useRef<HTMLUListElement>(null)

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

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(-1)
  }, [results])

  const selectAirport = (airport: AirportSearchResult) => {
    onChange(airport.code)
    setQuery(airport.code)
    setResults([])
    setShowDropdown(false)
    setActiveIndex(-1)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || results.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setActiveIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0))
        break
      case 'ArrowUp':
        e.preventDefault()
        setActiveIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1))
        break
      case 'Enter':
        e.preventDefault()
        if (activeIndex >= 0 && activeIndex < results.length) {
          selectAirport(results[activeIndex])
        }
        break
      case 'Escape':
        setShowDropdown(false)
        setActiveIndex(-1)
        break
    }
  }

  const inputId = `airport-input-${label.replace(/\s+/g, '-').toLowerCase()}`
  const listboxId = `${inputId}-listbox`

  return (
    <div>
      <label htmlFor={inputId} className="block text-sm text-deck-text-secondary mb-1">{label}</label>
      <div className="relative">
        <input
          id={inputId}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value.toUpperCase())
            setShowDropdown(true)
          }}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          role="combobox"
          aria-expanded={showDropdown && results.length > 0}
          aria-controls={listboxId}
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-option-${activeIndex}` : undefined}
          aria-autocomplete="list"
          className="w-full px-3 py-2 text-sm rounded-lg bg-deck-bg border border-deck-border text-deck-text-primary placeholder-deck-text-muted focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary font-mono min-h-[44px]"
        />
        {showDropdown && results.length > 0 && (
          <ul
            ref={listRef}
            id={listboxId}
            role="listbox"
            aria-label={`${label} results`}
            className="absolute z-10 w-full mt-1 bg-deck-surface border border-deck-border rounded-lg shadow-lg max-h-48 overflow-y-auto"
          >
            {results.map((airport, index) => (
              <li
                key={airport.code}
                id={`${listboxId}-option-${index}`}
                role="option"
                aria-selected={index === activeIndex}
              >
                <button
                  type="button"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => selectAirport(airport)}
                  className={`w-full text-left px-3 py-2 text-sm text-deck-text-primary min-h-[44px] ${
                    index === activeIndex
                      ? 'bg-deck-surface-hover'
                      : 'hover:bg-deck-surface-hover'
                  }`}
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
