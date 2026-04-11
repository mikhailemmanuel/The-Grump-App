"""Beli scraper — restaurant ratings and reviews via Beli's mobile API."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx

from app.celery_app import celery
from app.config import settings
from app.db_sync import SyncSessionLocal
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

# ── Beli API patterns (reverse-engineered from mobile app) ─────────────
# Base URL for Beli's backend API.
_BELI_API_BASE = "https://api.bfrg.co"
# Auth endpoint — email/password → JWT or session cookie.
_AUTH_URL = f"{_BELI_API_BASE}/v1/auth/login"
# User's rated restaurants (paginated).
_RATINGS_URL = f"{_BELI_API_BASE}/v1/me/ratings"
# Global top lists endpoint.
_TOP_LISTS_URL = f"{_BELI_API_BASE}/v1/restaurants/top"

_PAGE_DELAY = 2  # seconds between paginated requests
_MAX_RETRIES = 1  # re-auth retries on 401


class BeliScraper(BaseScraper):
    """Scrape restaurant ratings from Beli's mobile API."""

    def __init__(self) -> None:
        super().__init__(source="beli", entity_type="restaurant")
        self.dedup = GooglePlacesDedup()
        self.client = httpx.Client(
            base_url=_BELI_API_BASE,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "Beli/3.0 (iPhone; iOS 17.0)",
            },
            follow_redirects=True,
            timeout=30,
        )
        self._token: str | None = None

    # ── abstract implementation ────────────────────────────────────────

    def scrape(self) -> int:
        self._authenticate()
        total = 0

        # Scrape user's rated restaurants (paginated)
        total += self._scrape_paginated(_RATINGS_URL, "ratings")

        # Scrape global top lists
        total += self._scrape_paginated(_TOP_LISTS_URL, "top")

        self.client.close()
        return total

    # ── authentication ─────────────────────────────────────────────────

    def _authenticate(self) -> None:
        """Log in to Beli with email/password and store the auth token."""
        logger.info("Authenticating with Beli as %s", settings.beli_email)
        resp = self.client.post(
            _AUTH_URL,
            json={
                "email": settings.beli_email,
                "password": settings.beli_password,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # Beli returns a JWT in the response body or sets a session cookie.
        self._token = data.get("token") or data.get("access_token")
        if self._token:
            self.client.headers["Authorization"] = f"Bearer {self._token}"
        # If no explicit token, rely on cookies set by the response.
        logger.info("Beli authentication successful")

    # ── paginated fetch with 401 retry ─────────────────────────────────

    def _scrape_paginated(self, url: str, label: str) -> int:
        """Fetch paginated restaurant data, handling session expiry."""
        count = 0
        page = 1
        retries = 0

        while True:
            resp = self._request_with_retry("GET", url, params={"page": page, "limit": 50})
            if resp is None:
                logger.error("Beli %s: giving up after auth retries", label)
                break

            data = resp.json()
            items = data.get("results") or data.get("restaurants") or data.get("data") or []
            if not items:
                break

            for item in items:
                try:
                    self._process_restaurant(item)
                    count += 1
                except Exception:
                    logger.exception("Error processing Beli restaurant item")

            # Check for next page
            if not data.get("has_next", False) and not data.get("next"):
                break
            page += 1
            time.sleep(_PAGE_DELAY)

        logger.info("Beli %s: processed %d restaurants", label, count)
        return count

    def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        retries_left: int = _MAX_RETRIES,
    ) -> httpx.Response | None:
        """Make an authenticated request; re-authenticate on 401."""
        try:
            resp = self.client.request(method, url, params=params)
        except httpx.HTTPError:
            logger.exception("Beli HTTP error for %s", url)
            return None

        if resp.status_code == 401 and retries_left > 0:
            logger.warning("Beli 401 — re-authenticating (retries left: %d)", retries_left)
            try:
                self._authenticate()
            except httpx.HTTPStatusError:
                logger.exception("Beli re-authentication failed")
                return None
            return self._request_with_retry(method, url, params=params, retries_left=retries_left - 1)

        if resp.status_code >= 400:
            logger.error("Beli %s returned %d: %s", url, resp.status_code, resp.text[:300])
            return None

        return resp

    # ── restaurant processing ──────────────────────────────────────────

    def _process_restaurant(self, item: dict) -> None:
        """Extract fields from a Beli API restaurant object, dedup, and persist."""
        # Beli API response shape (observed patterns):
        #   { "name": "...", "city": "...", "rating": 8.5,
        #     "review": "...", "cuisine": "...", "price": 2 }
        name = item.get("name") or item.get("restaurant_name")
        city = item.get("city") or item.get("location", {}).get("city")
        if not name or not city:
            logger.debug("Skipping Beli item with missing name/city: %s", item.get("name"))
            return

        rating = item.get("rating") or item.get("score")
        snippet = item.get("review") or item.get("description") or item.get("note")
        cuisine = item.get("cuisine") or item.get("cuisine_type")

        # Dedup via Google Places
        place = self.dedup.lookup(name, city, "restaurant")
        google_place_id = place["place_id"] if place else None
        address = place["address"] if place else None
        lat = place["lat"] if place else None
        lng = place["lng"] if place else None

        with SyncSessionLocal() as session:
            venue = self.upsert_venue(
                session,
                name=place["name"] if place else name,
                city=city,
                country="",
                entity_type="restaurant",
                google_place_id=google_place_id,
                address=address,
                lat=lat,
                lng=lng,
                cuisine_tags=[cuisine] if cuisine else None,
                price_level=item.get("price") or item.get("price_level"),
            )
            self.upsert_recommendation(
                session,
                venue_id=venue.id,
                source=self.source,
                source_url=item.get("url") or item.get("link"),
                title=name,
                snippet=snippet[:500] if snippet else None,
                rating=float(rating) if rating is not None else None,
                awards=["beli_rated"],
            )
            session.commit()


# ── Celery task ────────────────────────────────────────────────────────


@celery.task(name="app.scrapers.beli.scrape_beli")
def scrape_beli() -> dict:
    """Celery entry-point for the Beli restaurant scraper."""
    job = BeliScraper().run()
    return {"job_id": job.id, "status": job.status, "items_found": job.items_found}
