# Walkabout: UX/UI Deep Dive & Information Architecture

## Design Philosophy: "The Calm Flight Deck"

**Aesthetic Direction:** *Rationalist Utility / Swiss International Style*

- **Tone:** Precision, clarity, and anticipation. Not a marketing site, but a professional tool for decision-making.
- **Typography:** Monospace for data (prices, dates, airport codes) paired with a high-legibility sans-serif for UI elements.
- **Palette:** Dark mode native (Unraid context). High-contrast signals for "Good Deal" (Electric Green) vs "Alert" (Amber). Deep charcoal backgrounds to reduce eye strain during long research sessions.

---

## 1. User Persona & Mental Model

**The "Self-Host Traveler"**

- **Context:** Runs Unraid server at home. Comfortable with Docker/Env vars but tired of maintaining complex configs.
- **Goal:** Wants to be "in the know" without constantly searching generic travel sites. Wants raw data filtered by their specific constraints.
- **Pain Points:** Notification spam, missing a "glitch fare", cluttered interfaces with ads.
- **Mental Model:** "Set and Forget" + "Morning Coffee Review". The system watches 24/7; I check it when I have intent or when alerted.

---

## 2. Primary User Journeys

### A. The "Morning Coffee" (Opportunistic Browsing)

- **Trigger:** Daily routine or a "New Deals" badge.
- **Flow:**
  1. User opens Dashboard.
  2. Glances at **"The Pulse"** (a feed of high-value deals from AKL).
  3. Scans for "Unicorns" (90%+ off or rare business class awards).
  4. Dismisses irrelevant deals (swipes/clicks "Not Interested").
  5. Bookmarks interesting ones to "Trip Ideas".

### B. The "Sniper" (Targeted Monitoring)

- **Trigger:** Specific trip need (e.g., "Japan in October").
- **Flow:**
  1. User navigates to **"Watchlist"**.
  2. Adds new Monitor: AKL -> TYO (All Airports).
  3. Sets constraints: "Business Class Only" OR "Price < $1000".
  4. System immediately shows *current* best matches (instant gratification).
  5. User toggles "High Priority Alert" for this specific monitor.

### C. The "Flexi-Planner" (Similarity & Discovery)

- **Trigger:** "I want to go to Europe, but it's too expensive."
- **Flow:**
  1. User views a high-priced London deal.
  2. System suggestions widget: "Cheaper Alternatives near LHR".
  3. Shows Paris or Amsterdam prices + train connection viability.
  4. User pivots search to these hubs.

### D. Alert Triage (Notification Management)

- **Trigger:** Mobile push notification via ntfy.
- **Flow:**
  1. Notification: "AKL->LAX dropped 40% ($800)".
  2. Tap notification -> Deep links to specific **Deal Detail View**.
  3. Action buttons: "Book (Airline Link)", "Track Price", "Ignore".

### E. First-Time Setup (Onboarding)

- **Trigger:** First container start.
- **Flow:**
  1. Welcome screen: "Let's set up your flight radar"
  2. Home airport selection (auto-suggest based on timezone)
  3. Add 3-5 destinations you're interested in
  4. Notification setup (ntfy topic or webhook URL)
  5. Optional: Seats.aero API key for award tracking
  6. "Start Monitoring" -> First feed fetch begins

---

## 3. Information Architecture (Sitemap)

The app structure is flat to reduce click-depth.

### Global Navigation (Sidebar/Bottom Bar)

| Section | Icon | Description |
|---------|------|-------------|
| **Dashboard** | Home | The Pulse - aggregated deal feed |
| **Watchlist** | Eye | Active monitors for specific routes |
| **Awards** | Star | Award flight availability |
| **History** | Chart | Price history for tracked routes |
| **Settings** | Gear | Config, notifications, integrations |

### Detail Views (Modals/Overlays)

- **Deal Card:** Price history, Airline, Stops, Booking Link
- **Destination Insight:** Seasonality, Average Price from AKL
- **Award Search:** Available dates, Cabin, Points required

---

## 4. Dashboard Layout & Composition

**Layout Strategy:** *Bento Grid / Modular Dashboard*

### Top Tier: Status & Urgency

- **System Health:** Subtle indicator (API connection status, last scrape time)
- **"Unicorn" Banner:** Only appears if a deal is >2 standard deviations better than average. Demands attention.

### Middle Tier: The Feed (The "Pulse")

**Card-based layout with clear data hierarchy:**

| Priority | Element | Treatment |
|----------|---------|-----------|
| 1 | Destination + Price | Large, bold |
| 2 | Dates + Airline | Secondary text |
| 3 | "40% below avg" badge | Color-coded chip |
| 4 | Actions | Icon buttons |

