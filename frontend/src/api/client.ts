import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL !== undefined
  ? import.meta.env.VITE_API_URL
  : 'http://localhost:8000'

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
  total_price_nzd: number | null
  passengers: number | null
  trip_type: string | null
  airline: string | null
  stops: number
  duration_minutes: number | null
  layover_airports: string | null
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
  converted_price: number | null
  preferred_currency: string | null
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
  // Location
  home_airport: string
  home_airports: string[]
  home_region: string
  watched_destinations: string[]
  watched_regions: string[]
  preferred_currency: string
  // Notifications
  notifications_enabled: boolean
  notification_provider: string
  notification_ntfy_url: string | null
  notification_ntfy_topic: string | null
  notification_discord_webhook: string | null
  notification_min_discount_percent: number
  notification_quiet_hours_start: number | null
  notification_quiet_hours_end: number | null
  notification_cooldown_minutes: number
  timezone: string
  // Granular toggles
  notify_deals: boolean
  notify_trip_matches: boolean
  notify_route_updates: boolean
  notify_system: boolean
  // Deal filters
  deal_notify_min_rating: number
  deal_notify_categories: string[]
  deal_notify_cabin_classes: string[]
  // Frequency
  deal_cooldown_minutes: number
  trip_cooldown_hours: number
  route_cooldown_hours: number
  // Digest
  daily_digest_enabled: boolean
  daily_digest_hour: number
  // API keys (masked on read)
  anthropic_api_key: string | null
  serpapi_key: string | null
  skyscanner_api_key: string | null
  amadeus_client_id: string | null
  amadeus_client_secret: string | null
  seats_aero_api_key: string | null
  ai_provider: string | null
  ai_api_key: string | null
  ai_ollama_url: string | null
  ai_model: string | null
}

