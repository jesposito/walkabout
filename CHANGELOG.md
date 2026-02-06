# Changelog

All notable changes to Walkabout will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-02-06

### Added
- SQLite backup service with daily scheduled backups (3:00 AM) and manual trigger
- `POST /api/backup` endpoint for on-demand backups with rotation (keeps last 7)
- `GET /api/backups` endpoint to list available backups
- Docker HEALTHCHECK instruction in Dockerfile
- Rolling-horizon date sampling for price monitoring (varies across search window daily)
- Unit tests for date sampling (9 tests)

### Changed
- `ensure_sqlite_columns()` now auto-generates from SQLAlchemy model metadata (no manual list)
- Default timezone changed from Pacific/Auckland to America/New_York throughout
- Default fallback airport changed from AKL to JFK
- Playwright browser locale changed from en-NZ to en-US
- Consolidated 4 docker-compose files into single docker-compose.yml
- Stale trip search locks automatically cleared on startup

### Removed
- Dead Celery worker/beat infrastructure (`celery_app/` directory)
- Dead Alembic migration files (`alembic/` directory, `alembic.ini`)
- Unused dependencies: celery, redis, asyncpg, psycopg2-binary, alembic
- Postgres connection pool configuration (SQLite is the target database)
- Production SQLite rejection guard (`model_post_init`)
- Obsolete docker-compose files (phase1a, prod, single variants)

## [0.4.0] - 2026-02-06

### Added
- In-app About page with version display and changelog
- Skip-to-main-content link for keyboard navigation
- Full ARIA combobox pattern on airport input (arrow key navigation, listbox/option roles)
- `aria-live="polite"` on status indicators and save status
- `aria-expanded` on collapsible sections
- Shared AIActionButton component (extracted from 3 pages)

### Changed
- WCAG AA color contrast compliance: muted text (4.7:1) and accent links (4.6:1) in both modes
- All interactive elements now meet 44px minimum touch target
- All buttons have visible keyboard focus indicators (focus-visible ring)
- Badge `above` variant renamed to `warning` for semantic clarity
- Renamed "Playwright" to "Google Flights Scraper" in dashboard status
- Deals tabs now use proper ARIA tab pattern (role=tablist, role=tab, aria-selected)

### Fixed
- Text scrunching in AI result blocks (added break-words, min-w-0, flex-wrap)
- Price + cabin layout overflow in DealCard
- Airport remove buttons now touch-friendly with aria-labels
- MileValueForm stacks vertically on mobile
- Pattern analysis badges wrap on narrow screens

## [0.3.0] - 2026-02-05

### Added
- SerpAPI integration for Google Flights price data with insights
- Amadeus GDS integration with price analysis metrics
- Seats.aero award flight tracking with pattern analysis
- AI service layer supporting Claude and Ollama with cost tracking
- AI-powered deal explanations on deal cards
- AI trip feasibility checks with budget and schedule analysis
- AI award sweet spot analysis and mile valuation
- AI settings review assistant
- Onboarding wizard for first-time setup

### Changed
- Price fetching now uses multi-source fallback chain (SerpAPI → Amadeus → Playwright)
- Dashboard shows AI-powered deal digest

## [0.2.0] - 2026-02-03

### Added
- React SPA frontend (Vite + TailwindCSS + React Router + TanStack Query)
- Dark/light mode with CSS custom property design system
- Mobile-responsive layout with bottom navigation
- Watchlist page for search definition management
- History page for price history charts
- Trip Plans page with multi-origin/destination flexible search
- Awards page for Seats.aero tracking

### Changed
- Frontend migrated from Jinja2 server-rendered templates to React SPA
- Price extraction rewritten with per-row extraction and confidence model
- URL construction fixed with filter passthrough and currency detection
- Confidence gating: 0.5 for storage, 0.6 for deal analysis

## [0.1.2] - 2026-01-30

### Added
- Granular notification settings: configure alerts by type (deals, trips, routes, system)
- Deal notification filters: minimum rating, categories (local/regional), cabin classes
- Per-notification-type cooldowns: separate cooldowns for deals, trips, and route updates
- Daily digest option with configurable hour
- Settings page accordion UI for organized configuration
- Toggle switches for all boolean settings

### Changed
- Settings page completely redesigned with collapsible sections
- Notification settings now use proper JSON API for ntfy (fixes emoji encoding)
- Improved mobile responsiveness for settings page

### Fixed
- ntfy notifications now properly display emojis (using JSON API instead of headers)
- SQLite migration helper now includes all notification columns (prevents missing column errors)
- Database column synchronization on startup for SQLite deployments
- Correct Discord and Buy Me a Coffee links on About page

## [0.1.1] - 2026-01-30

### Changed
- Deal cards now show action buttons directly on mobile (hover overlay only on desktop)
- Improved navigation touch targets for mobile devices
- Toast notifications now span full width on mobile

### Fixed
- Deal "View Deal" and "Track Route" buttons now accessible on touch devices (Tailscale mobile access)

## [0.1.0] - 2026-01-30

### Added
- Initial release
- Flight deal monitoring from Google Flights
- Trip plan management with flexible dates
- RSS deal aggregation from Fly4Free, SecretFlying
- Push notifications via ntfy
- Server-rendered dashboard
- SQLite database with proper foreign key support

### Fixed
- SQLite foreign key constraints now enabled (fixes trip plan match contamination)

[Unreleased]: https://github.com/jesposito/walkabout/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/jesposito/walkabout/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jesposito/walkabout/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jesposito/walkabout/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jesposito/walkabout/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/jesposito/walkabout/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jesposito/walkabout/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jesposito/walkabout/releases/tag/v0.1.0
