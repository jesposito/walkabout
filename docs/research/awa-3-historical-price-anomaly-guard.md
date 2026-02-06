# Research: Historical Price Anomaly Guard (walkabout-awa.3)

## Summary

Adding `confidence` float and `is_suspicious` boolean columns to FlightPrice model, with pre-storage validation comparing against 30-day median.

## Current State

### FlightPrice Model (`backend/app/models/flight_price.py`, 50 lines)
- Columns: id, search_definition_id, scraped_at, departure_date, return_date, price_nzd, airline, stops, duration_minutes, raw_data
- TimescaleDB hypertable partitioned by scraped_at
- Confidence currently stored in `raw_data` JSON, not indexed

### PriceAnalyzer (`backend/app/services/price_analyzer.py`, 207 lines)
- `analyze_price()` returns DealAnalysis with z_score, robust_z_score, median, MAD, percentile
- `get_price_history()` queries 90-day history by search_definition_id
- `robust_z_score()` uses median + MAD (Oracle approved)
- `is_absolute_new_low()` flags new lows within 2% margin
- Threshold: `deal_threshold_z_score = -1.5`

### ScrapingService (`backend/app/services/scraping_service.py`, 323 lines)
- `_process_prices()` at line 156: confidence gating already exists
- MIN_CONFIDENCE_FOR_STORAGE = 0.5, MIN_CONFIDENCE_FOR_DEALS = 0.6
- Creates FlightPrice objects at line 205, commits at 217
- Integration point: between FlightPrice creation and `self.db.add(price)` at line 215

### Config (`backend/app/config.py`, 39 lines)
- Pydantic BaseSettings with .env file
- Existing thresholds: deal_threshold_z_score, min_history_for_analysis

### Migration System (`backend/alembic/`)
- 4 existing migrations (001-004)
- SQLite fallback via `ensure_sqlite_columns()` in `database.py`

## What Needs to Change

| File | Change | Impact |
|------|--------|--------|
| `models/flight_price.py` | Add `confidence` (Numeric(5,4)) and `is_suspicious` (Boolean) columns | Schema |
| `alembic/versions/005_price_anomaly_guard.py` | New migration adding columns + indexes | DDL |
| `database.py` | Update `ensure_sqlite_columns()` with new columns | SQLite compat |
| `config.py` | Add `price_anomaly_threshold_percent: float = 300.0` | Config |
| `services/scraping_service.py` | Set confidence/is_suspicious on FlightPrice before add | ~5 lines |
| `services/price_analyzer.py` | Add `is_price_suspicious()` method using 30-day median | ~30 lines |

## Integration Architecture

```
_process_prices()
  ├── Confidence gating (existing, 0.5 threshold)
  ├── Create FlightPrice object
  ├── [NEW] Set price.confidence from extraction metadata
  ├── [NEW] Check 30-day median → set price.is_suspicious
  ├── self.db.add(price)
  ├── self.db.commit()
  └── Deal analysis (existing, only if confidence >= 0.6 AND NOT suspicious)
```

## Anomaly Detection Logic

1. Get 30-day price history for search_definition_id
2. If insufficient history (< 5 samples): not suspicious (fail open)
3. Calculate 30-day median
4. Flag suspicious if:
   - Price > 300% above median (spike)
   - Price < 20% of median (crash, >80% below)
5. Store confidence from extraction raw_data as indexed column
6. Exclude suspicious prices from deal analysis and notifications

## Migration Snippet

```python
# 005_price_anomaly_guard.py
op.add_column('flight_prices', sa.Column('confidence', sa.Numeric(5, 4), nullable=True))
op.add_column('flight_prices', sa.Column('is_suspicious', sa.Boolean(), server_default='0', nullable=False))
```

```python
# database.py ensure_sqlite_columns()
("flight_prices", "confidence", "REAL"),
("flight_prices", "is_suspicious", "BOOLEAN DEFAULT 0"),
```
