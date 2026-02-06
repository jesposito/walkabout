import { useMemo } from 'react'
import { useAirports, formatAirport } from '../../hooks/useAirports'

interface AirportRouteProps {
  origin: string
  destination: string
  className?: string
}

/**
 * Displays a route like "AKL (Auckland) -> NRT (Tokyo)"
 */
export default function AirportRoute({ origin, destination, className = '' }: AirportRouteProps) {
  const codes = useMemo(() => [origin, destination].filter(Boolean), [origin, destination])
  useAirports(codes)

  return (
    <span className={`font-mono text-sm font-semibold text-deck-text-primary ${className}`}>
      {formatAirport(origin)}
      <span className="text-deck-text-muted mx-1">&rarr;</span>
      {formatAirport(destination)}
    </span>
  )
}
