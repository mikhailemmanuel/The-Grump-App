"""Google Places dedup service with Redis caching and fuzzy DB fallback."""

from __future__ import annotations

import json
import logging

import httpx
import redis

from app.config import settings
from app.models.venue import Venue
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days in seconds

_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.rating,"
    "places.userRatingCount"
)

_ENTITY_TYPE_MAP = {
    "restaurant": "restaurant",
    "hotel": "lodging",
}


class GooglePlacesDedup:
    """Resolve venue identity via Google Places (new) API with Redis cache."""

    def __init__(self) -> None:
        self.api_key = settings.google_places_api_key
        self.redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    # ── public API ────────────────────────────────────────────────────

    def lookup(self, name: str, city: str, entity_type: str) -> dict | None:
        """Look up a place via Google Places. Returns dict or None.

        Returned dict keys: place_id, address, lat, lng, rating, review_count, name.
        """
        norm = BaseScraper.normalize_name(name)
        cache_key = f"places:{entity_type}:{norm}:{city.lower()}"

        # Check cache
        cached = self.redis.get(cache_key)
        if cached is not None:
            return json.loads(cached)

        # Call Google Places API
        included_type = _ENTITY_TYPE_MAP.get(entity_type, "restaurant")
        try:
            resp = httpx.post(
                "https://places.googleapis.com/v1/places:searchText",
                json={
                    "textQuery": f"{name}, {city}",
                    "includedType": included_type,
                },
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": _FIELD_MASK,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Google Places API error for %s, %s", name, city)
            return None

        data = resp.json()
        places = data.get("places", [])
        if not places:
            logger.info("No Google Places result for %s, %s", name, city)
            return None

        place = places[0]
        location = place.get("location", {})
        result = {
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text", name),
            "address": place.get("formattedAddress"),
            "lat": location.get("latitude"),
            "lng": location.get("longitude"),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
        }

        # Cache the result
        self.redis.set(cache_key, json.dumps(result), ex=_CACHE_TTL)
        return result

    def fuzzy_match(self, session, name: str, city: str, entity_type: str) -> Venue | None:
        """Fallback: query venues table for normalized_name LIKE match + same city + entity_type."""
        norm = BaseScraper.normalize_name(name)
        return (
            session.query(Venue)
            .filter(
                Venue.normalized_name.ilike(f"%{norm}%"),
                Venue.city == city,
                Venue.entity_type == entity_type,
            )
            .first()
        )
