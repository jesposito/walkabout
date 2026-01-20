# Walkabout

Self-hosted travel deal monitor for tracking flight prices, award availability, and resort deals.

## Features (Planned)

- **Multi-destination monitoring** - Track flights from any origin to any destination
- **Cash fare tracking** - Daily price monitoring via Google Flights
- **Award flight availability** - Track miles/points redemption options
- **Miles program management** - Know if you have enough points for a trip
- **Resort deal detection** - Historical price tracking to identify real deals vs fake discounts
- **Smart alerts** - Notifications when prices drop or award seats open
- **Lead time analysis** - Recommendations on when to book

## Architecture

```
Docker Compose Stack
├── Frontend (React + Tailwind)
├── Backend (FastAPI)
├── Scheduler (Celery)
├── Database (PostgreSQL + TimescaleDB)
└── Cache/Queue (Redis)
```

## Status

🚧 In planning phase

## License

MIT
