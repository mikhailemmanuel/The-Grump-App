"""Scraper that pulls Google Places ratings into FoodGrump recommendations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_

from app.celery_app import celery
from app.db_sync import SyncSessionLocal
from app.models.venue import Recommendation, Venue
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50
_STALE_DAYS = 30


class GoogleReviewsScraper(BaseScraper):
    """Fetch Google Places ratings for existing venues and store as recommendations."""

    def __init__(self, entity_type: str) -> None:
        super().__init__(source="google", entity_type=entity_type)
        self.dedup = GooglePlacesDedup()

    # ── core logic ────────────────────────────────────────────────────

    def scrape(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_DAYS)
        count = 0
        offset = 0

        while True:
            with SyncSessionLocal() as session:
                # Venues of this entity_type that have no google recommendation
                # or whose google recommendation is older than 30 days.
                stale_rec = (
                    session.query(Recommendation.venue_id)
                    .filter(
                        Recommendation.source == "google",
                        Recommendation.scraped_at >= cutoff,
                    )
                    .subquery()
                )

                venues = (
                    session.query(Venue)
                    .filter(
                        Venue.entity_type == self.entity_type,
                        ~Venue.id.in_(session.query(stale_rec.c.venue_id)),
                    )
                    .order_by(Venue.id)
                    .offset(offset)
                    .limit(_BATCH_SIZE)
                    .all()
                )

                if not venues:
                    break

                for venue in venues:
                    try:
                        result = self.dedup.lookup(
                            venue.name, venue.city, venue.entity_type,
                        )
                        if result and result.get("rating") and result.get("review_count"):
                            rating = result["rating"]
                            review_count = result["review_count"]
                            self.upsert_recommendation(
                                session,
                                venue_id=venue.id,
                                source="google",
                                snippet=f"Google rating: {rating}/5 based on {review_count} reviews",
                                rating=rating,
                                awards=[],
                            )
                            count += 1
                    except Exception:
                        logger.exception(
                            "Failed to fetch Google reviews for venue %s (%s)",
                            venue.name,
                            venue.id,
                        )

                session.commit()
                offset += _BATCH_SIZE

        logger.info(
            "GoogleReviewsScraper(%s) upserted %d recommendations", self.entity_type, count,
        )
        return count


# ── Celery tasks ──────────────────────────────────────────────────────


@celery.task(name="app.scrapers.google_reviews.sync_google_reviews_restaurants")
def sync_google_reviews_restaurants() -> None:
    scraper = GoogleReviewsScraper(entity_type="restaurant")
    scraper.run()


@celery.task(name="app.scrapers.google_reviews.sync_google_reviews_hotels")
def sync_google_reviews_hotels() -> None:
    scraper = GoogleReviewsScraper(entity_type="hotel")
    scraper.run()
