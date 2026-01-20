import { useQuery } from '@tanstack/react-query'
import { fetchRoutes, fetchPriceStats } from './api/client'
import PriceChart from './components/PriceChart'
import RouteCard from './components/RouteCard'

function App() {
  const { data: routes, isLoading } = useQuery({
    queryKey: ['routes'],
    queryFn: fetchRoutes,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Walkabout</h1>
          <p className="text-gray-600">Travel Deal Monitor</p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {routes?.map((route) => (
            <RouteCard key={route.id} route={route} />
          ))}
        </div>

        {(!routes || routes.length === 0) && (
          <div className="text-center py-12">
            <p className="text-gray-500">No routes configured yet.</p>
            <p className="text-gray-400 text-sm mt-2">
              Add a route via the API to start monitoring.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