**Card Actions:**
- Watch (Eye icon) - Add to watchlist
- Book (External link) - Opens airline/OTA
- Dismiss (X) - Hide from feed

### Right Panel / Bottom Sheet (Context)

- **"Smart Suggestions":** "You're watching TYO. Did you know KIX is $300 cheaper?"
- **Price Trends:** Sparkline graph showing trend for your watched routes

---

## 5. Interaction Patterns & Progressive Disclosure

### Hover/Tap for Detail
Cards show minimal info (Price/Dest/Dates). Hovering reveals "Stops", "Layover Duration", "Source" (which blog).

### Infinite Scroll with "Mark as Seen"
Feed loads more as you scroll. Clear visual line separates "new" from "seen" items.

### Quick Actions (Context Menu)
- **Right Click / Long Press on Destination:** "Add to Watchlist", "Block Destination"
- **Swipe (Mobile):** Right to Save, Left to Dismiss

### Keyboard Navigation
- `j/k` - Navigate feed items
- `Enter` - Open detail view
- `w` - Add to watchlist
- `d` - Dismiss
- `?` - Show shortcuts

---

## 6. Notification Strategy: "Signal over Noise"

### Tiered Notification System

| Tier | Trigger | Channel | Example |
|------|---------|---------|---------|
| **Critical** | Exact watchlist match, Unicorn deal | Push + Sound | "AKL->TYO $599 RT - 50% below avg" |
| **Informational** | General good deals | Daily Digest | "5 new deals from AKL this week" |
| **Silent** | Minor updates | In-App Badge | "System updated" |

### Anti-Fatigue Mechanisms

1. **Cooldown per route:** Same route won't alert twice in 24h unless price drops further
2. **Dedupe key:** Same deal from multiple blogs = 1 notification
3. **Quiet hours:** No push between 10pm-7am (configurable)
4. **Sensitivity slider:** User controls "Strict" (only amazing) to "Chatty" (tell me everything)

### Notification Content

```
Title: AKL -> LAX dropped 40%
Body: Round-trip from $800 NZD (Apr 15-25)
      18-month low price
Actions: [View Deal] [Dismiss]
```

---

## 7. Configuration UX (Unraid-Friendly)

### First Run Wizard (3 steps max)

1. **Home Base**
   - Pre-filled based on timezone detection
   - Single dropdown with search
   
2. **Interests**
   - "Where do you dream of going?"
   - Tag-style multi-select with popular suggestions
   
3. **Notifications**
   - ntfy topic URL input with "Test" button
   - Webhook URL alternative

### Settings Page (Progressive Disclosure)

**Basic Settings (always visible):**
- Home airport
- Watched destinations
- Notification URL

**Advanced Settings (collapsible):**
- Feed check interval
- Seats.aero API key
- Deal threshold percentage
- Quiet hours
- Debug logging

---

## 8. Mobile Considerations

Since this is a web-app, it must be responsive (PWA candidate).

### Navigation
- Bottom tab bar on mobile
- Collapsible sidebar on tablet/desktop

### Touch Targets
- 44px minimum for all interactive elements
- Swipe gestures for quick actions

### Data Density
- Reduce columns on mobile
- Price + Destination prominent
- Airline + Stops as icons

### Offline/Sleep Handling
- Show cached data immediately
- "Waking up..." spinner if Unraid is spinning up drives
- Optimistic UI for interactions

---

## 9. Empty States & Error Handling

### No Deals Yet
```
"Your flight radar is warming up..."
First deals will appear after the next scheduled check.
[Check Now] button
```

### No Watchlist Items
```
"Nothing on your radar"
Add routes you care about to get personalized alerts.
[Add Route] button
```

### Feed Source Down
```
[!] Secret Flying feed unavailable
Last successful: 2 hours ago
Other sources working normally.
```

### API Key Missing
```
Award tracking disabled
Add your Seats.aero API key in Settings to enable.
[Go to Settings]
```

---

## 10. Visual Design Tokens

### Colors (Dark Mode)

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#1a1a1a` | Main background |
| `--bg-card` | `#252525` | Card background |
| `--text-primary` | `#f0f0f0` | Main text |
| `--text-secondary` | `#888888` | Secondary text |
| `--accent-deal` | `#00ff88` | Good deal indicator |
| `--accent-alert` | `#ffaa00` | Warning/alert |
| `--accent-info` | `#00aaff` | Information |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Price | `JetBrains Mono` | 24px | Bold |
| Airport Code | `JetBrains Mono` | 14px | Medium |
| Body | `Inter` | 14px | Regular |
| Label | `Inter` | 12px | Medium |

### Spacing

- Base unit: 4px
- Card padding: 16px
- Card gap: 12px
- Section gap: 24px
