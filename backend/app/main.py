from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os

from app.api import routes, prices, health, status, notifications, deals, trips, about, awards
from app.api import settings as settings_api
from app.scheduler import start_scheduler, stop_scheduler
from app.services.notification import get_global_notifier, shutdown_notifier
from app.config import get_settings
from app.database import engine, Base, ensure_sqlite_columns
from app.models import SearchDefinition, ScrapeHealth, FlightPrice, Route, Alert, Deal, FeedHealth, TripPlan, TripPlanMatch
from app.models.route_market_price import RouteMarketPrice
from app.models.award import TrackedAwardSearch, AwardObservation

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Walkabout Phase 1a")
    
    if settings.database_url.startswith("sqlite"):
        logger.info("SQLite detected - creating tables if needed")
        Base.metadata.create_all(bind=engine)
        ensure_sqlite_columns()
    
    try:
        # Start the scheduler
        start_scheduler()
        logger.info("✅ APScheduler started")

        # Send startup notification
        notifier = get_global_notifier()
        await notifier.send_startup_notification()
        logger.info("✅ Startup notification sent")

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")

    # Application is running
    yield

    # Shutdown
    logger.info("🛑 Shutting down Walkabout")

    try:
        # Stop scheduler
        stop_scheduler()
        logger.info("✅ APScheduler stopped")

        # Close notifier HTTP client
        await shutdown_notifier()
        logger.info("✅ Notifier shutdown")

    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


app = FastAPI(
    title="Walkabout Phase 1a",
    description="Self-hosted travel deal monitor - Prove Ingestion Phase",
    version="1a.0.0",
    lifespan=lifespan
)

# CORS for Phase 1a - only localhost (security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(deals.router, prefix="/deals", tags=["deals"])
app.include_router(settings_api.router, prefix="/settings", tags=["settings"])
app.include_router(trips.router, prefix="/trips", tags=["trips"])
app.include_router(status.router, tags=["status"])
app.include_router(health.router, tags=["health"])  
app.include_router(routes.router, prefix="/api/routes", tags=["routes"])
app.include_router(prices.router, prefix="/prices", tags=["prices"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(about.router, prefix="/about", tags=["about"])
app.include_router(awards.router, prefix="/awards", tags=["awards"])


# Health check for monitoring/Docker
@app.get("/ping")
async def ping():
    """Simple ping endpoint for health checks."""
    return {"status": "ok", "phase": "1a"}