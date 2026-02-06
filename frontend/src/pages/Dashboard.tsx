import { PageHeader, EmptyState } from '../components/shared'

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        subtitle="Your morning flight briefing"
      />
      <EmptyState
        icon="📡"
        title="Flight radar warming up"
        description="Configure your watchlist to start monitoring prices and finding deals."
        actionLabel="Add a route"
        onAction={() => window.location.href = '/watchlist'}
      />
    </div>
  )
}
