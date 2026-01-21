from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import routes, prices, health, status
from app.scheduler import start_scheduler, stop_scheduler
from app.services.notification import NtfyNotifier
from app.config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown for Phase 1a.
    
    Startup:
    - Start APScheduler for scraping jobs
    - Send startup notification
    
    Shutdown:
    - Stop scheduler gracefully
    """
    # Startup
    logger.info("🚀 Starting Walkabout Phase 1a")
    
    try:
        # Start the scheduler
        start_scheduler()
        logger.info("✅ APScheduler started")
        
        # Send startup notification
        notifier = NtfyNotifier()
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
    allow_methods=["GET", "POST"],  # Limited for Phase 1a
    allow_headers=["*"],
)

# Include routers
# Status router handles the main "/" route and status page
app.include_router(status.router, tags=["status"])

# API routers
app.include_router(health.router, tags=["health"])  
app.include_router(routes.router, prefix="/api/routes", tags=["routes"])
app.include_router(prices.router, prefix="/api/prices", tags=["prices"])


# Health check for monitoring/Docker
@app.get("/ping")
async def ping():
    """Simple ping endpoint for health checks."""
    return {"status": "ok", "phase": "1a"}