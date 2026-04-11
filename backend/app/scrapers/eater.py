"""Scraper for Eater 'Best Restaurants' and 'Eater 38' lists."""

from __future__ import annotations

import logging
import time
import xml.etree.ElementTree as ET

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

# city-slug → (display city, country, eater subdomain)
_CITIES: dict[str, dict[str, str]] = {
    "new-york": {"city": "New York", "country": "US", "subdomain": "ny"},
    "los-angeles": {"city": "Los Angeles", "country": "US", "subdomain": "la"},
    "san-francisco": {"city": "San Francisco", "country": "US", "subdomain": "sf"},
    "chicago": {"city": "Chicago", "country": "US", "subdomain": "chicago"},
    "london": {"city": "London", "country": "GB", "subdomain": "london"},
}

# Eater 38 map-page slug per city subdomain
_EATER_38_SLUGS: dict[str, str] = {
    "ny": "best-new-york-restaurants-38",
    "la": "best-los-angeles-restaurants-38",
    "sf": "best-san-francisco-restaurants-38",
    "chicago": "best-chicago-restaurants-38",
    "london": "best-london-restaurants-38",
}

# Rating mapping per inclusion type
_INCLUSION_RATINGS: dict[str, float] = {
    "eater_38": 10.0,
    "eater_best_of": 7.5,
    "mentioned": 4.0,
}


class EaterScraper(BaseScraper):
    """Scrape Eater best-restaurant and Eater 38 lists."""

    def __init__(self) -> None:
        super().__init__(source="eater", entity_type="restaurant")
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
                sub = meta["subdomain"]
                city = meta["city"]
                country = meta["country"]

                # Eater 38 list
                e38_slug = _EATER_38_SLUGS.get(sub)
                if e38_slug:
                    url = f"https://{sub}.eater.com/maps/{e38_slug}"
                    total += self._scrape_map_page(url, city, country, "eater_38")
                    time.sleep(2)

                # Best-of list
                best_url = f"https://{sub}.eater.com/maps/best-restaurants-{slug}"
                total += self._scrape_map_page(best_url, city, country, "eater_best_of")
                time.sleep(2)

                # RSS feed for recent mentions
                total += self._scrape_rss(sub, city, country)
                time.sleep(2)
        finally:
            self.client.close()
        return total

    # ── map / list page scraping ───────────────────────────────────────

    def _scrape_map_page(
        self, url: str, city: str, country: str, inclusion: str
    ) -> int:
        logger.info("Fetching Eater map page: %s", url)
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to fetch %s", url)
            return 0

        soup = BeautifulSoup(resp.text, "html.parser")
        entries = self._extract_map_entries(soup)
        count = 0

        for entry in entries:
            try:
                self._process_entry(entry, city, country, inclusion, url)
                count += 1
            except Exception:
                logger.exception("Error processing entry on %s", url)

        # Pagination: follow "next page" if present
        next_link = soup.select_one('a[rel="next"], a.c-pagination__next')
        if next_link:
            href = next_link.get("href", "")
            next_url = href if href.startswith("http") else f"https://eater.com{href}"
            time.sleep(2)
            count += self._scrape_map_page(next_url, city, country, inclusion)

        return count

    @staticmethod
    def _extract_map_entries(soup: BeautifulSoup) -> list[BeautifulSoup]:
        """Extract venue entries from an Eater map/list page."""
        entries = soup.select(
            "section.c-mapstack__card, div.c-mapstack__card, "
            "div[data-venue], article.c-entry-content"
        )
        if not entries:
            # Fallback: numbered headings pattern used on Eater list pages
            entries = soup.select("section.c-mapstack__item, div.venue-card, li.venue-item")
        return entries

    def _process_entry(
        self,
        entry: BeautifulSoup,
        city: str,
        country: str,
        inclusion: str,
        page_url: str,
    ) -> None:
        # Restaurant name
        name_el = entry.select_one("h1, h2, h3, a.c-mapstack__card-hed, [data-venue-name]")
        if not name_el:
            return
        name = name_el.get_text(strip=True)
        if not name:
            return

        # Source URL (link to individual entry if available)
        link_el = entry.select_one("a[href]")
        source_url = page_url
        if link_el:
            href = link_el.get("href", "")
            if href and href.startswith("http"):
                source_url = href

        # Cuisine
        cuisine_tags: list[str] = []
        cuisine_el = entry.select_one("span.cuisine, [data-cuisine]")
        if cuisine_el:
            for tag in cuisine_el.get_text(strip=True).split(","):
                tag = tag.strip()
                if tag:
                    cuisine_tags.append(tag)

        # Neighborhood
        hood_el = entry.select_one("span.neighborhood, [data-neighborhood]")
        neighborhood = hood_el.get_text(strip=True) if hood_el else None

        # Editor snippet
        snippet_el = entry.select_one("div.c-entry-content p, p.venue-description, p")
        snippet = snippet_el.get_text(strip=True)[:500] if snippet_el else None

        # Rating and awards based on inclusion type
        rating = _INCLUSION_RATINGS.get(inclusion, 4.0)
        awards = [inclusion]

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
                awards=awards,
            )
            session.commit()
        logger.debug("Upserted %s in %s (%s, rating=%s)", name, city, inclusion, rating)

    # ── RSS feed ───────────────────────────────────────────────────────

    def _scrape_rss(self, subdomain: str, city: str, country: str) -> int:
        url = f"https://{subdomain}.eater.com/rss/index.xml"
        logger.info("Fetching Eater RSS: %s", url)
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.exception("Failed to fetch RSS %s", url)
            return 0

        count = 0
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            logger.exception("Failed to parse RSS XML from %s", url)
            return 0

        # Handle both RSS 2.0 and Atom namespaces
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items:
            try:
                title_el = item.find("title") or item.find("atom:title", ns)
                link_el = item.find("link") or item.find("atom:link", ns)
                desc_el = item.find("description") or item.find("atom:summary", ns)

                title = title_el.text.strip() if title_el is not None and title_el.text else None
                if not title:
                    continue

                link_text = None
                if link_el is not None:
                    link_text = link_el.text.strip() if link_el.text else link_el.get("href")

                snippet = None
                if desc_el is not None and desc_el.text:
                    # Strip HTML from description
                    desc_soup = BeautifulSoup(desc_el.text, "html.parser")
                    snippet = desc_soup.get_text(strip=True)[:500]

                # RSS items are "mentioned" tier
                place = self.dedup.lookup(title, city, self.entity_type)
                if not place:
                    # RSS titles are often article titles, not venue names — skip if no match
                    continue

                with SyncSessionLocal() as session:
                    venue = self.upsert_venue(
                        session,
                        name=place["name"],
                        city=city,
                        country=country,
                        entity_type=self.entity_type,
                        google_place_id=place["place_id"],
                        address=place["address"],
                        lat=place["lat"],
                        lng=place["lng"],
                    )
                    self.upsert_recommendation(
                        session,
                        venue_id=venue.id,
                        source=self.source,
                        source_url=link_text,
                        title=title,
                        snippet=snippet,
                        rating=_INCLUSION_RATINGS["mentioned"],
                        awards=["mentioned"],
                    )
                    session.commit()
                count += 1
            except Exception:
                logger.exception("Error processing RSS item from %s", url)

        return count


# ── Celery task ────────────────────────────────────────────────────────

def scrape_eater() -> int:
    """Celery-compatible entry point."""
    job = EaterScraper().run()
    return job.items_found or 0
