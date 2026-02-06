import { useState, useCallback } from 'react'
import { TokenEstimate } from '../api/client'

interface UseAIActionOptions<TResult> {
  /** The async function to execute the AI action */
  action: () => Promise<TResult>
  /** Optional async function to fetch a token/cost estimate */
  fetchEstimate?: () => Promise<TokenEstimate>
  /** Callback on success */
  onSuccess?: (result: TResult) => void
}

interface UseAIActionReturn<TResult> {
  /** Execute the AI action */
  execute: () => Promise<void>
  /** Whether the action is currently running */
  loading: boolean
  /** The result of the last execution */
  result: TResult | null
  /** Error message if the last execution failed */
  error: string | null
  /** Token/cost estimate (fetched separately) */
  estimate: TokenEstimate | null
  /** Whether the estimate is currently being fetched */
  estimateLoading: boolean
  /** Load the token/cost estimate */
  loadEstimate: () => Promise<void>
  /** Clear the result to hide the display */
  clear: () => void
}

export function useAIAction<TResult>(options: UseAIActionOptions<TResult>): UseAIActionReturn<TResult> {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<TResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [estimate, setEstimate] = useState<TokenEstimate | null>(null)
  const [estimateLoading, setEstimateLoading] = useState(false)

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await options.action()
      setResult(res)
      options.onSuccess?.(res)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'AI action failed'
      // Extract detail from Axios error response if available
      const axiosError = err as { response?: { data?: { detail?: string }; status?: number } }
      if (axiosError.response?.status === 503) {
        setError('AI is not configured. Set up a provider in Settings.')
      } else if (axiosError.response?.data?.detail) {
        setError(axiosError.response.data.detail)
      } else {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }, [options.action, options.onSuccess])

  const loadEstimate = useCallback(async () => {
    if (!options.fetchEstimate) return
    setEstimateLoading(true)
    try {
      const est = await options.fetchEstimate()
      setEstimate(est)
    } catch {
      // Silently fail - estimate is optional
    } finally {
      setEstimateLoading(false)
    }
  }, [options.fetchEstimate])

  const clear = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return { execute, loading, result, error, estimate, estimateLoading, loadEstimate, clear }
}
