"""Michelin Guide restaurant scraper."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.celery_app import celery
from app.db_sync import SyncSessionLocal
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

BASE_URL = "https://guide.michelin.com"

# Major cities to scrape by default.  Override via constructor.
DEFAULT_CITIES: list[dict[str, str]] = [
    {"slug": "us/new-york/restaurants", "city": "New York", "country": "US"},
    {"slug": "gb/london/restaurants", "city": "London", "country": "GB"},
    {"slug": "fr/paris/restaurants", "city": "Paris", "country": "FR"},
    {"slug": "jp/tokyo/restaurants", "city": "Tokyo", "country": "JP"},
    {"slug": "it/rome/restaurants", "city": "Rome", "country": "IT"},
    {"slug": "es/barcelona/restaurants", "city": "Barcelona", "country": "ES"},
    {"slug": "de/berlin/restaurants", "city": "Berlin", "country": "DE"},
    {"slug": "dk/copenhagen/restaurants", "city": "Copenhagen", "country": "DK"},
]

_DISTINCTION_MAP: dict[str, list[str]] = {
    "3": ["michelin_3_star"],
    "2": ["michelin_2_star"],
    "1": ["michelin_1_star"],
    "bib-gourmand": ["bib_gourmand"],
}

USER_AGENT = (
    "Mozilla/5.0 (compatible; FoodGrumpBot/1.0; +https://foodgrump.com/bot)"
)


class MichelinRestaurantScraper(BaseScraper):
    """Scrape restaurant listings from the Michelin Guide website."""

    def __init__(self, *, cities: list[dict[str, str]] | None = None) -> None:
        super().__init__(source="michelin", entity_type="restaurant")
        self.cities = cities or DEFAULT_CITIES
        self.dedup = GooglePlacesDedup()
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )

    # ── scrape implementation ─────────────────────────────────────────

    def scrape(self) -> int:
        """Scrape Michelin Guide restaurants. Returns total items processed."""
        total = 0
        try:
            for city_info in self.cities:
                total += self._scrape_city(city_info)
        finally:
            self.client.close()
        return total

    def _scrape_city(self, city_info: dict[str, str]) -> int:
        """Scrape all pages for a single city. Returns items processed."""
        city = city_info["city"]
        country = city_info["country"]
        slug = city_info["slug"]
        count = 0
        page = 1

        while True:
            url = f"{BASE_URL}/en/{slug}/page/{page}" if page > 1 else f"{BASE_URL}/en/{slug}"
            logger.info("Fetching %s (page %d)", url, page)

            try:
                resp = self.client.get(url)
                resp.raise_for_status()
            except httpx.HTTPError:
                logger.exception("Failed to fetch %s", url)
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select("div.card__menu-content, div.js-restaurant__list_item")

            if not cards:
                # Try alternate selector used in some Michelin page layouts.
                cards = soup.select("[data-restaurant-name]")

            if not cards:
                logger.info("No restaurant cards found on %s – stopping pagination", url)
                break

            for card in cards:
                try:
                    count += self._process_card(card, city, country)
                except Exception:
                    logger.exception("Error processing restaurant card on %s", url)

            # Check for next page link.
            next_link = soup.select_one("a.btn-next, a[rel='next'], li.arrow--right a")
            if next_link is None:
                break

            page += 1
            time.sleep(2)  # rate-limit between page fetches

        logger.info("City %s: processed %d restaurants", city, count)
        return count

    # ── card parsing ──────────────────────────────────────────────────

    def _process_card(self, card, city: str, country: str) -> int:
        """Parse a single restaurant card and upsert into DB. Returns 1 on success, 0 otherwise."""
        # Extract restaurant name.
        name_el = (
            card.select_one("h3.card-title, a.link, .card__menu-content--title")
            or card
        )
        name = (name_el.get("data-restaurant-name") or name_el.get_text()).strip()
        if not name:
            return 0

        # Distinction / stars.
        distinction = self._parse_distinction(card)
        awards = _DISTINCTION_MAP.get(distinction, [])

        # Cuisine type.
        cuisine_el = card.select_one(".card__menu-footer--price, .restaurant-details__classification")
        cuisine_text = cuisine_el.get_text(strip=True) if cuisine_el else ""
        cuisine_tags = [t.strip() for t in cuisine_text.split(",") if t.strip()] or []

        # Price level – count currency symbols (€/$).
        price_el = card.select_one(".price, .card__menu-footer--price")
        price_level = self._parse_price(price_el.get_text() if price_el else "")

        # Detail link (used as source_url).
        link_el = card.select_one("a[href]") or card.find_parent("a")
        detail_path = link_el["href"] if link_el else None
        source_url = f"{BASE_URL}{detail_path}" if detail_path and detail_path.startswith("/") else detail_path

        # Dedup via Google Places.
        place = self.dedup.lookup(name, city, "restaurant")
        place_id = place["place_id"] if place else None
        address = (place["address"] if place else None)
        lat = place["lat"] if place else None
        lng = place["lng"] if place else None

        # Persist.
        with SyncSessionLocal() as session:
            venue = self.upsert_venue(
                session,
                name=name,
                city=city,
                country=country,
                entity_type="restaurant",
                google_place_id=place_id,
                address=address,
                lat=lat,
                lng=lng,
                cuisine_tags=cuisine_tags or None,
                price_level=price_level,
            )
            self.upsert_recommendation(
                session,
                venue_id=venue.id,
                source=self.source,
                source_url=source_url,
                title=name,
                awards=awards or None,
                published_at=datetime.now(timezone.utc),
            )
            session.commit()

        logger.debug("Upserted restaurant %s (%s)", name, city)
        return 1

    # ── helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_distinction(card) -> str:
        """Return distinction key: '1', '2', '3', 'bib-gourmand', or ''."""
        # Look for star icons or explicit data attributes.
        star_els = card.select(".icon-michelin-star, .michelin-icon-star")
        if star_els:
            return str(len(star_els))

        distinction_el = card.select_one("[data-distinction]")
        if distinction_el:
            return distinction_el["data-distinction"]

        # Text-based fallback.
        text = card.get_text().lower()
        if "3 star" in text or "three star" in text:
            return "3"
        if "2 star" in text or "two star" in text:
            return "2"
        if "1 star" in text or "one star" in text:
            return "1"
        if "bib gourmand" in text:
            return "bib-gourmand"
        return ""

    @staticmethod
    def _parse_price(text: str) -> int | None:
        """Count currency symbols to derive price_level (1-4) or None."""
        symbols = sum(1 for c in text if c in "$€£¥")
        return symbols if 1 <= symbols <= 4 else None


# ── Celery task ───────────────────────────────────────────────────────

@celery.task(name="app.scrapers.michelin.scrape_michelin_restaurants")
def scrape_michelin_restaurants() -> dict:
    """Celery task: scrape Michelin Guide restaurants."""
    scraper = MichelinRestaurantScraper()
    job = scraper.run()
    return {"job_id": str(job.id), "status": job.status, "items_found": job.items_found}
