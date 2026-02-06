import { Deal } from '../api/client'
import { Card, Badge, PriceDisplay, Button, AirportCode } from './shared'

interface DealCardProps {
  deal: Deal
  onDismiss?: (id: number) => void
  onRestore?: (id: number) => void
}

const SOURCE_LABELS: Record<string, string> = {
  secret_flying: 'Secret Flying',
  omaat: 'OMAAT',
  the_points_guy: 'The Points Guy',
  the_flight_deal: 'The Flight Deal',
  fly4free: 'Fly4Free',
  going: 'Going',
  holiday_pirates: 'Holiday Pirates',
  australian_frequent_flyer: 'AFF',
  point_hacks: 'Point Hacks',
  frugal_flyer: 'Frugal Flyer',
  secret_flying_eu: 'Secret Flying EU',
  travel_free: 'Travel Free',
  ozbargain: 'OzBargain',
  cheapies_nz: 'Cheapies NZ',
  beat_that_flight: 'Beat That Flight',
}

function ratingToBadgeVariant(label: string | null): 'hot' | 'good' | 'decent' | 'normal' | 'above' {
  if (!label) return 'normal'
  const lower = label.toLowerCase()
  if (lower.includes('hot')) return 'hot'
  if (lower.includes('good')) return 'good'
  if (lower.includes('decent')) return 'decent'
  if (lower.includes('above')) return 'above'
  return 'normal'
}

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 1) return 'just now'
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return '1 day ago'
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString('en-NZ', { month: 'short', day: 'numeric' })
}

export default function DealCard({ deal, onDismiss, onRestore }: DealCardProps) {
  const sourceName = SOURCE_LABELS[deal.source] || deal.source
  const variant = ratingToBadgeVariant(deal.rating_label)

  return (
    <Card className="space-y-3">
      {/* Header: source + rating + time */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-deck-text-muted truncate">{sourceName}</span>
          {deal.rating_label && (
            <Badge variant={variant}>{deal.rating_label}</Badge>
          )}
        </div>
        <span className="text-xs text-deck-text-muted whitespace-nowrap">
          {formatTimeAgo(deal.published_at)}
        </span>
      </div>

      {/* Route */}
      <div className="flex items-baseline gap-2">
        {deal.origin && (
          <AirportCode code={deal.origin} className="text-sm font-semibold text-deck-text-primary" />
        )}
        {deal.origin && deal.destination && (
          <span className="text-deck-text-muted text-xs">&rarr;</span>
        )}
        {deal.destination && (
          <AirportCode code={deal.destination} className="text-sm font-semibold text-deck-text-primary" />
        )}
        {deal.airline && (
          <span className="text-xs text-deck-text-secondary ml-auto">
            {deal.airline}
          </span>
        )}
      </div>

      {/* Title */}
      <p className="text-sm text-deck-text-secondary leading-snug line-clamp-2">
        {deal.title}
      </p>

      {/* Price + cabin */}
      <div className="flex items-center gap-3">
        {deal.converted_price != null && deal.preferred_currency ? (
          <PriceDisplay
            price={deal.converted_price}
            currency={deal.preferred_currency}
            size="lg"
          />
        ) : deal.price != null ? (
          <PriceDisplay
            price={deal.price}
            currency={deal.currency || 'USD'}
            size="lg"
          />
        ) : null}
        {deal.converted_price != null && deal.price != null && deal.currency && deal.currency !== deal.preferred_currency && (
          <span className="text-xs text-deck-text-muted">
            ({deal.currency} {deal.price.toLocaleString()})
          </span>
        )}
        {deal.cabin_class && deal.cabin_class !== 'ECONOMY' && (
          <Badge variant="info">
            {deal.cabin_class.replace('_', ' ').toLowerCase()}
          </Badge>
        )}
        {deal.deal_rating != null && deal.deal_rating > 0 && (
          <span className="text-xs text-deal-hot font-medium ml-auto">
            -{Math.round(deal.deal_rating)}%
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        {deal.link && (
          <a
            href={deal.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg bg-accent-primary text-deck-bg hover:bg-accent-primary-dim font-medium transition-colors"
          >
            View deal
            <span className="text-xs">&#8599;</span>
          </a>
        )}
        {deal.is_relevant && onDismiss && (
          <Button variant="ghost" size="sm" onClick={() => onDismiss(deal.id)}>
            Dismiss
          </Button>
        )}
        {!deal.is_relevant && onRestore && (
          <Button variant="ghost" size="sm" onClick={() => onRestore(deal.id)}>
            Restore
          </Button>
        )}
        {deal.relevance_reason && (
          <span className="text-xs text-deck-text-muted ml-auto">
            {deal.relevance_reason}
          </span>
        )}
      </div>
    </Card>
  )
}
