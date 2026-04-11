"""Base scraper class with ScrapeJob lifecycle and venue/recommendation upsert."""

from __future__ import annotations

import logging
import re
import traceback
import unicodedata
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlalchemy import and_

from app.db_sync import SyncSessionLocal
from app.models.scrape import ScrapeJob
from app.models.venue import Recommendation, Venue

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Template-method base for all FoodGrump scrapers.

    Subclasses implement ``scrape()``. Call ``run()`` to execute with
    automatic ScrapeJob tracking.
    """

    def __init__(self, source: str, entity_type: str) -> None:
        self.source = source
        self.entity_type = entity_type

    # ── public entry point ────────────────────────────────────────────

    def run(self) -> ScrapeJob:
        """Execute the scraper with ScrapeJob lifecycle tracking."""
        with SyncSessionLocal() as session:
            job = ScrapeJob(
                source=self.source,
                entity_type=self.entity_type,
                status="running",
                started_at=datetime.now(timezone.utc),
            )
            session.add(job)
            session.commit()

        try:
            items = self.scrape()
            with SyncSessionLocal() as session:
                job = session.get(ScrapeJob, job.id)
                job.status = "done"
                job.finished_at = datetime.now(timezone.utc)
                job.items_found = items if isinstance(items, int) else 0
                session.commit()
                session.refresh(job)
            logger.info("Scrape %s/%s finished – %d items", self.source, self.entity_type, job.items_found)
        except Exception as exc:
            logger.exception("Scrape %s/%s failed", self.source, self.entity_type)
            with SyncSessionLocal() as session:
                job = session.get(ScrapeJob, job.id)
                job.status = "failed"
                job.finished_at = datetime.now(timezone.utc)
                job.error = f"{exc}\n{traceback.format_exc()}"
                session.commit()
                session.refresh(job)

        return job

    # ── abstract ──────────────────────────────────────────────────────

    @abstractmethod
    def scrape(self) -> int:
        """Run the actual scrape. Return the number of items found."""
        ...

    # ── upsert helpers ────────────────────────────────────────────────

    @staticmethod
    def upsert_venue(
        session,
        *,
        name: str,
        city: str,
        country: str,
        entity_type: str,
        google_place_id: str | None = None,
        address: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        tags: list[str] | None = None,
        price_level: int | None = None,
        cuisine_tags: list[str] | None = None,
        star_rating: int | None = None,
        hotel_brand: str | None = None,
    ) -> Venue:
        """Find venue by google_place_id or (normalized_name + city + entity_type), or create."""
        venue: Venue | None = None

        if google_place_id:
            venue = session.query(Venue).filter(Venue.google_place_id == google_place_id).first()

        if venue is None:
            norm = BaseScraper.normalize_name(name)
            venue = (
                session.query(Venue)
                .filter(
                    and_(
                        Venue.normalized_name == norm,
                        Venue.city == city,
                        Venue.entity_type == entity_type,
                    )
                )
                .first()
            )

        if venue is None:
            venue = Venue(
                name=name,
                normalized_name=BaseScraper.normalize_name(name),
                city=city,
                country=country,
                entity_type=entity_type,
            )
            session.add(venue)

        # Update fields
        if google_place_id:
            venue.google_place_id = google_place_id
        if address:
            venue.address = address
        if lat is not None and lng is not None:
            venue.location = f"SRID=4326;POINT({lng} {lat})"
        if tags:
            venue.tags = tags
        if price_level is not None:
            venue.price_level = price_level
        if cuisine_tags is not None:
            venue.cuisine_tags = cuisine_tags
        if star_rating is not None:
            venue.star_rating = star_rating
        if hotel_brand is not None:
            venue.hotel_brand = hotel_brand

        session.flush()
        return venue

    @staticmethod
    def upsert_recommendation(
        session,
        *,
        venue_id,
        source: str,
        source_url: str | None = None,
        title: str | None = None,
        snippet: str | None = None,
        rating: float | None = None,
        awards: list[str] | None = None,
        published_at: datetime | None = None,
    ) -> Recommendation:
        """Upsert recommendation by (venue_id, source, source_url)."""
        rec = (
            session.query(Recommendation)
            .filter(
                and_(
                    Recommendation.venue_id == venue_id,
                    Recommendation.source == source,
                    Recommendation.source_url == source_url,
                )
            )
            .first()
        )

        if rec is None:
            rec = Recommendation(venue_id=venue_id, source=source, source_url=source_url)
            session.add(rec)

        rec.title = title
        rec.snippet = snippet
        rec.rating = rating
        rec.awards = awards
        rec.published_at = published_at
        rec.scraped_at = datetime.now(timezone.utc)

        session.flush()
        return rec

    # ── utilities ─────────────────────────────────────────────────────

    @staticmethod
    def normalize_name(name: str) -> str:
        """Lowercase, strip accents, remove punctuation, collapse whitespace."""
        name = name.lower().strip()
        # Strip accents
        name = unicodedata.normalize("NFKD", name)
        name = "".join(c for c in name if not unicodedata.combining(c))
        # Remove punctuation (keep letters, digits, spaces)
        name = re.sub(r"[^\w\s]", "", name)
        # Collapse whitespace
        name = re.sub(r"\s+", " ", name).strip()
        return name
