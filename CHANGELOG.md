# Changelog

All notable changes to Walkabout will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/jesposito/walkabout/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/jesposito/walkabout/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jesposito/walkabout/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jesposito/walkabout/releases/tag/v0.1.0
