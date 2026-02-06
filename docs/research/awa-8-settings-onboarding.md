# Research: Settings and Onboarding (awa.8)

## Executive Summary

The backend settings system is mature with 40+ fields covering location, notifications (4 providers), AI config, and API keys. The Jinja2 settings page is fully featured with airport autocomplete, toggle switches, provider-aware field visibility, and masked API keys. The React Settings page is a placeholder. Main work is porting Jinja2 functionality to React components.

## Settings API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/settings/api/settings` | GET | All settings (keys masked) |
| `/settings/api/settings` | PUT | Update settings (ignores masked values) |
| `/settings/api/airports/search` | GET | Airport autocomplete (q, limit) |
| `/settings/api/airports/{code}` | GET | Single airport details |

## Settings Categories

### Location (8 fields)
- home_airports (list), home_airport (legacy), home_region, watched_destinations, watched_regions, preferred_currency

### Notifications (20+ fields)
- Master: notifications_enabled, notification_provider (none/ntfy_sh/ntfy_self/discord)
- Provider-specific: ntfy_url, ntfy_topic, discord_webhook
- Granular toggles: notify_deals, notify_trip_matches, notify_route_updates, notify_system
- Filters: deal_notify_min_rating (1-5), deal_notify_categories, deal_notify_cabin_classes
- Timing: timezone, quiet_hours_start/end, cooldown_minutes
- Digest: daily_digest_enabled, daily_digest_hour

### AI & API Keys (8 fields)
- ai_provider (none/anthropic/openai/gemini/ollama/openai_compatible)
- ai_api_key, ai_ollama_url, ai_model
- anthropic_api_key, serpapi_key, skyscanner_api_key, amadeus_client_id/secret

## Notification Providers

| Provider | Config Fields |
|----------|--------------|
| none | In-app only |
| ntfy_sh | topic |
| ntfy_self | url + topic |
| discord | webhook URL |

## Airport Search

- Endpoint: `/api/airports/search?q=auck&limit=10`
- Scoring: exact code (100), code prefix (90), city prefix (85), city contains (70), country (50)
- Data: airports.dat CSV with ~7000 airports, region inference from timezone
- City aliases: nyc->new york, la->los angeles, etc.

## Components to Build

1. **CollapsibleSection** - Expandable section with icon + title
2. **AirportMultiSelect** - Debounced search + badge rendering + dedup
3. **ToggleSwitch** - iOS-style toggle for booleans
4. **PasswordInput** - Masked API key input (handles ****last4 pattern)
5. **ProviderFieldToggler** - Show/hide fields based on provider selection
6. **HourSelector** - 0-23 + "Off" dropdown for quiet hours

## TypeScript Interface Gap

Current `UserSettings` interface has only 3 fields. Needs expansion to 40+ fields to match backend `SettingsResponse`.

## Implementation Priority

1. Core: Update TypeScript interface, AirportMultiSelect, CollapsibleSection, ToggleSwitch
2. Notifications: Provider field visibility, all toggles, test button
3. API Keys: Password masking, AI provider visibility
4. Polish: Form validation, loading/saving states, success/error feedback

## Onboarding Wizard (3 steps)

1. **Home Airport** - Where are you based?
2. **Interests** - Dream destinations, preferred cabin
3. **Notifications** - Enable + pick provider

Triggered when UserSettings has no home_airport set.

## Files Reviewed

- `backend/app/api/settings.py`, `backend/app/models/user_settings.py`
- `backend/app/services/notification.py`, `backend/app/api/notifications.py`
- `backend/app/services/airports.py`, `backend/app/resources/airports.dat`
- `backend/alembic/versions/004_granular_notification_settings.py`
- `backend/templates/settings.html` (Jinja2 reference implementation)
- `frontend/src/api/client.ts`, `frontend/src/pages/Settings.tsx`
