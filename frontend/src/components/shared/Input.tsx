import { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export default function Input({ label, error, className = '', id, ...props }: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-deck-text-secondary">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`
          w-full rounded-lg bg-deck-bg border border-deck-border px-3 py-2
          text-deck-text-primary placeholder:text-deck-text-muted
          focus:outline-none focus:ring-2 focus:ring-accent-primary/50 focus:border-accent-primary
          disabled:opacity-50
          ${error ? 'border-deal-above focus:ring-deal-above/50' : ''}
          ${className}
        `}
        {...props}
      />
      {error && (
        <p className="text-sm text-deal-above">{error}</p>
      )}
    </div>
  )
}
