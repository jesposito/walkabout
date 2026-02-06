import { useEffect } from 'react'
import { TokenEstimate } from '../../api/client'
import { useAIAction } from '../../hooks/useAIAction'
import Button from './Button'
import Spinner from './Spinner'

interface AIActionButtonProps<T> {
  label: string
  action: () => Promise<T>
  fetchEstimate?: () => Promise<TokenEstimate>
  onSuccess?: (result: T) => void
  renderResult: (result: T) => React.ReactNode
}

export function formatEstimate(estimate: TokenEstimate | null): string {
  if (!estimate) return ''
  const totalTokens = estimate.input_tokens_est + estimate.output_tokens_est
  const cost = estimate.cost_est_usd
  if (cost < 0.001) return `~${totalTokens} tokens`
  return `~${totalTokens} tokens (~$${cost.toFixed(3)})`
}

export default function AIActionButton<T>({
  label,
  action,
  fetchEstimate,
  onSuccess,
  renderResult,
}: AIActionButtonProps<T>) {
  const ai = useAIAction<T>({ action, fetchEstimate, onSuccess })

  useEffect(() => {
    if (fetchEstimate && !ai.estimate && !ai.estimateLoading) {
      ai.loadEstimate()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant="secondary"
          size="sm"
          onClick={(e) => { e.stopPropagation(); ai.execute() }}
          disabled={ai.loading}
        >
          {ai.loading ? (
            <span className="flex items-center gap-1.5">
              <Spinner size="sm" />
              Thinking...
            </span>
          ) : (
            label
          )}
        </Button>
        {ai.estimate && !ai.result && !ai.loading && (
          <span className="text-xs text-deck-text-muted">
            {formatEstimate(ai.estimate)}
          </span>
        )}
      </div>

      {ai.error && (
        <p className="text-xs text-danger break-words">{ai.error}</p>
      )}

      {ai.result && (
        <div className="p-3 rounded-lg bg-deck-bg border border-deck-border space-y-2 min-w-0">
          <div className="break-words min-w-0">{renderResult(ai.result)}</div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); ai.execute() }}
              className="text-xs text-accent-primary hover:underline min-h-[44px] inline-flex items-center"
              disabled={ai.loading}
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); ai.clear() }}
              className="text-xs text-deck-text-muted hover:text-deck-text-secondary min-h-[44px] inline-flex items-center"
            >
              Hide
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
