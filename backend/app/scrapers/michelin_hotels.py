"""Michelin Hotels Guide scraper — extracts Michelin Key–awarded hotels."""

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

# Thailand-focused cities for initial launch.  Override via constructor.
DEFAULT_CITIES: list[dict[str, str]] = [
    {"city": "Bangkok", "country": "Thailand", "slug": "thailand/bangkok"},
    {"city": "Chiang Mai", "country": "Thailand", "slug": "thailand/chiang-mai"},
    {"city": "Phuket", "country": "Thailand", "slug": "thailand/phuket"},
]

_BASE_URL = "https://guide.michelin.com/en"

_KEYS_AWARD_MAP: dict[int, str] = {
    3: "michelin_3_keys",
    2: "michelin_2_keys",
    1: "michelin_1_key",
}

_REQUEST_HEADERS = {
    "User-Agent": "FoodGrumpBot/1.0 (+https://foodgrump.com)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

# Seconds to sleep between page fetches (rate-limiting).
_PAGE_DELAY = 2


class MichelinHotelScraper(BaseScraper):
    """Scrapes the Michelin Hotels Guide for Key-awarded hotels."""

    def __init__(self, *, cities: list[dict[str, str]] | None = None) -> None:
        super().__init__(source="michelin", entity_type="hotel")
        self.cities = cities or DEFAULT_CITIES
        self.dedup = GooglePlacesDedup()

    # ── core scrape ────────────────────────────────────────────────────

    def scrape(self) -> int:
        """Scrape Michelin Hotels Guide listings. Returns total items found."""
        total = 0
        for city_info in self.cities:
            try:
                count = self._scrape_city(city_info)
                total += count
            except Exception:
                logger.exception(
                    "Failed to scrape Michelin hotels for %s", city_info["city"]
                )
        return total

    # ── per-city scrape with pagination ────────────────────────────────

    def _scrape_city(self, city_info: dict[str, str]) -> int:
        city = city_info["city"]
        country = city_info["country"]
        slug = city_info["slug"]

        count = 0
        page = 1

        with httpx.Client(headers=_REQUEST_HEADERS, timeout=15, follow_redirects=True) as client:
            while True:
                url = f"{_BASE_URL}/{slug}/hotels"
                params: dict[str, str | int] = {"page": page}
                logger.info("Fetching Michelin hotels: %s page %d", city, page)

                try:
                    resp = client.get(url, params=params)
                    resp.raise_for_status()
                except httpx.HTTPError:
                    logger.exception("HTTP error fetching %s page %d", url, page)
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.select("div.card__menu, div.card__menu-content, div.hotel-card")

                # Fallback: try broader card selectors used in different layouts.
                if not cards:
                    cards = soup.select("[data-controller='hotel-card'], .js-restaurant__list_item")

                if not cards:
                    logger.info("No hotel cards found for %s page %d — stopping", city, page)
                    break

                for card in cards:
                    try:
                        parsed = self._parse_card(card, city, country)
                        if parsed:
                            count += 1
                    except Exception:
                        logger.exception("Error parsing hotel card in %s", city)

                # Check for next page.
                next_link = soup.select_one("a.btn-next, a[rel='next'], li.arrow.next a")
                if next_link is None:
                    break

                page += 1
                time.sleep(_PAGE_DELAY)

        logger.info("Scraped %d hotels for %s", count, city)
        return count

    # ── card parsing ───────────────────────────────────────────────────

    def _parse_card(self, card, city: str, country: str) -> bool:
        """Parse a single hotel card element. Returns True if upserted."""
        # Extract hotel name.
        name_el = card.select_one(
            "h2.card-title, h3.card-title, .card__menu-content--title, a.link"
        )
        if name_el is None:
            return False
        name = name_el.get_text(strip=True)
        if not name:
            return False

        # Michelin Keys (1-3): encoded as SVG icons or data attributes.
        keys_count = self._extract_keys(card)
        awards = [_KEYS_AWARD_MAP[keys_count]] if keys_count in _KEYS_AWARD_MAP else []

        # Price tier.
        price_el = card.select_one(".card__menu-price, .price, .js-price")
        price_tier = self._parse_price_tier(price_el.get_text(strip=True)) if price_el else None

        # Detail / snippet text.
        snippet_el = card.select_one(
            ".card__menu-footer--text, .card-description, .hotel-card__description"
        )
        snippet = snippet_el.get_text(strip=True) if snippet_el else None

        # Source URL.
        link_el = card.select_one("a[href]")
        source_url = None
        if link_el:
            href = link_el.get("href", "")
            source_url = href if href.startswith("http") else f"https://guide.michelin.com{href}"

        # Hotel brand detection.
        hotel_brand = self._detect_brand(card, name)

        # Dedup via Google Places.
        place = self.dedup.lookup(name, city, "hotel")
        place_id = place["place_id"] if place else None
        address = place["address"] if place else None
        lat = place["lat"] if place else None
        lng = place["lng"] if place else None

        # Persist.
        with SyncSessionLocal() as session:
            venue = self.upsert_venue(
                session,
                name=name,
                city=city,
                country=country,
                entity_type="hotel",
                google_place_id=place_id,
                address=address,
                lat=lat,
                lng=lng,
                price_level=price_tier,
                star_rating=keys_count if keys_count else None,
                hotel_brand=hotel_brand,
            )
            self.upsert_recommendation(
                session,
                venue_id=venue.id,
                source=self.source,
                source_url=source_url,
                title=f"Michelin {keys_count} Key{'s' if keys_count != 1 else ''}" if keys_count else "Michelin Hotels Guide",
                snippet=snippet,
                awards=awards or None,
                published_at=datetime.now(timezone.utc),
            )
            session.commit()

        return True

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _extract_keys(card) -> int:
        """Detect Michelin Keys count from a card element."""
        # Data attribute approach.
        keys_attr = card.get("data-keys") or card.get("data-distinction")
        if keys_attr:
            try:
                return int(keys_attr)
            except (ValueError, TypeError):
                pass

        # Count key icons.
        key_icons = card.select(".michelin-key, .icon-key, .distinction-icon--key")
        if key_icons:
            return min(len(key_icons), 3)

        # Text-based fallback: look for "3 Keys", "2 Keys", "1 Key".
        text = card.get_text(" ", strip=True)
        for n in (3, 2, 1):
            label = f"{n} Key" if n == 1 else f"{n} Keys"
            if label in text:
                return n

        return 0

    @staticmethod
    def _parse_price_tier(text: str) -> int | None:
        """Map price symbols to a 1-4 integer tier."""
        # Count currency symbols (€, $, £, ¥).
        symbols = sum(1 for c in text if c in "€$£¥")
        if symbols:
            return min(symbols, 4)
        return None

    @staticmethod
    def _detect_brand(card, name: str) -> str | None:
        """Attempt to extract a hotel brand from the card or name."""
        brand_el = card.select_one(".card__menu-brand, .hotel-brand, .brand-name")
        if brand_el:
            brand = brand_el.get_text(strip=True)
            if brand:
                return brand

        # Heuristic: check name for well-known brand prefixes.
        known_brands = [
            "Four Seasons", "Ritz-Carlton", "Mandarin Oriental", "Aman",
            "Rosewood", "St. Regis", "Park Hyatt", "Peninsula",
            "Raffles", "Belmond", "Bulgari", "Capella", "One&Only",
            "Six Senses", "Waldorf Astoria", "Conrad", "Fairmont",
            "InterContinental", "Shangri-La", "Cheval Blanc",
        ]
        for brand in known_brands:
            if brand.lower() in name.lower():
                return brand

        return None


# ── Celery task ────────────────────────────────────────────────────────

@celery.task(name="app.scrapers.michelin.scrape_michelin_hotels")
def scrape_michelin_hotels() -> dict:
    """Celery task entry point for the Michelin Hotels Guide scraper."""
    scraper = MichelinHotelScraper()
    job = scraper.run()
    return {"job_id": str(job.id), "status": job.status, "items_found": job.items_found}
