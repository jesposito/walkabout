# Walkabout Unraid Deployment Guide

Deploy Walkabout on your Unraid server as a single Docker container with SQLite.

## Quick Start

```bash
# 1. SSH to your Unraid server
ssh root@your-unraid-ip

# 2. Create data directory
mkdir -p /mnt/user/appdata/walkabout/data

# 3. Pull and run the container
docker run -d \
  --name walkabout \
  -p 8000:8000 \
  -v /mnt/user/appdata/walkabout/data:/app/data \
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest

# 4. Wait for startup and check status
sleep 10
curl -f http://localhost:8000/health
```

## Service Access

Once deployed, access at:

| Service | URL | Purpose |
|---------|-----|---------|
| **Dashboard** | `http://your-unraid-ip:8000/` | Main deals and trips view |
| **Settings** | `http://your-unraid-ip:8000/settings` | Configure airports, notifications, AI |
| **Health Check** | `http://your-unraid-ip:8000/health` | Health status endpoint |
| **About** | `http://your-unraid-ip:8000/about` | Version info and links |

## Initial Setup

### 1. Configure Your Settings

1. Open `http://your-unraid-ip:8000/settings`
2. Set your **Home Airports** (e.g., AKL, WLG, CHC)
3. Configure **Notifications** (optional):
   - ntfy: Set your ntfy server URL and topic
   - Discord: Paste your Discord webhook URL
4. Configure **AI Provider** (optional):
   - Claude: Add your Anthropic API key
   - Ollama: Set your Ollama server URL

### 2. Add Trip Plans

1. Go to the **Trips** page
2. Click "New Trip Plan"
3. Set your origins, destinations, dates, and budget
4. Walkabout will monitor for matching deals

## Container Management

### Basic Commands

```bash
# View logs
docker logs -f walkabout

# Restart
docker restart walkabout

# Stop
docker stop walkabout

# Remove
docker rm walkabout

# Update to latest
docker pull ghcr.io/jesposito/walkabout:latest
docker stop walkabout
docker rm walkabout
docker run -d \
  --name walkabout \
  -p 8000:8000 \
  -v /mnt/user/appdata/walkabout/data:/app/data \
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

### Port Conflicts

If port 8000 is in use, map to a different port:

```bash
docker run -d \
  --name walkabout \
  -p 8002:8000 \  # External port 8002 -> internal 8000
  -v /mnt/user/appdata/walkabout/data:/app/data \
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

Then access at `http://your-unraid-ip:8002`

### Custom Network

To use a custom Docker network (e.g., for Tailscale or reverse proxy):

```bash
docker run -d \
  --name walkabout \
  --network your-network \
  -p 8000:8000 \
  -v /mnt/user/appdata/walkabout/data:/app/data \
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

## Data & Backups

### Data Location

All data is stored in a single SQLite database:

```
/mnt/user/appdata/walkabout/data/
├── walkabout.db          # SQLite database (deals, trips, settings)
├── screenshots/          # Scrape debug screenshots
└── html_snapshots/       # Scrape debug HTML
```

### Backup

```bash
# Simple backup
cp /mnt/user/appdata/walkabout/data/walkabout.db /mnt/user/appdata/walkabout/data/backups/walkabout-$(date +%Y%m%d).db

# Or use Unraid's built-in backup tools
```

### Restore

```bash
# Stop container
docker stop walkabout

# Restore database
cp /mnt/user/appdata/walkabout/data/backups/walkabout-20260130.db /mnt/user/appdata/walkabout/data/walkabout.db

# Start container
docker start walkabout
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs walkabout

# Verify data directory exists and has correct permissions
ls -la /mnt/user/appdata/walkabout/data/
```

### Can't Access Web Interface

```bash
# Check if container is running
docker ps | grep walkabout

# Check port binding
netstat -tlnp | grep 8000

# Test from server
curl http://localhost:8000/health
```

### Database Missing Data After Update

If you see missing data after a container update, check your volume mount. The correct mount is:

```bash
-v /mnt/user/appdata/walkabout/data:/app/data
```

**Not** `/mnt/user/appdata/walkabout:/app/data` (missing `/data` subdirectory).

### Notifications Not Working

1. Check Settings page - verify provider is configured
2. Test notification from Settings page
3. For ntfy: verify your ntfy server is accessible
4. For Discord: verify webhook URL is correct

Check logs for notification errors:
```bash
docker logs walkabout 2>&1 | grep -i notification
```

## Upgrading

### Standard Upgrade

```bash
# Pull latest image
docker pull ghcr.io/jesposito/walkabout:latest

# Recreate container
docker stop walkabout
docker rm walkabout
docker run -d \
  --name walkabout \
  -p 8000:8000 \
  -v /mnt/user/appdata/walkabout/data:/app/data \
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

### Database Migrations

The app automatically applies any needed database migrations on startup. SQLite columns are auto-added if missing.

---

## Quick Reference

| Action | Command |
|--------|---------|
| **Start** | `docker start walkabout` |
| **Stop** | `docker stop walkabout` |
| **Logs** | `docker logs -f walkabout` |
| **Status** | `http://your-unraid-ip:8000/` |
| **Health** | `curl http://your-unraid-ip:8000/health` |
| **Settings** | `http://your-unraid-ip:8000/settings` |
