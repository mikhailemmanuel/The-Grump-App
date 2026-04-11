"""Match venues to reservation / booking platform links."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import httpx

from app.celery_app import celery
from app.db_sync import SyncSessionLocal
from app.models.venue import ReservationLink, Venue

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50
_STALE_DAYS = 30
_REQUEST_TIMEOUT = 10
_INTER_PLATFORM_SLEEP = 1

# ── platform-specific matchers ────────────────────────────────────────

_RESTAURANT_PLATFORMS = ["resy", "opentable", "sevenrooms", "tock"]
_HOTEL_PLATFORMS = ["booking_com", "hotels_com", "expedia"]


def _slug(name: str) -> str:
    """Convert venue name to a URL-friendly slug."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _search_resy(client: httpx.Client, name: str, city: str) -> dict | None:
    """Try Resy venue lookup by name-based slug."""
    slug = _slug(name)
    try:
        resp = client.get(
            f"https://api.resy.com/3/venue?url_slug={slug}&location={quote_plus(city)}",
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            venue_id_ext = str(data.get("id", ""))
            url_slug = data.get("url_slug", slug)
            return {
                "platform": "resy",
                "booking_url": f"https://resy.com/cities/{_slug(city)}/{url_slug}",
                "venue_id_ext": venue_id_ext or None,
            }
    except Exception:
        logger.debug("Resy lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_opentable(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search OpenTable for a venue."""
    try:
        resp = client.get(
            "https://www.opentable.com/s",
            params={"term": f"{name} {city}", "covers": "2"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            # Look for a restaurant profile link in the response
            match = re.search(
                r'href="(https://www\.opentable\.com/r/[^"]+)"', resp.text,
            )
            if match:
                booking_url = match.group(1)
                # Extract external id from URL path
                ext_match = re.search(r"/r/([^?]+)", booking_url)
                venue_id_ext = ext_match.group(1) if ext_match else None
                return {
                    "platform": "opentable",
                    "booking_url": booking_url,
                    "venue_id_ext": venue_id_ext,
                }
    except Exception:
        logger.debug("OpenTable lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_sevenrooms(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search SevenRooms for a venue."""
    try:
        resp = client.get(
            f"https://www.sevenrooms.com/reservations/{_slug(name)}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200 and "reservations" in str(resp.url):
            return {
                "platform": "sevenrooms",
                "booking_url": str(resp.url),
                "venue_id_ext": _slug(name),
            }
    except Exception:
        logger.debug("SevenRooms lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_tock(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search Tock for a venue."""
    try:
        resp = client.get(
            f"https://www.exploretock.com/{_slug(name)}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200 and "exploretock.com" in str(resp.url):
            return {
                "platform": "tock",
                "booking_url": str(resp.url),
                "venue_id_ext": _slug(name),
            }
    except Exception:
        logger.debug("Tock lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_booking_com(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search Booking.com for a hotel."""
    try:
        resp = client.get(
            "https://www.booking.com/searchresults.html",
            params={"ss": f"{name} {city}"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            match = re.search(
                r'href="(https://www\.booking\.com/hotel/[^"]+)"', resp.text,
            )
            if match:
                booking_url = match.group(1).split("?")[0]
                return {
                    "platform": "booking_com",
                    "booking_url": booking_url,
                    "venue_id_ext": None,
                }
    except Exception:
        logger.debug("Booking.com lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_hotels_com(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search Hotels.com for a hotel."""
    try:
        resp = client.get(
            "https://www.hotels.com/search.do",
            params={"q-destination": f"{name} {city}"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            match = re.search(
                r'href="(https://www\.hotels\.com/ho\d+[^"]*)"', resp.text,
            )
            if match:
                booking_url = match.group(1).split("?")[0]
                ext_match = re.search(r"/ho(\d+)", booking_url)
                return {
                    "platform": "hotels_com",
                    "booking_url": booking_url,
                    "venue_id_ext": ext_match.group(1) if ext_match else None,
                }
    except Exception:
        logger.debug("Hotels.com lookup failed for %s, %s", name, city, exc_info=True)
    return None


def _search_expedia(client: httpx.Client, name: str, city: str) -> dict | None:
    """Search Expedia for a hotel."""
    try:
        resp = client.get(
            "https://www.expedia.com/Hotel-Search",
            params={"destination": f"{name} {city}"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=_REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            match = re.search(
                r'href="(https://www\.expedia\.com/[^"]*Hotel[^"]*\.h\d+[^"]*)"',
                resp.text,
            )
            if match:
                booking_url = match.group(1).split("?")[0]
                ext_match = re.search(r"\.h(\d+)", booking_url)
                return {
                    "platform": "expedia",
                    "booking_url": booking_url,
                    "venue_id_ext": ext_match.group(1) if ext_match else None,
                }
    except Exception:
        logger.debug("Expedia lookup failed for %s, %s", name, city, exc_info=True)
    return None


_PLATFORM_FN = {
    "resy": _search_resy,
    "opentable": _search_opentable,
    "sevenrooms": _search_sevenrooms,
    "tock": _search_tock,
    "booking_com": _search_booking_com,
    "hotels_com": _search_hotels_com,
    "expedia": _search_expedia,
}


# ── ReservationMatcher ────────────────────────────────────────────────


class ReservationMatcher:
    """Find reservation / booking links for venues across platforms."""

    def match_venue(self, session, venue: Venue) -> list[dict]:
        """Search platforms for booking links and upsert results."""
        platforms = (
            _RESTAURANT_PLATFORMS
            if venue.entity_type == "restaurant"
            else _HOTEL_PLATFORMS
        )

        results: list[dict] = []
        with httpx.Client() as client:
            for platform in platforms:
                fn = _PLATFORM_FN.get(platform)
                if fn is None:
                    continue

                try:
                    match = fn(client, venue.name, venue.city)
                except Exception:
                    logger.exception(
                        "Platform %s search error for venue %s", platform, venue.name,
                    )
                    match = None

                if match:
                    self._upsert_link(session, venue.id, match)
                    results.append(match)

                time.sleep(_INTER_PLATFORM_SLEEP)

        return results

    @staticmethod
    def _upsert_link(session, venue_id, match: dict) -> None:
        """Upsert a ReservationLink row."""
        existing = (
            session.query(ReservationLink)
            .filter(
                ReservationLink.venue_id == venue_id,
                ReservationLink.platform == match["platform"],
            )
            .first()
        )

        if existing is None:
            existing = ReservationLink(
                venue_id=venue_id,
                platform=match["platform"],
            )
            session.add(existing)

        existing.booking_url = match["booking_url"]
        existing.venue_id_ext = match.get("venue_id_ext")
        existing.verified_at = datetime.now(timezone.utc)
        session.flush()


# ── Celery task ───────────────────────────────────────────────────────


@celery.task(name="app.scrapers.reservations.match_reservations")
def match_reservations() -> None:
    """Process all venues without recent reservation links."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=_STALE_DAYS)
    matcher = ReservationMatcher()
    offset = 0
    total = 0

    while True:
        with SyncSessionLocal() as session:
            # Venues that have no reservation links verified after cutoff
            fresh = (
                session.query(ReservationLink.venue_id)
                .filter(ReservationLink.verified_at >= cutoff)
                .subquery()
            )

            venues = (
                session.query(Venue)
                .filter(~Venue.id.in_(session.query(fresh.c.venue_id)))
                .order_by(Venue.id)
                .offset(offset)
                .limit(_BATCH_SIZE)
                .all()
            )

            if not venues:
                break

            for venue in venues:
                try:
                    results = matcher.match_venue(session, venue)
                    total += len(results)
                except Exception:
                    logger.exception(
                        "Failed to match reservations for venue %s (%s)",
                        venue.name,
                        venue.id,
                    )

            session.commit()
            offset += _BATCH_SIZE

    logger.info("ReservationMatcher upserted %d links", total)
