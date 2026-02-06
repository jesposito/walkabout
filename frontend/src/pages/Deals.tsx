import { PageHeader, EmptyState } from '../components/shared'

export default function Deals() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Deals"
        subtitle="Found deals from RSS feeds and price monitoring"
      />
      <EmptyState
        icon="🏷️"
        title="No deals yet"
        description="Deals will appear here as we find price drops and flight deals from RSS feeds."
      />
    </div>
  )
}
