interface BadgeProps {
  variant: 'hot' | 'good' | 'decent' | 'normal' | 'warning' | 'info'
  children: React.ReactNode
  className?: string
}

const variantStyles: Record<BadgeProps['variant'], string> = {
  hot: 'bg-deal-hot/20 text-deal-hot border-deal-hot/30',
  good: 'bg-deal-good/20 text-deal-good border-deal-good/30',
  decent: 'bg-deal-decent/20 text-deal-decent border-deal-decent/30',
  normal: 'bg-deck-border text-deck-text-secondary border-deck-border',
  warning: 'bg-deal-above/20 text-deal-above border-deal-above/30',
  info: 'bg-accent-secondary/20 text-accent-secondary border-accent-secondary/30',
}

export default function Badge({ variant, children, className = '' }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
        border ${variantStyles[variant]} ${className}
      `}
    >
      {children}
    </span>
  )
}
