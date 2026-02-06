import { PageHeader, EmptyState } from '../components/shared'

export default function Watchlist() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Watchlist"
        subtitle="Routes you're monitoring"
      />
      <EmptyState
        icon="👀"
        title="Nothing tracked yet"
        description="Add your first route to start monitoring prices."
        actionLabel="Add a route"
        onAction={() => {}}
      />
    </div>
  )
}
