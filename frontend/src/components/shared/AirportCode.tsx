import { useMemo } from 'react'
import { useAirports, formatAirport } from '../../hooks/useAirports'

interface AirportCodeProps {
  code: string
  showCity?: boolean
  className?: string
}

/**
 * Displays an airport code with its city name: "AKL (Auckland)"
 * Automatically fetches and caches airport data.
 */
export default function AirportCode({ code, showCity = true, className = '' }: AirportCodeProps) {
  const codes = useMemo(() => [code], [code])
  useAirports(codes)

  if (!code) return null

  const display = showCity ? formatAirport(code) : code

  return <span className={`font-mono ${className}`}>{display}</span>
}
