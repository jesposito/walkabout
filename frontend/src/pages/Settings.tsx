import { PageHeader, Card } from '../components/shared'

export default function Settings() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        subtitle="Configure your preferences"
      />
      <Card>
        <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-3">Location</h3>
        <p className="text-deck-text-muted text-sm">Home airport configuration coming soon.</p>
      </Card>
      <Card>
        <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-3">Notifications</h3>
        <p className="text-deck-text-muted text-sm">Notification preferences coming soon.</p>
      </Card>
      <Card>
        <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-3">API Keys</h3>
        <p className="text-deck-text-muted text-sm">API key configuration coming soon.</p>
      </Card>
    </div>
  )
}
