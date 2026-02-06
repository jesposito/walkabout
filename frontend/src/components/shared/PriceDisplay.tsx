interface PriceDisplayProps {
  price: number
  currency?: string
  size?: 'sm' | 'md' | 'lg'
  trend?: 'up' | 'down' | 'stable' | null
  className?: string
}

const sizeClasses = {
  sm: 'text-price-sm',
  md: 'text-price-md',
  lg: 'text-price-lg',
}

const trendIcons = {
  up: '\u2191',
  down: '\u2193',
  stable: '\u2192',
}

const trendColors = {
  up: 'text-deal-above',
  down: 'text-deal-hot',
  stable: 'text-deck-text-secondary',
}

export default function PriceDisplay({
  price,
  currency = 'NZD',
  size = 'md',
  trend,
  className = '',
}: PriceDisplayProps) {
  const formatted = new Intl.NumberFormat('en-NZ', {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(price)

  return (
    <span className={`font-mono ${sizeClasses[size]} ${className}`}>
      <span className="text-deck-text-primary">{formatted}</span>
      <span className="text-deck-text-muted ml-1 text-xs">{currency}</span>
      {trend && (
        <span className={`ml-1 text-sm ${trendColors[trend]}`}>
          {trendIcons[trend]}
        </span>
      )}
    </span>
  )
}
