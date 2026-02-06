interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
  label?: string
}

const sizeClasses = {
  sm: 'h-4 w-4 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-3',
}

export default function Spinner({ size = 'md', className = '', label = 'Loading' }: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label={label}
      className={`
        animate-spin rounded-full border-deck-border border-t-accent-primary
        ${sizeClasses[size]} ${className}
      `}
    />
  )
}
