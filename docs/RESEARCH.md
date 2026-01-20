# Research Notes

## Flight Fare APIs

### Cash Fares

| API/Service | Free Tier | Notes |
|-------------|-----------|-------|
| **SerpAPI (Google Flights)** | 100/mo free, ~$50/mo | Most accurate consumer prices |
| **Skyscanner API** | Partner program | Requires affiliate approval |
| **Amadeus Self-Service** | 2,000/mo free (test) | Prices can differ from airline websites |
| **Kiwi.com (Tequila)** | Free tier | Good for multi-city |

### Award Availability

| Service | API Access | Cost |
|---------|------------|------|
| **Seats.aero** | Pro API (1,000/day) | ~$10/mo |
| **AwardFares** | No public API | $9-20/mo web only |

## Hotel/Resort APIs

- Booking.com Affiliate API (requires partnership)
- SerpAPI Hotels (pay per search)
- Custom scraping for price history tracking

## Existing Projects

- `romankh3/flights-monitoring` - Java/Spring + Skyscanner (2020)
- `arijitroy003/flight-tracker` - Amadeus + Skyscanner (2025)
- `lg/awardwiz` - Archived Sept 2024

## Key Findings

1. No official airline APIs for award availability - all tools scrape
2. Alaska + Hawaiian "Atmos Rewards" supported by Seats.aero
3. No NZ-focused solution exists - gap worth filling
4. Google Flights via SerpAPI most reliable for consumer prices
