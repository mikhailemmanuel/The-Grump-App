"""Condé Nast Traveler scraper — hotel awards (Gold List, Hot List, Readers' Choice)."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.celery_app import celery
from app.db_sync import SyncSessionLocal
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

_AWARD_URLS: list[tuple[str, str]] = [
    ("https://www.cntraveler.com/the-gold-list", "cn_gold_list"),
    ("https://www.cntraveler.com/hot-list", "cn_hot_list"),
    ("https://www.cntraveler.com/readers-choice-awards", "cn_readers_choice"),
]

_PAGE_DELAY = 3  # seconds between HTTP requests — be respectful


class CondeNastScraper(BaseScraper):
    """Scrape cntraveler.com for hotel award lists."""

    def __init__(self) -> None:
        super().__init__(source="conde_nast", entity_type="hotel")
        self.dedup = GooglePlacesDedup()
        self.client = httpx.Client(
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
            timeout=30,
        )

    # ── abstract implementation ────────────────────────────────────────

    def scrape(self) -> int:
        total = 0
        for url, award_key in _AWARD_URLS:
            try:
                count = self._scrape_award_list(url, award_key)
                total += count
                logger.info("Condé Nast %s: found %d hotels", award_key, count)
            except Exception:
                logger.exception("Error scraping %s (%s)", award_key, url)
            time.sleep(_PAGE_DELAY)
        self.client.close()
        return total

    # ── internals ──────────────────────────────────────────────────────

    def _scrape_award_list(self, url: str, award_key: str) -> int:
        """Fetch an award landing page and extract hotel entries."""
        resp = self.client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Detect the current year from the page (e.g. "2025 Gold List")
        year = self._extract_year(soup)

        # Gather hotel links from the listing page
        hotel_links = self._extract_hotel_links(soup, url)
        logger.info("Condé Nast %s %s: %d hotel links found", award_key, year, len(hotel_links))

        count = 0
        for link in hotel_links:
            try:
                hotel = self._parse_hotel_link(link)
                if hotel is None:
                    continue
                self._persist(hotel, award_key, url, year)
                count += 1
            except Exception:
                logger.exception("Error processing hotel link %s", link)
            time.sleep(_PAGE_DELAY)
        return count

    def _extract_year(self, soup: BeautifulSoup) -> str:
        """Try to pull the award year from the page title or heading."""
        title = soup.find("h1") or soup.find("title")
        if title:
            match = re.search(r"(20\d{2})", title.get_text())
            if match:
                return match.group(1)
        return str(datetime.now(timezone.utc).year)

    def _extract_hotel_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """Extract unique hotel article links from the listing page."""
        links: list[str] = []
        seen: set[str] = set()
        for a_tag in soup.find_all("a", href=True):
            href: str = a_tag["href"]
            # CN hotel pages typically match /story/hotels/...
            if "/story/" not in href and "/hotels/" not in href:
                continue
            # Normalise to absolute URL
            if href.startswith("/"):
                href = "https://www.cntraveler.com" + href
            if href not in seen:
                seen.add(href)
                links.append(href)
        return links

    def _parse_hotel_link(self, url: str) -> dict | None:
        """Fetch an individual hotel page and extract structured data."""
        resp = self.client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Hotel name — try <h1>, then <title>
        h1 = soup.find("h1")
        name = h1.get_text(strip=True) if h1 else None
        if not name:
            title_tag = soup.find("title")
            name = title_tag.get_text(strip=True).split("|")[0].strip() if title_tag else None
        if not name:
            return None

        # City — look for structured data or common patterns
        city = self._extract_city(soup)
        if not city:
            logger.warning("Could not determine city for %s (%s)", name, url)
            return None

        # Editor snippet — first <p> in the article body
        snippet = None
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 60:
                snippet = text[:500]
                break

        return {"name": name, "city": city, "snippet": snippet, "url": url}

    @staticmethod
    def _extract_city(soup: BeautifulSoup) -> str | None:
        """Best-effort city extraction from a CN hotel page."""
        # Try JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            import json

            try:
                ld = json.loads(script.string or "")
                if isinstance(ld, dict):
                    addr = ld.get("address") or {}
                    city = addr.get("addressLocality")
                    if city:
                        return city
                if isinstance(ld, list):
                    for item in ld:
                        addr = (item or {}).get("address") or {}
                        city = addr.get("addressLocality")
                        if city:
                            return city
            except (json.JSONDecodeError, TypeError):
                continue
        # Fallback: look for a subtitle/dek element mentioning a city
        for sel in ("p.dek", "p.rubric__dek", ".content-header__dek", "[class*='subtitle']"):
            tag = soup.select_one(sel)
            if tag:
                text = tag.get_text(strip=True)
                if text:
                    return text.split(",")[0].strip()
        return None

    def _persist(
        self,
        hotel: dict,
        award_key: str,
        source_url: str,
        year: str,
    ) -> None:
        """Dedup via Google Places, then upsert venue + recommendation."""
        name = hotel["name"]
        city = hotel["city"]

        place = self.dedup.lookup(name, city, "hotel")
        google_place_id = place["place_id"] if place else None
        address = place["address"] if place else None
        lat = place["lat"] if place else None
        lng = place["lng"] if place else None

        with SyncSessionLocal() as session:
            venue = self.upsert_venue(
                session,
                name=place["name"] if place else name,
                city=city,
                country="",  # CN doesn't always provide country; dedup fills address
                entity_type="hotel",
                google_place_id=google_place_id,
                address=address,
                lat=lat,
                lng=lng,
            )
            self.upsert_recommendation(
                session,
                venue_id=venue.id,
                source=self.source,
                source_url=hotel.get("url") or source_url,
                title=f"Condé Nast Traveler {award_key.replace('cn_', '').replace('_', ' ').title()} {year}",
                snippet=hotel.get("snippet"),
                awards=[award_key],
            )
            session.commit()


# ── Celery task ────────────────────────────────────────────────────────


@celery.task(name="app.scrapers.conde_nast.scrape_conde_nast")
def scrape_conde_nast() -> dict:
    """Celery entry-point for the Condé Nast Traveler hotel scraper."""
    job = CondeNastScraper().run()
    return {"job_id": job.id, "status": job.status, "items_found": job.items_found}
