interface CardProps {
  children: React.ReactNode
  interactive?: boolean
  className?: string
  onClick?: () => void
  'aria-expanded'?: boolean
}

export default function Card({ children, interactive, className = '', onClick, 'aria-expanded': ariaExpanded }: CardProps) {
  return (
    <div
      className={`
        bg-deck-surface rounded-card border border-deck-border p-4
        shadow-[var(--card-shadow)]
        ${interactive
          ? 'cursor-pointer hover:shadow-[var(--card-shadow-hover)] hover:-translate-y-0.5 hover:border-deck-text-muted transition-all duration-200 ease-out'
          : ''}
        ${className}
      `}
      onClick={onClick}
      aria-expanded={ariaExpanded}
    >
      {children}
    </div>
  )
}
