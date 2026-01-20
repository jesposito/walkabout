from celery import Celery
from celery.schedules import crontab
from app.config import get_settings

settings = get_settings()

app = Celery(
    "walkabout",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["celery_app.tasks.scrape_flights"]
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Pacific/Auckland",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "scrape-morning": {
        "task": "celery_app.tasks.scrape_flights.scrape_all_routes",
        "schedule": crontab(hour=6, minute=30),
    },
    "scrape-evening": {
        "task": "celery_app.tasks.scrape_flights.scrape_all_routes",
        "schedule": crontab(hour=18, minute=30),
    },
}
