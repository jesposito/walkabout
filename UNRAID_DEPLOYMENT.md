# Walkabout Unraid Deployment Guide

Deploy Walkabout Phase 1a on your Unraid server with custom network support.

## Quick Start (ansiblenet)

```bash
# 1. SSH to your Unraid server
ssh root@your-unraid-ip

# 2. Create deployment directory
mkdir -p /mnt/user/appdata/walkabout
cd /mnt/user/appdata/walkabout

# 3. Download deployment files
curl -o docker-compose.yml https://raw.githubusercontent.com/jesposito/walkabout/main/docker-compose.prod.yml
curl -o .env.example https://raw.githubusercontent.com/jesposito/walkabout/main/.env.example

# 4. Create environment file
cp .env.example .env
nano .env  # Edit with your settings (see Configuration section)

# 5. Create data directories
mkdir -p ./data/{screenshots,html_snapshots,backups}

# 6. Deploy with ansiblenet
docker network create ansiblenet --driver bridge || true  # Create if doesn't exist
USE_EXTERNAL_NETWORK=true EXTERNAL_NETWORK_NAME=ansiblenet docker-compose up -d

# 7. Wait for startup and check status
sleep 30
docker-compose ps
curl -f http://localhost:8000/ping
```

## Network Configurations

### Option 1: ansiblenet (Custom Bridge Network)
```bash
# Create the network if it doesn't exist
docker network create ansiblenet --driver bridge

# Deploy with ansiblenet
USE_EXTERNAL_NETWORK=true EXTERNAL_NETWORK_NAME=ansiblenet docker-compose up -d
```

### Option 2: Default Bridge Network
```bash
# Use default Docker networking
docker-compose up -d
```

### Option 3: Host Network (Maximum Performance)
```bash
# Add to docker-compose override
echo "
version: '3.8'
services:
  backend:
    network_mode: host
  ntfy:
    network_mode: host
" > docker-compose.override.yml

docker-compose up -d
```

## Configuration

### Required Environment Variables

Create `.env` file with:

```bash
# Database password (REQUIRED)
DB_PASSWORD=your_secure_password_here

# Notification settings
NTFY_TOPIC=walkabout-deals

# Network ports (if using custom networks)
BACKEND_PORT=8000
NTFY_PORT=8080

# Base URL for notification links
BASE_URL=http://your-unraid-ip:8000
```

### Optional Settings

```bash
# External network (for ansiblenet)
USE_EXTERNAL_NETWORK=true
EXTERNAL_NETWORK_NAME=ansiblenet

# API keys (for Phase 2 features)
ANTHROPIC_API_KEY=your_claude_key
SEATS_AERO_API_KEY=your_seats_key
```

## Service Access

Once deployed, access services at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Main Dashboard** | `http://your-unraid-ip:8000/` | Status page with manual controls |
| **API Documentation** | `http://your-unraid-ip:8000/docs` | Interactive API explorer |
| **Health Check** | `http://your-unraid-ip:8000/ping` | Simple health endpoint |
| **Notifications** | `http://your-unraid-ip:8080/walkabout-deals` | Subscribe to ntfy alerts |

## Initial Setup

### 1. Create Your First Flight Monitor

```bash
# SSH to Unraid and run:
docker-compose exec backend python -c "
import sys
sys.path.append('/app')

from app.database import SessionLocal
from app.models import SearchDefinition, TripType, CabinClass, StopsFilter

db = SessionLocal()

# Create AKL → HNL monitor for your family
search_def = SearchDefinition(
    origin='AKL',
    destination='HNL', 
    name='Auckland to Honolulu (Family of 4)',
    trip_type=TripType.ROUND_TRIP,
    adults=2,
    children=2,
    cabin_class=CabinClass.ECONOMY,
    departure_days_min=60,    # 60-90 days from now
    departure_days_max=90,
    trip_duration_days_min=7, # 7-14 day trips
    trip_duration_days_max=14,
    is_active=True
)

db.add(search_def)
db.commit()
print(f'✅ Created: {search_def.display_name}')
db.close()
"
```

### 2. Test the System

```bash
# Trigger a manual scrape
curl -X POST http://your-unraid-ip:8000/api/scrape/manual/1

# Test notifications
curl -X POST http://your-unraid-ip:8000/api/notifications/test

# Check logs
docker-compose logs -f backend
```

### 3. Subscribe to Notifications

1. Visit: `http://your-unraid-ip:8080/walkabout-deals`
2. Click "Subscribe" and allow notifications
3. Or install the ntfy mobile app and subscribe to the topic

