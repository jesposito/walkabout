import { ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

const variantStyles = {
  primary: 'bg-accent-primary text-deck-bg hover:bg-accent-primary-dim active:bg-accent-primary-dim font-medium',
  secondary: 'bg-deck-surface text-deck-text-primary border border-deck-border hover:bg-deck-surface-hover active:bg-deck-surface-hover',
  ghost: 'text-deck-text-secondary hover:text-deck-text-primary hover:bg-deck-surface active:bg-deck-surface',
  danger: 'text-danger border border-danger/30 hover:bg-danger/10 active:bg-danger/20 font-medium',
}

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm min-h-[44px]',
  md: 'px-4 py-2 text-sm min-h-[44px]',
  lg: 'px-6 py-3 text-base min-h-touch',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`
        inline-flex items-center justify-center rounded-lg transition-colors
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-deck-bg
        disabled:opacity-50 disabled:pointer-events-none
        active:scale-[0.98] transition-transform
        ${variantStyles[variant]}
        ${sizeStyles[size]}
        ${className}
      `}
      {...props}
    >
      {children}
    </button>
  )
}
