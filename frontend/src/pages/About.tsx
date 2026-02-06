import { useQuery } from '@tanstack/react-query'
import { fetchVersion, fetchChangelog } from '../api/client'
import { PageHeader, Card, Spinner } from '../components/shared'

export default function About() {
  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: fetchVersion,
  })

  const { data: changelog, isLoading: changelogLoading } = useQuery({
    queryKey: ['changelog'],
    queryFn: fetchChangelog,
  })

  return (
    <div className="space-y-6">
      <PageHeader
        title="About"
        subtitle={version ? `${version.name} ${version.version}` : 'Loading...'}
      />

      <Card>
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide">Version</h3>
          <p className="text-lg font-mono font-semibold text-accent-primary">
            {version?.version || '...'}
          </p>
          <p className="text-sm text-deck-text-secondary">
            {version?.description || 'Self-hosted flight deal aggregator'}
          </p>
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-4">Changelog</h3>
        {changelogLoading ? (
          <div className="flex justify-center py-4">
            <Spinner />
          </div>
        ) : changelog ? (
          <div className="prose prose-sm max-w-none text-deck-text-secondary">
            <pre className="whitespace-pre-wrap text-xs font-mono text-deck-text-secondary bg-deck-bg rounded-lg p-4 overflow-x-auto break-words">
              {typeof changelog === 'string' ? changelog : JSON.stringify(changelog, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-deck-text-muted">No changelog available.</p>
        )}
      </Card>

      <Card>
        <h3 className="text-sm font-medium text-deck-text-secondary uppercase tracking-wide mb-3">Links</h3>
        <div className="space-y-2">
          <a
            href="https://github.com/jesposito/walkabout"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-accent-primary hover:underline"
          >
            GitHub Repository
          </a>
          <a
            href="https://discord.gg/eKg4MhMkVJ"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-accent-primary hover:underline"
          >
            Discord Community
          </a>
          <a
            href="https://buymeacoffee.com/jesposito"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-accent-primary hover:underline"
          >
            Buy Me a Coffee
          </a>
        </div>
      </Card>
    </div>
  )
}