## Management Commands

### Container Management
```bash
# View status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# Restart services
docker-compose restart

# Update to latest images
docker-compose pull
docker-compose up -d

# Stop everything
docker-compose down
```

### Database Management
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Database backup
docker-compose exec db pg_dump -U walkabout walkabout > ./data/backups/walkabout-$(date +%Y%m%d).sql

# Database restore
docker-compose exec -T db psql -U walkabout walkabout < ./data/backups/walkabout-20241221.sql
```

### Manual Operations
```bash
# Trigger scrape for all monitors
curl -X POST http://your-unraid-ip:8000/api/scrape/manual/all

# View recent prices for monitor ID 1
curl http://your-unraid-ip:8000/search/1/prices

# Check system health
curl http://your-unraid-ip:8000/api/status/health
```

## Monitoring & Maintenance

### Health Monitoring

Add to your Unraid monitoring tools:

```bash
# Health check endpoint
curl -f http://your-unraid-ip:8000/ping

# Detailed health status
curl http://your-unraid-ip:8000/api/status/health
```

### Log Monitoring

```bash
# Monitor for errors
docker-compose logs --tail=100 -f backend | grep ERROR

# Monitor scraping activity
docker-compose logs --tail=100 -f backend | grep "Scraping\|Success\|Failed"

# Monitor deal alerts
docker-compose logs --tail=100 -f backend | grep "Deal detected"
```

### Backup Strategy

```bash
# Create backup script at /mnt/user/scripts/walkabout-backup.sh
#!/bin/bash
cd /mnt/user/appdata/walkabout

# Database backup
docker-compose exec -T db pg_dump -U walkabout walkabout > ./data/backups/walkabout-$(date +%Y%m%d_%H%M%S).sql

# Keep only last 7 days of backups
find ./data/backups/ -name "walkabout-*.sql" -mtime +7 -delete

echo "Backup completed: $(date)"
```

Add to cron: `0 3 * * * /mnt/user/scripts/walkabout-backup.sh`

## Troubleshooting

### Common Issues

**Issue: Containers won't start**
```bash
# Check logs
docker-compose logs

# Verify network exists
docker network ls | grep ansiblenet

# Verify .env file
cat .env
```

**Issue: Can't access web interface**
```bash
# Check if backend is running
docker-compose ps backend

# Check port binding
netstat -tlnp | grep 8000

# Check firewall
iptables -L | grep 8000
```

**Issue: No notifications received**
```bash
# Test ntfy server
curl http://your-unraid-ip:8080/v1/health

# Test notification sending
curl -X POST http://your-unraid-ip:8000/api/notifications/test

# Check subscription URL
echo "Visit: http://your-unraid-ip:8080/walkabout-deals"
```

**Issue: Scraping failures**
```bash
# Check scraper logs
docker-compose logs playwright

# View failure screenshots
ls -la ./data/screenshots/

# Check for captchas
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import ScrapeHealth
db = SessionLocal()
healths = db.query(ScrapeHealth).all()
for h in healths:
    print(f'Monitor {h.search_definition_id}: {h.consecutive_failures} failures, last reason: {h.last_failure_reason}')
"
```

### Support

- **GitHub Issues**: [jesposito/walkabout/issues](https://github.com/jesposito/walkabout/issues)
- **Documentation**: See `PHASE1A_README.md` for Phase 1a details
- **Logs**: Always include `docker-compose logs` output when reporting issues

## Upgrading

### To Latest Version
```bash
cd /mnt/user/appdata/walkabout

# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Verify upgrade
curl http://your-unraid-ip:8000/ping
```

### From Phase 1a to 1b (Future)
When Phase 1b is released, you'll be able to migrate your data:

```bash
# Backup current data
./scripts/backup.sh

# Update docker-compose to Phase 1b
curl -o docker-compose.yml https://raw.githubusercontent.com/jesposito/walkabout/main/docker-compose.yml

# Run migration
docker-compose exec backend alembic upgrade head

# Restart with new features
docker-compose up -d
```

---

## Quick Reference

**Start**: `USE_EXTERNAL_NETWORK=true EXTERNAL_NETWORK_NAME=ansiblenet docker-compose up -d`  
**Stop**: `docker-compose down`  
**Logs**: `docker-compose logs -f backend`  
**Status**: Visit `http://your-unraid-ip:8000/`  
**Health**: `curl http://your-unraid-ip:8000/ping`  
**Backup**: `docker-compose exec -T db pg_dump -U walkabout walkabout > backup.sql`