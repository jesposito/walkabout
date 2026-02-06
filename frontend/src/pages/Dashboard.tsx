export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-deck-text-primary">Dashboard</h1>
        <p className="text-deck-text-secondary mt-1">Your morning flight briefing</p>
      </div>

      <div className="bg-deck-surface rounded-card border border-deck-border p-6">
        <p className="text-deck-text-muted text-center py-8">
          Deal feed coming soon. Configure your watchlist to start monitoring.
        </p>
      </div>
    </div>
  )
}
