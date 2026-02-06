interface CardProps {
  children: React.ReactNode
  interactive?: boolean
  className?: string
  onClick?: () => void
}

export default function Card({ children, interactive, className = '', onClick }: CardProps) {
  const base = 'bg-deck-surface rounded-card border border-deck-border p-4'
  const interactiveStyles = interactive
    ? 'cursor-pointer hover:bg-deck-surface-hover hover:border-deck-text-muted transition-colors'
    : ''

  return (
    <div className={`${base} ${interactiveStyles} ${className}`} onClick={onClick}>
      {children}
    </div>
  )
}
