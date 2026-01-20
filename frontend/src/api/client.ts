import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
})

export interface Route {
  id: number
  origin: string
  destination: string
  name: string
  is_active: boolean
  scrape_frequency_hours: number
  created_at: string
}

export interface FlightPrice {
  id: number
  route_id: number
  scraped_at: string
  departure_date: string
  return_date: string
  price_nzd: number
  airline: string | null
  stops: number
  cabin_class: string
  passengers: number
}

export interface PriceStats {
  route_id: number
  min_price: number
  max_price: number
  avg_price: number
  current_price: number | null
  price_count: number
  z_score: number | null
  percentile: number | null
}

export async function fetchRoutes(): Promise<Route[]> {
  const { data } = await api.get('/api/routes')
  return data
}

export async function fetchPriceHistory(routeId: number, days = 30): Promise<FlightPrice[]> {
  const { data } = await api.get(`/api/prices/${routeId}`, {
    params: { days }
  })
  return data
}

export async function fetchPriceStats(routeId: number): Promise<PriceStats> {
  const { data } = await api.get(`/api/prices/${routeId}/stats`)
  return data
}

export async function triggerScrape(): Promise<void> {
  await api.post('/api/scrape/trigger')
}
