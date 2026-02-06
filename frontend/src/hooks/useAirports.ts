import { useEffect, useRef, useState } from 'react'
import { lookupAirports } from '../api/client'

// Module-level cache shared across all hook instances
const airportCache: Record<string, { city: string; country: string }> = {}
let pendingCodes = new Set<string>()
let batchTimer: ReturnType<typeof setTimeout> | null = null
let batchCallbacks: Array<() => void> = []

function flushBatch() {
  const codes = [...pendingCodes]
  const cbs = [...batchCallbacks]
  pendingCodes = new Set()
  batchCallbacks = []
  batchTimer = null

  if (codes.length === 0) return

  lookupAirports(codes).then((result) => {
    for (const [code, info] of Object.entries(result)) {
      airportCache[code] = info
    }
    // Mark codes not found so we don't re-fetch
    for (const code of codes) {
      if (!airportCache[code]) {
        airportCache[code] = { city: code, country: '' }
      }
    }
    cbs.forEach((cb) => cb())
  }).catch(() => {
    cbs.forEach((cb) => cb())
  })
}

function requestCodes(codes: string[], onReady: () => void) {
  const missing = codes.filter((c) => c && !airportCache[c])
  if (missing.length === 0) {
    return // All cached
  }
  for (const c of missing) pendingCodes.add(c)
  batchCallbacks.push(onReady)
  if (!batchTimer) {
    batchTimer = setTimeout(flushBatch, 50)
  }
}

/**
 * Format an airport code with its city name: "AKL (Auckland)"
 * Returns just the code if not yet resolved.
 */
export function formatAirport(code: string): string {
  if (!code) return ''
  const info = airportCache[code.toUpperCase()]
  if (info && info.city !== code.toUpperCase()) {
    return `${code} (${info.city})`
  }
  return code
}

/**
 * Get city name for an airport code, or the code itself if not found.
 */
export function getCity(code: string): string {
  if (!code) return ''
  const info = airportCache[code.toUpperCase()]
  if (info && info.city !== code.toUpperCase()) return info.city
  return code
}

/**
 * Hook that ensures airport data is loaded for the given codes.
 * Returns a version counter that increments when new data arrives.
 */
export function useAirports(codes: string[]): number {
  const [version, setVersion] = useState(0)
  const codesRef = useRef(codes)
  codesRef.current = codes

  useEffect(() => {
    const uniqueCodes = [...new Set(codes.filter(Boolean).map((c) => c.toUpperCase()))]
    if (uniqueCodes.length === 0) return

    // Check if all are already cached
    const allCached = uniqueCodes.every((c) => airportCache[c])
    if (allCached) return

    requestCodes(uniqueCodes, () => {
      setVersion((v) => v + 1)
    })
  }, [codes.join(',')])

  return version
}
