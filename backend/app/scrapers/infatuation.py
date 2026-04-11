"""Scraper for The Infatuation restaurant reviews."""

from __future__ import annotations

import logging
import time

import httpx
from bs4 import BeautifulSoup

from app.db_sync import SyncSessionLocal
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36 FoodGrumpBot/1.0"
)

_CITIES = {
    "new-york": {"city": "New York", "country": "US"},
    "los-angeles": {"city": "Los Angeles", "country": "US"},
    "san-francisco": {"city": "San Francisco", "country": "US"},
    "chicago": {"city": "Chicago", "country": "US"},
    "london": {"city": "London", "country": "GB"},
    "paris": {"city": "Paris", "country": "FR"},
}

_BASE_URL = "https://www.theinfatuation.com"

# Descriptive ratings → 0-10 numeric scale
_RATING_MAP: dict[str, float] = {
    "extraordinary": 10.0,
    "exceptional": 9.0,
    "excellent": 8.5,
    "great": 8.0,
    "very good": 7.5,
    "good": 7.0,
    "solid": 6.0,
    "decent": 5.0,
    "fair": 4.0,
    "poor": 3.0,
    "bad": 2.0,
}

_PRICE_MAP: dict[str, int] = {
    "$": 1,
    "$$": 2,
    "$$$": 3,
    "$$$$": 4,
}


class InfatuationScraper(BaseScraper):
    """Scrape The Infatuation city review pages."""

    def __init__(self) -> None:
        super().__init__(source="infatuation", entity_type="restaurant")
        self.client = httpx.Client(
            headers={"User-Agent": _USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )
        self.dedup = GooglePlacesDedup()

    # ── core ───────────────────────────────────────────────────────────

    def scrape(self) -> int:
        total = 0
        try:
            for slug, meta in _CITIES.items():
                total += self._scrape_city(slug, meta["city"], meta["country"])
        finally:
            self.client.close()
        return total

    # ── city-level pagination ──────────────────────────────────────────

    def _scrape_city(self, slug: str, city: str, country: str) -> int:
        count = 0
        page = 1
        while True:
            url = f"{_BASE_URL}/{slug}/reviews"
            params: dict[str, str | int] = {"page": page}
            logger.info("Fetching %s page %d", url, page)
            try:
                resp = self.client.get(url, params=params)
                resp.raise_for_status()
            except httpx.HTTPError:
                logger.exception("Failed to fetch %s page %d", url, page)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = self._extract_review_cards(soup)
            if not cards:
                logger.info("No more cards for %s at page %d", slug, page)
                break

            for card in cards:
                try:
                    self._process_card(card, city, country, slug)
                    count += 1
                except Exception:
                    logger.exception("Error processing card in %s", slug)

            # Check for next page link
            next_link = soup.select_one('a[aria-label="Next page"], a[rel="next"]')
            if next_link is None:
                break
            page += 1
            time.sleep(2)

        return count

    # ── parsing helpers ────────────────────────────────────────────────

    @staticmethod
    def _extract_review_cards(soup: BeautifulSoup) -> list[BeautifulSoup]:
        """Return review card elements from a listing page."""
        cards = soup.select('div[data-testid="reviewCard"], article.review-card, div.venue-card')
        if not cards:
            # Fallback: look for any linked headings that appear to be reviews
            cards = soup.select("div.search-result, div.review-item, li.review-list-item")
        return cards

    @staticmethod
    def _parse_rating(text: str | None) -> float | None:
        if not text:
            return None
        cleaned = text.strip().lower()
        if cleaned in _RATING_MAP:
            return _RATING_MAP[cleaned]
        # Try parsing as a numeric value
        try:
            val = float(cleaned)
            return min(val, 10.0)
        except ValueError:
            # Partial match
            for key, score in _RATING_MAP.items():
                if key in cleaned:
                    return score
        return None

    @staticmethod
    def _parse_price(text: str | None) -> int | None:
        if not text:
            return None
        stripped = text.strip()
        return _PRICE_MAP.get(stripped)

    def _process_card(
        self, card: BeautifulSoup, city: str, country: str, slug: str
    ) -> None:
        # Extract restaurant name
        name_el = card.select_one("h2, h3, a.venue-name, [data-testid='venueName']")
        if not name_el:
            return
        name = name_el.get_text(strip=True)
        if not name:
            return

        # Link / source URL
        link_el = card.select_one("a[href]")
        source_url = None
        if link_el:
            href = link_el.get("href", "")
            source_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # Rating
        rating_el = card.select_one(
            "span.rating, [data-testid='rating'], span.score, div.rating-label"
        )
        rating = self._parse_rating(rating_el.get_text() if rating_el else None)

        # Price level
        price_el = card.select_one("span.price, [data-testid='price']")
        price_level = self._parse_price(price_el.get_text() if price_el else None)

        # Cuisine tags
        cuisine_tags: list[str] = []
        tag_els = card.select("span.cuisine-tag, a.tag, [data-testid='cuisineTag']")
        for t in tag_els:
            tag_text = t.get_text(strip=True)
            if tag_text:
                cuisine_tags.append(tag_text)

        # Neighborhood
        hood_el = card.select_one("span.neighborhood, [data-testid='neighborhood']")
        neighborhood = hood_el.get_text(strip=True) if hood_el else None

        # Snippet
        snippet_el = card.select_one("p, div.review-snippet, [data-testid='snippet']")
        snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else None

        # Dedup & upsert
        place = self.dedup.lookup(name, city, self.entity_type)
        with SyncSessionLocal() as session:
            venue = self.upsert_venue(
                session,
                name=name,
                city=city,
                country=country,
                entity_type=self.entity_type,
                google_place_id=place["place_id"] if place else None,
                address=place["address"] if place else None,
                lat=place["lat"] if place else None,
                lng=place["lng"] if place else None,
                price_level=price_level,
                cuisine_tags=cuisine_tags or None,
                tags=[neighborhood] if neighborhood else None,
            )
            self.upsert_recommendation(
                session,
                venue_id=venue.id,
                source=self.source,
                source_url=source_url,
                title=name,
                snippet=snippet,
                rating=rating,
                awards=None,
            )
            session.commit()
        logger.debug("Upserted %s in %s (rating=%s)", name, city, rating)


# ── Celery task ────────────────────────────────────────────────────────

def scrape_infatuation() -> int:
    """Celery-compatible entry point."""
    job = InfatuationScraper().run()
    return job.items_found or 0
