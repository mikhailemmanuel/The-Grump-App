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
    "sync-google-reviews-restaurants": {
        "task": "app.scrapers.google_reviews.sync_google_reviews_restaurants",
        "schedule": crontab(minute=0, hour=5, day_of_week="sunday"),
    },
    "sync-google-reviews-hotels": {
        "task": "app.scrapers.google_reviews.sync_google_reviews_hotels",
        "schedule": crontab(minute=0, hour=5, day_of_week="monday"),
    },
    "match-reservations": {
        "task": "app.scrapers.reservations.match_reservations",
        "schedule": crontab(minute=0, hour=9),
    },
    "compute-rankings": {
        "task": "app.scrapers.scoring.compute_all_rankings",
        "schedule": crontab(minute=0, hour=10),
    },
    "generate-ai-summaries": {
        "task": "app.scrapers.ai_summary.generate_all_summaries",
        "schedule": crontab(minute=0, hour=11),
    },
}

celery.autodiscover_tasks(["app.scrapers", "app.services"])
