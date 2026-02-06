import { PageHeader, EmptyState } from '../components/shared'

export default function History() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="History"
        subtitle="Price history and trends"
      />
      <EmptyState
        icon="📈"
        title="No price history"
        description="Price charts will appear here once routes are being tracked."
      />
    </div>
  )
}
