import { useState } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchSettings } from './api/client'
import AppShell from './components/AppShell'
import OnboardingWizard from './components/OnboardingWizard'
import Dashboard from './pages/Dashboard'
import Watchlist from './pages/Watchlist'
import TripPlans from './pages/TripPlans'
import Deals from './pages/Deals'
import History from './pages/History'
import Settings from './pages/Settings'

function AppContent() {
  const queryClient = useQueryClient()
  const [dismissed, setDismissed] = useState(false)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchSettings,
  })

  const needsOnboarding =
    !dismissed &&
    !isLoading &&
    settings &&
    (!settings.home_airports || settings.home_airports.length === 0)

  return (
    <>
      {needsOnboarding && (
        <OnboardingWizard
          onComplete={() => {
            setDismissed(true)
            queryClient.invalidateQueries({ queryKey: ['settings'] })
          }}
        />
      )}
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/watchlist" element={<Watchlist />} />
          <Route path="/trips" element={<TripPlans />} />
          <Route path="/deals" element={<Deals />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
