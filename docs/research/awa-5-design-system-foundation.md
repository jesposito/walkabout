# Research: Design System & Frontend Foundation

**Beads ID**: walkabout-awa.5.1
**Feature**: walkabout-awa.5 (Design System & Frontend Foundation)
**Date**: 2026-02-06

---

## Table of Contents

1. [UX Design Token Summary](#1-ux-design-token-summary)
2. [Current Frontend State Analysis](#2-current-frontend-state-analysis)
3. [Current Jinja2 Template Functionality Inventory](#3-current-jinja2-template-functionality-inventory)
4. [Backend API Endpoint Summary](#4-backend-api-endpoint-summary)
5. [React Router Setup Plan](#5-react-router-setup-plan)
6. [Tailwind Dark Mode + Design Token Configuration](#6-tailwind-dark-mode--design-token-configuration)
7. [Font Loading Strategy](#7-font-loading-strategy)
8. [Navigation Component Design](#8-navigation-component-design)
9. [Shared Component Inventory](#9-shared-component-inventory)
10. [Migration Strategy](#10-migration-strategy)
11. [NPM Dependencies](#11-npm-dependencies)
12. [Files That Will Need Changes](#12-files-that-will-need-changes)

---

## 1. UX Design Token Summary

Source: `/home/jed/dev/walkabout/docs/UX_DESIGN.md` ("The Calm Flight Deck")

### Design Philosophy

- **Aesthetic**: Rationalist Utility / Swiss International Style
- **Tone**: Precision, clarity, anticipation. Professional decision-making tool.
- **Dark mode native**: High-contrast signals on deep charcoal backgrounds.
- **Mobile-first**: PWA candidate, responsive at all breakpoints.

### Colors (Dark Mode)

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#1a1a1a` | Main background |
| `--bg-card` | `#252525` | Card background |
| `--text-primary` | `#f0f0f0` | Main text |
| `--text-secondary` | `#888888` | Secondary text |
| `--accent-deal` | `#00ff88` | Good deal indicator (Electric Green) |
| `--accent-alert` | `#ffaa00` | Warning/alert (Amber) |
| `--accent-info` | `#00aaff` | Information |

**Note on Jinja2 template divergence**: The current Jinja2 templates use Tailwind's `slate` palette (e.g., `slate-900: #0f172a`, `slate-800/50`) and `cyan-500`, `emerald-500`, `violet-500` as accent colors. These are close but not identical to the UX spec. The React app should align more closely with the UX_DESIGN.md tokens while keeping visual continuity with the existing app appearance users are accustomed to.

**Recommendation**: Merge both systems. Use the Jinja2 template's Tailwind slate palette as the base (it is battle-tested and looks good), but extend it with the UX_DESIGN.md semantic tokens as custom CSS properties. This gives us:
- `bg-primary` = `slate-900` (#0f172a) -- slightly bluer than UX spec's pure dark
- `bg-card` = `slate-800` (#1e293b)
- `accent-deal` = `emerald-400` (#34d399) -- Tailwind's emerald is close to `#00ff88`
- `accent-alert` = `amber-400` (#fbbf24) -- close to `#ffaa00`
- `accent-info` = `cyan-400` (#22d3ee) -- close to `#00aaff`

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Price | `JetBrains Mono` | 24px / `text-2xl` | Bold (700) |
| Airport Code | `JetBrains Mono` | 14px / `text-sm` | Medium (500) |
| Body | `Inter` | 14px / `text-sm` | Regular (400) |
| Label | `Inter` | 12px / `text-xs` | Medium (500) |

Both fonts are already loaded in the Jinja2 templates via Google Fonts CDN in `style.css`.

### Spacing

- **Base unit**: 4px (`1` in Tailwind's default spacing scale)
- **Card padding**: 16px (`p-4`)
- **Card gap**: 12px (`gap-3`)
- **Section gap**: 24px (`gap-6`)

These map directly to standard Tailwind spacing values.

### Navigation Structure

| Section | Icon | UX_DESIGN Name | Jinja2 Equivalent |
|---------|------|----------------|-------------------|
| Dashboard | Home | "The Pulse" - deal feed | `/deals/` (Flight Deals) |
| Watchlist | Eye | Active monitors | `/prices/` (My Routes) |
| Awards | Star | Award flight availability | Not yet implemented |
| History | Chart | Price history for tracked routes | Embedded in `/prices/` |
| Settings | Gear | Config, notifications, integrations | `/settings/` |

**Current Jinja2 nav**: Deals, Trip Plans, Routes, Settings, Theme toggle, Live indicator.

**Mapping for React**: The UX spec's 5 sections map to the existing pages plus one future page (Awards). Trip Plans from the Jinja2 UI should remain but is not in the UX_DESIGN.md nav -- it could be a sub-section of Dashboard or its own tab.

### Interaction Patterns

- **Progressive disclosure**: Cards show minimal info; hover/tap reveals detail.
- **Infinite scroll** with "mark as seen" line.
- **Quick actions**: Right-click / long-press context menus.
- **Keyboard navigation**: `j/k` for feed, `Enter` for detail, `w` for watchlist, `d` for dismiss, `?` for shortcuts.
- **Swipe gestures** on mobile: Right to save, Left to dismiss.

### Layout Strategy

- **Bento Grid / Modular Dashboard** for the main dashboard.
- **Desktop**: Collapsible sidebar navigation.
- **Mobile**: Bottom tab bar navigation.
- **Touch targets**: 44px minimum for all interactive elements.

---

## 2. Current Frontend State Analysis

### File Inventory

| File | Purpose | Status |
|------|---------|--------|
| `frontend/package.json` | Dependencies & scripts | Minimal -- no router |
| `frontend/src/main.tsx` | Entry point with QueryClientProvider | Basic |
| `frontend/src/App.tsx` | Single-page app, lists routes | Light-mode only, no routing |
| `frontend/src/components/RouteCard.tsx` | Displays route with stats + chart | Light-mode, uses old Route model |
| `frontend/src/components/PriceChart.tsx` | Recharts line chart for prices | Light-mode, works well |
| `frontend/src/api/client.ts` | Axios API client | Uses old `/api/routes` and `/api/prices` endpoints |
| `frontend/src/index.css` | Tailwind imports + light bg | `bg-gray-50 text-gray-900` -- light mode |
| `frontend/tailwind.config.js` | Bare-minimum config | No dark mode, no theme extensions |
| `frontend/vite.config.ts` | Vite + React plugin | Proxy to `http://backend:8000` |
| `frontend/tsconfig.json` | TypeScript strict config | Good -- strict mode enabled |
| `frontend/postcss.config.js` | PostCSS with Tailwind + autoprefixer | Standard |
| `frontend/index.html` | HTML entry | No fonts, no dark class |

### Key Gaps

1. **No routing**: Single-page App.tsx with no React Router.
2. **No dark mode**: Light-mode-only styling. Tailwind dark mode not configured.
3. **No design system**: No shared tokens, no font configuration.
4. **Stale API models**: Uses `Route` interface (old model) -- backend now uses `SearchDefinition`.
5. **No navigation**: No sidebar, no bottom bar, no layout shell.
6. **No responsive design**: Basic grid only.
7. **Missing fonts**: No Google Fonts loaded in `index.html`.
8. **Light-mode defaults**: `index.css` applies `bg-gray-50 text-gray-900`.

### What To Keep

- **`@tanstack/react-query`**: Already installed and used well for data fetching. Keep.
- **`recharts`**: Used for PriceChart. Keep -- good library for the charting needs.
- **`axios`**: Used for API client. Keep.
- **`PriceChart.tsx`**: The component logic is solid. Will need visual restyling for dark mode but the data flow is correct.
- **Vite + React setup**: Build config is good. The proxy to `backend:8000` is correct for Docker setup.

### What Needs Major Rework

- **`App.tsx`**: Replace entirely with router setup + layout shell.
- **`RouteCard.tsx`**: Restyle for dark mode; update to use `SearchDefinition` model instead of `Route`.
- **`api/client.ts`**: Add new endpoints (deals, trips, settings, search definitions); update existing types.
- **`index.css`**: Replace light-mode defaults with dark-mode-first styling.
- **`tailwind.config.js`**: Extend with design tokens, dark mode, font families.
- **`index.html`**: Add font preloads, dark class on html element.

---

## 3. Current Jinja2 Template Functionality Inventory

### Templates

| Template | Route | Functionality |
|----------|-------|---------------|
| `base.html` | (layout) | Header nav, footer, dark mode toggle, Live indicator, theme persistence via localStorage |
| `deals.html` | `/deals/` | Deal feed with tabs (Local/Regional/Hubs), sort (Best Deals/Newest/Price), deal cards with route, price, source, cabin class, rating badges; AI-enhanced vs basic mode; hover actions; Track Route button |
| `trips.html` | `/trips/` | Trip plan CRUD form, destination vibe chips, origin/destination airport search, trip cards with matches, best flights with booking links, search trigger, match checking |
| `prices.html` | `/prices/` | Route search definitions grid, add route modal with airport autocomplete, stats loading, price refresh, frequency/source configuration, booking options |
| `settings.html` | `/settings/` | Collapsible sections for Location, Notifications, AI & APIs; home airport multi-select, dream destinations, currency, notification providers (ntfy/Discord), quiet hours, AI provider config |
| `status.html` | `/status/` | System status dashboard, scheduler info, notification health, active monitors with health metrics, manual scrape triggers |
| `about.html` | `/about/` | Version display, feature list, changelog (rendered from markdown), links to GitHub/Discord/BMC |

### JavaScript Functionality in Templates

| Feature | Template | Complexity |
|---------|----------|------------|
| Airport autocomplete search | trips, prices, settings | High -- debounced fetch, dropdown rendering |
| Chip/tag multi-select | trips | Medium -- toggle state, hidden inputs |
| Form CRUD (create/edit/delete) | trips, settings | High -- full form handling with validation |
| Price refresh + polling | trips, prices | High -- async operations with status polling |
| Toast notifications | deals | Low -- CSS transition-based |
| Theme toggle | base | Low -- localStorage + class toggle |
| Deal match checking | trips | Medium -- async with result rendering |
| Dynamic stats loading | prices | Medium -- parallel fetch + DOM rendering |
| Hover overlays | deals | Low -- CSS-only with group hover |
| Inline search results rendering | trips | High -- dynamic HTML generation |

### Estimated Lines of JavaScript in Templates

- `deals.html`: ~55 lines (trackRoute function, toast)
- `trips.html`: ~620 lines (CRUD, chips, autocomplete x2, search, matches, polling)
- `prices.html`: ~290 lines (modal, autocomplete x2, CRUD, stats, refresh)
- `settings.html`: ~330 lines (autocomplete x2, CRUD, conditional fields, save)
- `status.html`: ~110 lines (scrape triggers, notifications test)
- `about.html`: ~10 lines (markdown rendering)

**Total**: ~1,415 lines of inline JavaScript that needs to become React components.

### CSS / Styling Patterns in Use

From `/home/jed/dev/walkabout/backend/app/static/style.css`:
- Google Fonts import: Inter (300-700) + JetBrains Mono (400, 500, 700)
- CSS custom properties: `--bg-color: #0f172a`
- Custom scrollbar styling
- Deal card hover animation (translateY + box-shadow)

From `base.html` Tailwind CDN config:
- `darkMode: 'class'` -- class-based dark mode
- Extended `slate-850`, `slate-950` colors
- Custom font families: Inter + JetBrains Mono

---

## 4. Backend API Endpoint Summary

### Route Prefixes (from main.py)

| Prefix | Module | Purpose |
|--------|--------|---------|
| `/deals` | deals.py | Deal feed page + API |
| `/settings` | settings.py | Settings page + API |
| `/trips` | trips.py | Trip plans page + API |
| `/prices` | prices.py | Routes/price tracking page + API |
| `/api/routes` | routes.py | Legacy route CRUD API |
| `/api` | notifications.py | Notification endpoints |
| `/about` | about.py | About page |
| (root) | status.py | Status page |
| (root) | health.py | Health check |

### JSON API Endpoints Available for React

#### Deals
| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/deals/api/deals` | List deals | `{deals: [{id, title, origin, destination, price, currency, airline, cabin_class, source, link, published_at, is_relevant, relevance_reason}], count}` |
| GET | `/deals/api/health/feeds` | Feed health | `{feeds: [...]}` |
| POST | `/deals/api/ingest` | Trigger RSS ingestion | `{results: [...]}` |
| POST | `/deals/api/recalculate-relevance` | Recalculate deal relevance | `{updated: int}` |
| POST | `/deals/api/rate-deals` | Trigger AI deal rating | `{rated: int}` |
| GET | `/deals/api/insights` | Get deal insights | insights object |
| POST | `/deals/api/deals/{id}/dismiss` | Dismiss a deal | `{success: true}` |
| POST | `/deals/api/deals/{id}/restore` | Restore a deal | `{success: true}` |

#### Trips
| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/trips/api/trips` | List trip plans | `{trips: [TripPlanResponse]}` |
| POST | `/trips/api/trips` | Create trip plan | TripPlanResponse |
| GET | `/trips/api/trips/{id}` | Get trip plan | TripPlanResponse |
| PUT | `/trips/api/trips/{id}` | Update trip plan | TripPlanResponse |
| DELETE | `/trips/api/trips/{id}` | Delete trip plan | `{deleted: true}` |
| PUT | `/trips/api/trips/{id}/toggle` | Toggle active state | `{is_active: bool}` |
| GET | `/trips/api/trips/{id}/matches` | Get trip matches | `{trip, matches: [{deal, match_score}]}` |
| POST | `/trips/api/trips/{id}/search` | Search Google Flights | `{status, results}` |
| POST | `/trips/api/trips/{id}/check-matches` | Check RSS matches | `{match_count, top_matches}` |

#### Settings
| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/settings/api/settings` | Get settings | SettingsResponse |
| PUT | `/settings/api/settings` | Update settings | SettingsResponse |
| GET | `/settings/api/airports/search?q=...` | Airport autocomplete | `{results: [{code, name, city, country, region, label}]}` |
| GET | `/settings/api/airports/{code}` | Get airport details | airport object |

#### Prices (Search Definitions)
| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/prices/searches` | List search definitions | `[SearchDefinitionResponse]` |
| POST | `/prices/searches` | Create search definition | SearchDefinitionResponse |
| GET | `/prices/searches/{id}` | Get search definition | SearchDefinitionResponse |
| DELETE | `/prices/searches/{id}` | Deactivate search def | `{status, id}` |
| GET | `/prices/searches/{id}/prices` | Get price history | `[PriceResponse]` |
| GET | `/prices/searches/{id}/stats` | Get price stats | PriceStats |
| GET | `/prices/searches/{id}/latest` | Get latest prices | `[PriceResponse]` |
| GET | `/prices/searches/{id}/options` | Get flight options (cheapest) | `{options: [{departure_date, return_date, price_nzd, airline, stops, booking_url}]}` |
| PUT | `/prices/searches/{id}/frequency` | Update check frequency | `{status, frequency_hours}` |
| PUT | `/prices/searches/{id}/source` | Update price source | `{status, preferred_source}` |
| POST | `/prices/searches/{id}/refresh` | Refresh prices now | `{success, prices_found, source, min_price}` |

#### Notifications
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/notifications/test` | Send test notification |

#### Health
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | Health check |

### API Client Changes Needed

The current React API client (`client.ts`) uses:
- `Route` interface: `{id, origin, destination, name, is_active, scrape_frequency_hours, created_at}`
- `FlightPrice` interface: `{id, route_id, scraped_at, departure_date, return_date, price_nzd, airline, stops, cabin_class, passengers}`
- Endpoints: `/api/routes`, `/api/prices/{routeId}`, `/api/prices/{routeId}/stats`

These are **legacy endpoints** from an older backend design. The backend has since moved to:
- `SearchDefinition` model at `/prices/searches`
- `Deal` model at `/deals/api/deals`
- `TripPlan` model at `/trips/api/trips`

The API client needs a complete rewrite to match the current backend.

---

## 5. React Router Setup Plan

### Required Routes

| Path | Component | Description | Maps to Jinja2 |
|------|-----------|-------------|-----------------|
| `/` | `DashboardPage` | Deal feed ("The Pulse") | `deals.html` |
| `/trips` | `TripsPage` | Trip plan management | `trips.html` |
| `/routes` | `RoutesPage` | Tracked route search definitions | `prices.html` |
| `/settings` | `SettingsPage` | App configuration | `settings.html` |
| `/about` | `AboutPage` | Version & changelog | `about.html` |

The `/status` page from Jinja2 is a developer/admin tool and does not need a React equivalent initially.

### React Router v7 Setup

React Router v7 (the latest stable as of 2026) is the recommended version. It provides:
- File-based or config-based routing
- Data loaders and actions (optional, can use react-query instead)
- Nested layouts
- Type safety improvements

**However**, since we already have `@tanstack/react-query` for data fetching, we should use React Router purely for navigation and layout, not for data loading. This keeps our architecture clean: React Router for routing, React Query for server state.

### Proposed Router Structure

```tsx
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { TripsPage } from './pages/TripsPage'
import { RoutesPage } from './pages/RoutesPage'
import { SettingsPage } from './pages/SettingsPage'
import { AboutPage } from './pages/AboutPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="trips" element={<TripsPage />} />
          <Route path="routes" element={<RoutesPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="about" element={<AboutPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

### AppLayout Component

The `AppLayout` component renders the navigation shell (sidebar on desktop, bottom tabs on mobile) and uses `<Outlet />` for page content.

```tsx
// src/layouts/AppLayout.tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from '../components/navigation/Sidebar'
import { BottomTabs } from '../components/navigation/BottomTabs'

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      {/* Desktop sidebar */}
      <Sidebar className="hidden md:flex" />

      {/* Main content area */}
      <main className="md:ml-64 pb-16 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile bottom tabs */}
      <BottomTabs className="md:hidden" />
    </div>
  )
}
```

---

## 6. Tailwind Dark Mode + Design Token Configuration

### Dark Mode Strategy

Use **class-based dark mode** (`darkMode: 'class'`) to match the Jinja2 templates. Since the app is dark-mode-first, the `dark` class should be applied by default on `<html>`. Light mode can be toggled via a user preference stored in localStorage.

### Recommended `tailwind.config.js`

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Extended slate shades to match Jinja2 templates
        slate: {
          850: '#1e293b',
          950: '#020617',
        },
        // Semantic accent colors from UX_DESIGN.md
        deal: {
          good: '#34d399',     // emerald-400 (close to #00ff88)
          alert: '#fbbf24',    // amber-400 (close to #ffaa00)
          info: '#22d3ee',     // cyan-400 (close to #00aaff)
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      spacing: {
        // UX_DESIGN.md uses 4px base unit -- Tailwind already does this
        // Card padding: 16px = p-4 (already standard)
        // Card gap: 12px = gap-3 (already standard)
        // Section gap: 24px = gap-6 (already standard)
      },
    },
  },
  plugins: [],
}
```

### CSS Custom Properties

Add CSS custom properties in `index.css` for dynamic theming:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* Light mode tokens */
    --bg-primary: #f1f5f9;      /* slate-100 */
    --bg-card: #ffffff;
    --text-primary: #0f172a;     /* slate-900 */
    --text-secondary: #64748b;   /* slate-500 */
  }

  .dark {
    --bg-primary: #0f172a;       /* slate-900 */
    --bg-card: #1e293b;          /* slate-800 */
    --text-primary: #f0f0f0;
    --text-secondary: #888888;
  }

  html {
    @apply antialiased;
  }

  body {
    @apply bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-sans;
    @apply selection:bg-cyan-500 selection:text-white;
  }
}
```

### Theme Persistence

```tsx
// src/hooks/useTheme.ts
import { useState, useEffect } from 'react'

export function useTheme() {
  const [isDark, setIsDark] = useState(() => {
    if (typeof window === 'undefined') return true
    return localStorage.theme !== 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.theme = 'dark'
    } else {
      root.classList.remove('dark')
      localStorage.theme = 'light'
    }
  }, [isDark])

  const toggle = () => setIsDark(prev => !prev)

  return { isDark, toggle }
}
```

---

## 7. Font Loading Strategy

### Current State

- Jinja2 templates: Fonts loaded via CSS `@import` in `/static/style.css`:
  ```css
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
  ```

### Recommended Approach for React/Vite

Use `<link>` tags in `index.html` with `preconnect` hints for best performance:

```html
<!-- index.html -->
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Walkabout | Your Flight Deal Hub</title>

  <!-- Preconnect to Google Fonts for faster loading -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />

  <!-- Load fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
</head>
<body class="dark">
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
```

**Why not npm packages (e.g., `@fontsource/inter`)?**
- Google Fonts CDN is already used in the Jinja2 templates, so consistency is maintained.
- CDN provides better caching (user may already have these fonts cached from other sites).
- Simpler setup -- no additional Vite configuration needed.
- If offline/self-hosted is later needed, switching to `@fontsource` packages is straightforward.

**Alternative (for self-hosted/Unraid without internet)**: Install `@fontsource/inter` and `@fontsource/jetbrains-mono` npm packages and import in `main.tsx`. This would be a future enhancement for the Docker self-hosted use case.

---

## 8. Navigation Component Design

### Desktop: Collapsible Sidebar

Based on the UX_DESIGN.md specification and the existing Jinja2 header nav pattern.

```
+------------------+--------------------------------------+
| WALKABOUT        |                                      |
| [logo]           |        Main Content Area             |
|                  |                                      |
| Dashboard   (/)  |                                      |
| Trips    (/trips)|                                      |
| Routes  (/routes)|                                      |
| Settings (/set.) |                                      |
|                  |                                      |
| [theme toggle]   |                                      |
| [LIVE indicator] |                                      |
+------------------+--------------------------------------+
```

**Key behaviors**:
- Fixed on left side, 256px wide (`w-64`)
- Collapsible to icon-only mode (64px / `w-16`) via toggle button
- Active link highlighted with background + accent color
- Collapsed state persisted to localStorage
- Contains: logo, nav links, theme toggle, live indicator

### Mobile: Bottom Tab Bar

```
+--------------------------------------------------+
|                  Main Content                     |
|                                                   |
+--------------------------------------------------+
| [Home] [Trips] [Routes] [Settings]               |
+--------------------------------------------------+
```

**Key behaviors**:
- Fixed to bottom of viewport
- 4 primary tabs with icons and labels
- 44px minimum touch targets (as per UX spec)
- Active tab highlighted with accent color
- Safe area inset for notched devices (`pb-safe`)
- Hidden when keyboard is visible (iOS/Android)

### Nav Items

```tsx
const NAV_ITEMS = [
  { path: '/',         label: 'Dashboard', icon: HomeIcon },
  { path: '/trips',    label: 'Trips',     icon: MapIcon },
  { path: '/routes',   label: 'Routes',    icon: ChartIcon },
  { path: '/settings', label: 'Settings',  icon: GearIcon },
]
```

### Icon Strategy

Use inline SVG icons matching the Jinja2 templates (which use Heroicons-style SVG). Two options:

1. **@heroicons/react** (recommended): Official React package from the same team behind Tailwind. Already matches the existing icon style.
2. **lucide-react**: Popular alternative, slightly different style.

Recommendation: **@heroicons/react** for consistency with existing Jinja2 template icons.

### Responsive Breakpoints

| Breakpoint | Navigation | Layout |
|------------|-----------|--------|
| `< md` (768px) | Bottom tab bar | Single column, full width |
| `>= md` (768px) | Sidebar (collapsible) | Content with left margin |
| `>= lg` (1024px) | Sidebar (expanded by default) | Content with left margin |

---

## 9. Shared Component Inventory

### Layout Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `AppLayout` | Main layout shell (sidebar + content + bottom tabs) | P0 |
| `Sidebar` | Desktop navigation sidebar | P0 |
| `BottomTabs` | Mobile bottom tab navigation | P0 |
| `PageHeader` | Page title bar with actions (matches Jinja2 header sections) | P0 |

### UI Primitives

| Component | Purpose | Priority |
|-----------|---------|----------|
| `Card` | Base card component (dark bg, border, rounded) | P0 |
| `Button` | Primary/secondary/ghost button variants | P0 |
| `Badge` | Cabin class, deal rating, status badges | P0 |
| `LoadingSpinner` | Consistent loading indicator | P0 |
| `EmptyState` | Empty state with icon, title, description, action | P1 |
| `Toast` | Notification toast (success/error/info) | P1 |
| `Modal` | Dialog overlay (for add route, confirmations) | P1 |
| `Toggle` | On/off switch (for active state, notification toggles) | P1 |

### Form Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `AirportSearch` | Airport autocomplete input (used in trips, routes, settings) | P0 |
| `ChipSelect` | Multi-select chip/tag component (destination vibes) | P1 |
| `Select` | Styled select dropdown | P1 |
| `Input` | Styled text/number input | P1 |
| `DateInput` | Styled date input with dark mode support | P1 |

### Data Display Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `DealCard` | Flight deal card (origin, destination, price, source, actions) | P0 |
| `TripCard` | Trip plan card with matches and actions | P1 |
| `RouteCard` (reworked) | Search definition card with stats and options | P1 |
| `PriceChart` (reworked) | Dark-mode price chart | P1 |
| `FlightOption` | Cheapest flight option with booking link | P1 |
| `SourceBadge` | RSS source indicator (colored dot + name) | P1 |

### Utility Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `ThemeToggle` | Dark/light mode switch | P0 |
| `LiveIndicator` | Pulsing green dot with "LIVE" text | P1 |
| `PriceDisplay` | Formatted price with currency (uses JetBrains Mono) | P0 |
| `AirportCode` | Styled airport code (uses JetBrains Mono) | P0 |

---

## 10. Migration Strategy

### Principle: Parallel Operation

The React frontend and Jinja2 templates will coexist during the transition. Users access the Jinja2 UI at the existing routes; the React app is developed at a separate path or port.

### Architecture

```
User Request
    |
    v
FastAPI (backend:8000)
    |
    +-- /deals/, /trips/, /prices/, /settings/ --> Jinja2 templates (existing)
    +-- /api/*, /deals/api/*, /trips/api/*, /settings/api/*, /prices/searches/* --> JSON APIs (existing)
    +-- /app/* --> React SPA (new, served via static files or proxy)

Vite Dev Server (frontend:3000)
    |
    +-- /* --> React SPA
    +-- /api/* --> Proxy to backend:8000 (via vite.config.ts)
```

### Phase 1: Foundation (This Feature - walkabout-awa.5)

1. Set up design tokens, dark mode, fonts in Tailwind config
2. Install React Router and set up route structure
3. Build AppLayout with Sidebar + BottomTabs
4. Create shared UI primitives (Card, Button, Badge, etc.)
5. Create DashboardPage shell (empty, just layout)
6. Update API client with new endpoint types
7. React app runs on Vite dev server (port 3000), proxied to backend

### Phase 2: Page-by-Page Migration (Future Features)

1. **Dashboard/Deals page**: Port deal cards, tabs, sorting, actions
2. **Routes page**: Port search definition CRUD, stats, price refresh
3. **Trips page**: Port trip plan CRUD, matching, search
4. **Settings page**: Port all settings sections
5. **About page**: Port version/changelog display

### Phase 3: Cutover (Future)

1. Build React app for production (`vite build`)
2. Serve built React app from FastAPI as static files at root
3. Move Jinja2 templates to legacy routes or remove
4. Update Docker setup to serve React from backend

### Vite Proxy Configuration

The current `vite.config.ts` proxies `/api` to backend. Expand this to proxy all backend API paths:

```ts
proxy: {
  '/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
  '/deals/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
  '/trips/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
  '/settings/api': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
  '/prices/searches': {
    target: 'http://backend:8000',
    changeOrigin: true,
  },
}
```

### API Client Restructure

The new API client should be organized by domain:

```
src/api/
  client.ts          -- axios instance configuration
  types.ts           -- all TypeScript interfaces
  deals.ts           -- deal API functions
  trips.ts           -- trip plan API functions
  settings.ts        -- settings API functions
  prices.ts          -- search definition + price API functions
  airports.ts        -- airport search API functions
```

### Key Type Mappings

| Old (client.ts) | New (backend model) | Notes |
|-----------------|---------------------|-------|
| `Route` | `SearchDefinition` | Different fields, different endpoints |
| `FlightPrice` | `FlightPrice` | Similar but `route_id` -> `search_definition_id` |
| `PriceStats` | `PriceStats` | Similar, added `price_trend` |
| (none) | `Deal` | New -- RSS deal from feeds |
| (none) | `TripPlan` | New -- trip plan with destinations/vibes |
| (none) | `UserSettings` | New -- all settings |
| (none) | `Airport` | New -- airport autocomplete result |

---

## 11. NPM Dependencies

### Keep (Already Installed)

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.2.0 | UI library |
| `react-dom` | ^18.2.0 | DOM renderer |
| `@tanstack/react-query` | ^5.17.0 | Server state management |
| `recharts` | ^2.10.0 | Price charts |
| `axios` | ^1.6.0 | HTTP client |
| `typescript` | ^5.3.0 | Type checking |
| `vite` | ^5.0.0 | Build tool |
| `@vitejs/plugin-react` | ^4.2.0 | Vite React plugin |
| `tailwindcss` | ^3.4.0 | CSS framework |
| `postcss` | ^8.4.0 | CSS processing |
| `autoprefixer` | ^10.4.0 | CSS vendor prefixes |
| `@types/react` | ^18.2.0 | React type definitions |
| `@types/react-dom` | ^18.2.0 | ReactDOM type definitions |

### Add (New Dependencies)

| Package | Version | Purpose | Type |
|---------|---------|---------|------|
| `react-router-dom` | ^7.x | Client-side routing | runtime |
| `@heroicons/react` | ^2.x | Icon library (matches Jinja2 style) | runtime |
| `clsx` | ^2.x | Conditional class names utility | runtime |

### Optional / Later

| Package | Purpose | When |
|---------|---------|------|
| `@fontsource/inter` | Self-hosted Inter font | If offline mode needed |
| `@fontsource/jetbrains-mono` | Self-hosted JetBrains Mono font | If offline mode needed |
| `framer-motion` | Animations (page transitions, card animations) | Phase 2+ |
| `react-hot-toast` | Toast notifications (alternative to custom) | Phase 2+ |
| `@headlessui/react` | Accessible UI primitives (modals, dropdowns) | Phase 2+ |

### Not Needed

| Package | Why Not |
|---------|---------|
| `@reduxjs/toolkit` | React Query handles server state; React state is sufficient for UI state |
| `zustand` | Not needed at this scale; `useContext` + `useState` sufficient |
| `styled-components` / `emotion` | Using Tailwind CSS |
| `next.js` | This is a SPA, not SSR. Vite is the right tool. |
| `chart.js` | Already using recharts |

---

## 12. Files That Will Need Changes

### Existing Files to Modify

| File | Changes |
|------|---------|
| `frontend/package.json` | Add react-router-dom, @heroicons/react, clsx |
| `frontend/tailwind.config.js` | Add darkMode, extend colors, fontFamily |
| `frontend/vite.config.ts` | Expand proxy paths for all backend API routes |
| `frontend/index.html` | Add font preloads, dark class on body, update title |
| `frontend/src/index.css` | Replace light-mode defaults with dark-mode-first theming |
| `frontend/src/main.tsx` | Wrap App in BrowserRouter (or move routing to App) |
| `frontend/src/App.tsx` | Replace with router configuration + AppLayout |
| `frontend/src/api/client.ts` | Rewrite with new types and endpoint structure |
| `frontend/src/components/PriceChart.tsx` | Restyle for dark mode (line colors, axis colors) |
| `frontend/src/components/RouteCard.tsx` | Restyle for dark mode; update to SearchDefinition model |

### New Files to Create

| File | Purpose |
|------|---------|
| **Layouts** | |
| `frontend/src/layouts/AppLayout.tsx` | Main layout with sidebar + bottom tabs + outlet |
| **Navigation** | |
| `frontend/src/components/navigation/Sidebar.tsx` | Desktop sidebar navigation |
| `frontend/src/components/navigation/BottomTabs.tsx` | Mobile bottom tab bar |
| `frontend/src/components/navigation/NavItem.tsx` | Individual nav link component |
| **Pages** | |
| `frontend/src/pages/DashboardPage.tsx` | Deal feed page (shell initially) |
| `frontend/src/pages/TripsPage.tsx` | Trip plans page (shell initially) |
| `frontend/src/pages/RoutesPage.tsx` | Route tracking page (shell initially) |
| `frontend/src/pages/SettingsPage.tsx` | Settings page (shell initially) |
| `frontend/src/pages/AboutPage.tsx` | About page (shell initially) |
| **UI Primitives** | |
| `frontend/src/components/ui/Card.tsx` | Base card component |
| `frontend/src/components/ui/Button.tsx` | Button with variants |
| `frontend/src/components/ui/Badge.tsx` | Status/label badge |
| `frontend/src/components/ui/LoadingSpinner.tsx` | Loading indicator |
| `frontend/src/components/ui/EmptyState.tsx` | Empty state display |
| `frontend/src/components/ui/PageHeader.tsx` | Page title + actions header |
| **Data Display** | |
| `frontend/src/components/PriceDisplay.tsx` | Formatted price with currency |
| `frontend/src/components/AirportCode.tsx` | Styled airport code |
| **Hooks** | |
| `frontend/src/hooks/useTheme.ts` | Dark/light mode management |
| **API** | |
| `frontend/src/api/types.ts` | All TypeScript interfaces |
| `frontend/src/api/deals.ts` | Deal API functions |
| `frontend/src/api/trips.ts` | Trip plan API functions |
| `frontend/src/api/settings.ts` | Settings API functions |
| `frontend/src/api/prices.ts` | Search definition + price API functions |
| `frontend/src/api/airports.ts` | Airport search API functions |

### Summary Count

- **Existing files to modify**: 10
- **New files to create**: ~25
- **Total files touched**: ~35

---

## Appendix: Key Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Router | React Router v7 | Latest stable, wide ecosystem, no data loader conflict with React Query |
| Icons | @heroicons/react | Matches existing Jinja2 template icon style |
| Dark mode | Class-based, dark-first | Matches UX_DESIGN.md spec and existing Jinja2 approach |
| Fonts | Google Fonts CDN in index.html | Consistent with Jinja2, good caching |
| State management | React Query + React state | Already in use, sufficient for this app's complexity |
| CSS | Tailwind with extended theme | Already in use, matches Jinja2 template styling |
| Migration | Parallel operation | React and Jinja2 coexist; page-by-page migration |
| Color palette | Merge UX spec with Jinja2 Tailwind palette | Keep visual continuity while aligning with design spec |
