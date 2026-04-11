"""Celery application with beat schedule for FoodGrump scrapers."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery = Celery("foodgrump", broker=settings.redis_url, backend=settings.redis_url)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery.conf.beat_schedule = {
    "scrape-michelin-restaurants": {
        "task": "app.scrapers.michelin.scrape_michelin_restaurants",
        "schedule": crontab(minute=0, hour=2, day_of_week="sunday"),
    },
    "scrape-michelin-hotels": {
        "task": "app.scrapers.michelin.scrape_michelin_hotels",
        "schedule": crontab(minute=0, hour=3, day_of_week="sunday"),
    },
    "scrape-conde-nast": {
        "task": "app.scrapers.conde_nast.scrape_conde_nast",
        "schedule": crontab(minute=0, hour=4, day_of_week="sunday"),
    },
    "scrape-beli": {
        "task": "app.scrapers.beli.scrape_beli",
        "schedule": crontab(minute=0, hour=6),
    },
    "scrape-reddit-restaurants": {
        "task": "app.scrapers.reddit.scrape_reddit_restaurants",
        "schedule": crontab(minute=0, hour=7),
    },
    "scrape-reddit-hotels": {
        "task": "app.scrapers.reddit.scrape_reddit_hotels",
        "schedule": crontab(minute=0, hour=8),
    },
    "scrape-infatuation": {
        "task": "app.scrapers.infatuation.scrape_infatuation",
        "schedule": crontab(minute=0, hour=2, day_of_week="monday"),
    },
    "scrape-eater": {
        "task": "app.scrapers.eater.scrape_eater",
        "schedule": crontab(minute=0, hour=3, day_of_week="monday"),
    },
    "compute-rankings": {
        "task": "app.scrapers.rankings.compute_rankings",
        "schedule": crontab(minute=0, hour=10),
    },
}

celery.autodiscover_tasks(["app.scrapers"])
