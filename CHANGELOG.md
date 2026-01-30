# Changelog

All notable changes to Walkabout will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/jesposito/walkabout/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jesposito/walkabout/releases/tag/v0.1.0
