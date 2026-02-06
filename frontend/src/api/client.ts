import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
})

// --- Types ---

export interface SearchDefinition {
  id: number
  origin: string
  destination: string
  trip_type: string
  adults: number
  children: number
  cabin_class: string
  stops_filter: string
  currency: string
  name: string | null
  is_active: boolean
  created_at: string | null
}

export interface FlightPrice {
  id: number
  search_definition_id: number
  scraped_at: string
  departure_date: string
  return_date: string | null
  price_nzd: number
  airline: string | null
  stops: number
  duration_minutes: number | null
}

export interface PriceStats {
  search_definition_id: number
  min_price: number | null
  max_price: number | null
  avg_price: number | null
  current_price: number | null
  price_count: number
  price_trend: string | null
}

export interface Deal {
  id: number
  title: string
  origin: string | null
  destination: string | null
  price: number | null
  currency: string | null
  airline: string | null
  cabin_class: string | null
  source: string
  link: string | null
  published_at: string | null
  is_relevant: boolean
  relevance_reason: string | null
  deal_rating: number | null
  rating_label: string | null
}

export interface DealsResponse {
  deals: Deal[]
  count: number
}

export interface FeedHealth {
  source: string
  last_success: string | null
  consecutive_failures: number
  total_fetched: number
  total_new: number
  last_error: string | null
}

export interface UserSettings {
  home_airport: string | null
  notification_enabled: boolean
  ntfy_topic: string | null
}

// --- Search Definitions (Watchlist) ---

export async function fetchSearchDefinitions(activeOnly = true): Promise<SearchDefinition[]> {
  const { data } = await api.get('/prices/searches', { params: { active_only: activeOnly } })
  return data
}

export async function fetchSearchDefinition(id: number): Promise<SearchDefinition> {
  const { data } = await api.get(`/prices/searches/${id}`)
  return data
}

export async function createSearchDefinition(search: Partial<SearchDefinition>): Promise<SearchDefinition> {
  const { data } = await api.post('/prices/searches', search)
  return data
}

export async function deleteSearchDefinition(id: number): Promise<void> {
  await api.delete(`/prices/searches/${id}`)
}

// --- Prices ---

export async function fetchPriceHistory(searchId: number, days = 30): Promise<FlightPrice[]> {
  const { data } = await api.get(`/prices/searches/${searchId}/prices`, { params: { days } })
  return data
}

export async function fetchPriceStats(searchId: number): Promise<PriceStats> {
  const { data } = await api.get(`/prices/searches/${searchId}/stats`)
  return data
}

export async function fetchFlightOptions(searchId: number, limit = 3): Promise<{ options: unknown[] }> {
  const { data } = await api.get(`/prices/searches/${searchId}/options`, { params: { limit } })
  return data
}

export async function refreshPrices(searchId: number): Promise<{ success: boolean; prices_found?: number; error?: string }> {
  const { data } = await api.post(`/prices/searches/${searchId}/refresh`)
  return data
}

// --- Deals ---

export async function fetchDeals(params: {
  origin?: string
  relevant?: boolean
  limit?: number
  offset?: number
} = {}): Promise<DealsResponse> {
  const { data } = await api.get('/deals/api/deals', {
    params: { limit: 50, ...params },
  })
  return data
}

export async function dismissDeal(id: number): Promise<void> {
  await api.post(`/deals/api/deals/${id}/dismiss`)
}

export async function restoreDeal(id: number): Promise<void> {
  await api.post(`/deals/api/deals/${id}/restore`)
}

export async function fetchFeedHealth(): Promise<FeedHealth[]> {
  const { data } = await api.get('/deals/api/health/feeds')
  return data.feeds
}

// --- Settings ---

export async function fetchSettings(): Promise<UserSettings> {
  const { data } = await api.get('/settings/api/settings')
  return data
}

export async function updateSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
  const { data } = await api.put('/settings/api/settings', settings)
  return data
}

// --- Legacy compatibility ---

export async function fetchRoutes(): Promise<SearchDefinition[]> {
  return fetchSearchDefinitions()
}