export interface AirportSearchResult {
  code: string
  name: string
  city: string
  country: string
  region: string
  label: string
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

export interface CategorizedDeals {
  local: Deal[]
  regional: Deal[]
  worldwide: Deal[]
  counts: { local: number; regional: number; worldwide: number }
  preferred_currency: string
}

export async function fetchCategorizedDeals(params: {
  limit?: number
  sort?: string
} = {}): Promise<CategorizedDeals> {
  const { data } = await api.get('/deals/api/deals/categorized', {
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

// --- Airports ---

export async function searchAirports(query: string, limit = 10): Promise<AirportSearchResult[]> {
  if (query.length < 2) return []
  const { data } = await api.get('/settings/api/airports/search', { params: { q: query, limit } })
  return data.results
}

export async function lookupAirports(codes: string[]): Promise<Record<string, { city: string; country: string }>> {
  if (codes.length === 0) return {}
  const { data } = await api.get('/settings/api/airports/bulk', { params: { codes: codes.join(',') } })
  return data
}

// --- Notifications ---

export async function testNotification(): Promise<{ success: boolean; message: string; provider: string }> {
  const { data } = await api.post('/settings/api/notifications/test')
  return data
}

// --- Trip Plans ---

export interface TripLeg {
  origin: string
  destination: string
  date_start: string | null
  date_end: string | null
  order: number
}

export interface TripPlan {
  id: number
  name: string
  origins: string[]
  destinations: string[]
  destination_types: string[]
  legs: TripLeg[]
  available_from: string | null
  available_to: string | null
  trip_duration_min: number
  trip_duration_max: number
  budget_max: number | null
  budget_currency: string
  cabin_classes: string[]
  travelers_adults: number
  travelers_children: number
  is_active: boolean
  notify_on_match: boolean
  check_frequency_hours: number
  match_count: number
  last_match_at: string | null
  notes: string | null
  created_at: string
  search_in_progress: boolean
}

export interface TripPlanCreate {
  name: string
  origins?: string[]
  destinations?: string[]
  destination_types?: string[]
  legs?: TripLeg[]
  available_from?: string | null
  available_to?: string | null
  trip_duration_min?: number
  trip_duration_max?: number
  budget_max?: number | null
  budget_currency?: string
  cabin_classes?: string[]
  travelers_adults?: number
  travelers_children?: number
  notify_on_match?: boolean
  check_frequency_hours?: number
  notes?: string | null
}

export interface TripPlanMatch {
  id: number
  trip_plan_id: number
  source: string
  origin: string
  destination: string
  departure_date: string
  return_date: string | null
  price_nzd: number
  airline: string | null
  stops: number
  duration_minutes: number | null
  booking_url: string | null
  match_score: number
  deal_title: string | null
  found_at: string
}

export interface DestinationType {
  id: string
  name: string
  emoji: string
  description: string
}

export async function fetchDestinationTypes(): Promise<DestinationType[]> {
  const { data } = await api.get('/trips/api/destination-types')
  return data
}

export async function fetchTripPlans(activeOnly = false): Promise<TripPlan[]> {
  const { data } = await api.get('/trips/api/trips', { params: { active_only: activeOnly } })
  return data.trips || data
}

export async function fetchTripPlan(id: number): Promise<TripPlan> {
  const { data } = await api.get(`/trips/api/trips/${id}`)
  return data
}

export async function createTripPlan(plan: TripPlanCreate): Promise<TripPlan> {
  const { data } = await api.post('/trips/api/trips', plan)
  return data
}

export async function updateTripPlan(id: number, plan: TripPlanCreate): Promise<TripPlan> {
  const { data } = await api.put(`/trips/api/trips/${id}`, plan)
  return data
}

export async function deleteTripPlan(id: number): Promise<void> {
  await api.delete(`/trips/api/trips/${id}`)
}

export async function toggleTripPlan(id: number): Promise<{ is_active: boolean }> {
  const { data } = await api.put(`/trips/api/trips/${id}/toggle`)
  return data
}

export async function searchTripPlan(id: number): Promise<{ status: string; message: string }> {
  const { data } = await api.post(`/trips/api/trips/${id}/search`)
  return data
}

// --- Trip AI Intelligence ---

export interface TokenEstimate {
  input_tokens_est: number
  output_tokens_est: number
  cost_est_usd: number
}

export interface TripNameResult {
  name: string
  vibe: string
  estimate: TokenEstimate
}

export interface TripFeasibilityResult {
  verdict: string
  reasoning: string
  confidence: 'high' | 'medium' | 'low'
  estimate: TokenEstimate
}

export interface DestinationSuggestion {
  airport: string
  city: string
  reasoning: string
}

export interface DestinationSuggestResult {
  suggestions: DestinationSuggestion[]
  estimate: TokenEstimate
}

export interface DestinationSuggestRequest {
  origins: string[]
  available_from?: string | null
  available_to?: string | null
  duration_min?: number
  duration_max?: number
  budget_max?: number | null
  budget_currency?: string
  cabin_classes?: string[]
  travelers_adults?: number
  travelers_children?: number
}

export async function aiNameTrip(id: number): Promise<TripNameResult> {
  const { data } = await api.post(`/trips/api/trips/${id}/name`)
  return data
}

export async function aiNameTripEstimate(id: number): Promise<TokenEstimate> {
  const { data } = await api.get(`/trips/api/trips/${id}/name/estimate`)
  return data
}

export async function aiCheckFeasibility(id: number): Promise<TripFeasibilityResult> {
  const { data } = await api.post(`/trips/api/trips/${id}/feasibility`)
  return data
}

export async function aiFeasibilityEstimate(id: number): Promise<TokenEstimate> {
  const { data } = await api.get(`/trips/api/trips/${id}/feasibility/estimate`)
  return data
}

export async function aiSuggestDestinations(request: DestinationSuggestRequest): Promise<DestinationSuggestResult> {
  const { data } = await api.post('/trips/api/suggest-destinations', request)
  return data
}

export async function fetchTripPlanMatches(id: number, limit = 20): Promise<TripPlanMatch[]> {
  const { data } = await api.get(`/trips/api/trips/${id}/matches`, { params: { limit } })
  const raw = data.matches || data
  // Backend returns {deal: {...}, match_score} - flatten to TripPlanMatch shape
  return raw.map((m: Record<string, unknown>) => {
    if (m.deal && typeof m.deal === 'object') {
      const deal = m.deal as Record<string, unknown>
      return {
        id: deal.id,
        trip_plan_id: id,
        source: deal.source || 'unknown',
        origin: deal.origin,
        destination: deal.destination,
        departure_date: deal.published_at || '',
        return_date: null,
        price_nzd: deal.converted_price ?? deal.price ?? 0,
        airline: deal.airline,
        stops: 0,
        duration_minutes: null,
        booking_url: deal.link,
        match_score: m.match_score as number,
        deal_title: deal.title,
        found_at: deal.published_at || '',
      } as TripPlanMatch
    }
    return m as unknown as TripPlanMatch
  })
}

// --- Awards ---

export interface AwardSearch {
  id: number
  name: string | null
  origin: string
  destination: string
  program: string | null
  date_start: string | null
  date_end: string | null
  cabin_class: string
  min_seats: number
  direct_only: boolean
  is_active: boolean
  notify_on_change: boolean
  last_polled_at: string | null
  notes: string | null
  created_at: string
}

export interface AwardSearchCreate {
  name?: string
  origin: string
  destination: string
  program?: string | null
  date_start?: string | null
  date_end?: string | null
  cabin_class?: string
  min_seats?: number
  direct_only?: boolean
  notify_on_change?: boolean
  notes?: string | null
}

export interface AwardObservation {
  id: number
  search_id: number
  observed_at: string
  is_changed: boolean
  programs_with_availability: string[]
  best_economy_miles: number | null
  best_business_miles: number | null
  best_first_miles: number | null
  total_options: number
  max_seats_available: number
}

export async function fetchAwardSearches(activeOnly = false): Promise<AwardSearch[]> {
  const { data } = await api.get('/awards/api/awards', { params: { active_only: activeOnly } })
  return data
}

export async function createAwardSearch(search: AwardSearchCreate): Promise<AwardSearch> {
  const { data } = await api.post('/awards/api/awards', search)
  return data
}

export async function deleteAwardSearch(id: number): Promise<void> {
  await api.delete(`/awards/api/awards/${id}`)
}

export async function toggleAwardSearch(id: number): Promise<{ is_active: boolean }> {
  const { data } = await api.put(`/awards/api/awards/${id}/toggle`)
  return data
}

export async function pollAwardSearch(id: number): Promise<{ status: string; message?: string; changed?: boolean; total_options?: number }> {
  const { data } = await api.post(`/awards/api/awards/${id}/poll`)
  return data
}

export async function fetchAwardObservations(id: number, limit = 20): Promise<{ search: AwardSearch; observations: AwardObservation[] }> {
  const { data } = await api.get(`/awards/api/awards/${id}/observations`, { params: { limit } })
  return data
}

export async function fetchLatestAwardResults(id: number): Promise<{ observation: AwardObservation | null; results: unknown[] }> {
  const { data } = await api.get(`/awards/api/awards/${id}/latest`)
  return data
}

// --- System Status ---

export interface DataSourceInfo {
  available: boolean
  type: string
}

export interface SystemStatus {
  data_sources: Record<string, DataSourceInfo>
  ai_enabled: boolean
  total_sources_available: number
  scheduler: {
    running: boolean
    next_run: string | null
    job_count: number
  }
  stats: {
    active_monitors: number
    recent_prices_7d: number
    last_scrape_at: string | null
  }
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const { data } = await api.get('/api/status/sources')
  return data
}

// --- Legacy compatibility ---

export async function fetchRoutes(): Promise<SearchDefinition[]> {
  return fetchSearchDefinitions()
}
