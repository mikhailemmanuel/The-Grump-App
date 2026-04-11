"""Reddit scraper — extract restaurant & hotel recommendations via Reddit + OpenAI."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone

import httpx
import openai

from app.celery_app import celery
from app.config import settings
from app.db_sync import SyncSessionLocal
from app.scrapers.base import BaseScraper
from app.scrapers.dedup import GooglePlacesDedup

logger = logging.getLogger(__name__)

# ── Reddit configuration ───────────────────────────────────────────────

_REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
_REDDIT_SEARCH_URL = "https://oauth.reddit.com/r/{subreddit}/search"
_REDDIT_COMMENTS_URL = "https://oauth.reddit.com/comments/{article_id}"

_USER_AGENT = "FoodGrump/1.0 (scraper)"
_REQUEST_DELAY = 2  # seconds between Reddit API calls

_RESTAURANT_SUBREDDITS = [
    "FoodNYC",
    "AskSF",
    "chicagofood",
    "foodlosangeles",
    "londonfoodies",
    "TokyoFoods",
    "parisfoodies",
]

_HOTEL_SUBREDDITS = [
    "fattravel",
    "travel",
    "solotravel",
    "luxurytravel",
    "hotels",
    "JapanTravel",
    "VisitingNYC",
]

_RESTAURANT_QUERIES = ["best restaurant", "recommendation", "where to eat"]
_HOTEL_QUERIES = ["best hotel", "where to stay", "hotel recommendation"]

_SENTIMENT_SCORES = {"positive": 0.9, "mixed": 0.5, "negative": 0.2}

# ── Reddit OAuth helpers ───────────────────────────────────────────────


def _get_reddit_token() -> str:
    """Obtain a Reddit OAuth bearer token using client credentials flow."""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")

    resp = httpx.post(
        _REDDIT_TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": _USER_AGENT},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _reddit_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
    }


# ── Reddit search + comment fetching ──────────────────────────────────


def _search_subreddit(
    token: str,
    subreddit: str,
    query: str,
    limit: int = 50,
) -> list[dict]:
    """Search a subreddit for threads matching query. Returns listing data."""
    url = _REDDIT_SEARCH_URL.format(subreddit=subreddit)
    try:
        resp = httpx.get(
            url,
            params={
                "q": query,
                "sort": "top",
                "limit": limit,
                "restrict_sr": "on",
                "t": "year",
            },
            headers=_reddit_headers(token),
            timeout=15,
        )
        resp.raise_for_status()
        time.sleep(_REQUEST_DELAY)
        return resp.json().get("data", {}).get("children", [])
    except httpx.HTTPError:
        logger.exception("Reddit search failed: r/%s q=%s", subreddit, query)
        return []


def _fetch_thread_comments(token: str, article_id: str, limit: int = 50) -> list[str]:
    """Fetch top comments from a Reddit thread. Returns comment body texts."""
    url = _REDDIT_COMMENTS_URL.format(article_id=article_id)
    try:
        resp = httpx.get(
            url,
            params={"sort": "top", "limit": limit},
            headers=_reddit_headers(token),
            timeout=15,
        )
        resp.raise_for_status()
        time.sleep(_REQUEST_DELAY)

        listings = resp.json()
        comments: list[str] = []
        if len(listings) >= 2:
            for child in listings[1].get("data", {}).get("children", []):
                body = child.get("data", {}).get("body", "")
                if body and len(body) > 20:
                    comments.append(body[:2000])  # cap long comments
        return comments
    except httpx.HTTPError:
        logger.exception("Reddit comment fetch failed: %s", article_id)
        return []


# ── OpenAI LLM extraction ─────────────────────────────────────────────


def _extract_venues_llm(comments: list[str], entity_type: str) -> list[dict]:
    """Use GPT-4o-mini to extract venue recommendations from Reddit comments.

    Returns list of dicts with keys: name, city, sentiment, context_quote,
    and cuisine (restaurants only).
    """
    if not comments:
        return []

    entity_label = "restaurant" if entity_type == "restaurant" else "hotel"
    joined = "\n---\n".join(comments[:30])  # batch size cap

    prompt = (
        f"Extract {entity_label} recommendations from these Reddit comments. "
        f"For each, return: {{name, city, sentiment: positive/negative/mixed, "
        f"context_quote"
        f'{", cuisine" if entity_type == "restaurant" else ""}}}. '
        f"Only include entries where a specific {entity_label} name is mentioned. "
        f"Return as a JSON array. If none found, return [].\n\n"
        f"Comments:\n{joined}"
    )

    client = openai.OpenAI(api_key=settings.openai_api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You extract structured venue data from Reddit comments. "
                        "Respond with only a JSON array, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0]
        venues = json.loads(raw)
        # Filter out entries missing required fields
        return [
            v
            for v in venues
            if isinstance(v, dict) and v.get("name") and v.get("city")
        ]
    except (openai.OpenAIError, json.JSONDecodeError, KeyError):
        logger.exception("OpenAI extraction failed")
        return []


# ── Scraper classes ────────────────────────────────────────────────────


class _RedditBaseScraper(BaseScraper):
    """Shared logic for Reddit restaurant/hotel scrapers."""

    subreddits: list[str]
    queries: list[str]

    def scrape(self) -> int:
        token = _get_reddit_token()
        dedup = GooglePlacesDedup()
        count = 0

        for subreddit in self.subreddits:
            for query in self.queries:
                try:
                    threads = _search_subreddit(token, subreddit, query, limit=50)
                except Exception:
                    logger.exception(
                        "Search error r/%s q=%s", subreddit, query
                    )
                    continue

                # Collect comments across threads for batch extraction
                all_comments: list[tuple[str, str]] = []  # (comment, thread_url)
                for thread in threads:
                    td = thread.get("data", {})
                    article_id = td.get("id", "")
                    permalink = td.get("permalink", "")
                    if not article_id:
                        continue

                    try:
                        comments = _fetch_thread_comments(token, article_id)
                    except Exception:
                        logger.exception("Comment fetch error: %s", article_id)
                        continue

                    thread_url = f"https://www.reddit.com{permalink}" if permalink else None
                    for c in comments:
                        all_comments.append((c, thread_url))

                if not all_comments:
                    continue

                # Batch LLM extraction
                comment_texts = [c for c, _ in all_comments]
                # Use first thread url as fallback source_url
                default_url = all_comments[0][1] if all_comments else None

                try:
                    extracted = _extract_venues_llm(comment_texts, self.entity_type)
                except Exception:
                    logger.exception("LLM extraction error for r/%s", subreddit)
                    continue

                # Persist extracted venues
                with SyncSessionLocal() as session:
                    for item in extracted:
                        try:
                            name = item["name"]
                            city = item["city"]
                            sentiment = item.get("sentiment", "mixed")
                            quote = item.get("context_quote", "")
                            cuisine = item.get("cuisine")

                            # Dedup via Google Places
                            place_data = dedup.lookup(name, city, self.entity_type)

                            venue_kwargs: dict = {
                                "name": name,
                                "city": city,
                                "country": "",  # unknown from Reddit
                                "entity_type": self.entity_type,
                            }
                            if place_data:
                                venue_kwargs.update(
                                    google_place_id=place_data.get("place_id"),
                                    address=place_data.get("address"),
                                    lat=place_data.get("lat"),
                                    lng=place_data.get("lng"),
                                )
                            if cuisine and self.entity_type == "restaurant":
                                venue_kwargs["cuisine_tags"] = [cuisine]

                            venue = self.upsert_venue(session, **venue_kwargs)

                            sentiment_score = _SENTIMENT_SCORES.get(sentiment, 0.5)
                            self.upsert_recommendation(
                                session,
                                venue_id=venue.id,
                                source=self.source,
                                source_url=default_url,
                                title=name,
                                snippet=quote[:500] if quote else None,
                                rating=round(sentiment_score * 10, 1),
                            )
                            count += 1
                        except Exception:
                            logger.exception(
                                "Error processing venue %s", item.get("name")
                            )
                            continue
                    session.commit()

        return count


class RedditRestaurantScraper(_RedditBaseScraper):
    """Scrape Reddit for restaurant recommendations."""

    subreddits = _RESTAURANT_SUBREDDITS
    queries = _RESTAURANT_QUERIES

    def __init__(self) -> None:
        super().__init__(source="reddit", entity_type="restaurant")


class RedditHotelScraper(_RedditBaseScraper):
    """Scrape Reddit for hotel recommendations."""

    subreddits = _HOTEL_SUBREDDITS
    queries = _HOTEL_QUERIES

    def __init__(self) -> None:
        super().__init__(source="reddit", entity_type="hotel")


# ── Celery tasks ───────────────────────────────────────────────────────


@celery.task(name="app.scrapers.reddit.scrape_reddit_restaurants")
def scrape_reddit_restaurants() -> dict:
    """Celery entry-point for the Reddit restaurant scraper."""
    job = RedditRestaurantScraper().run()
    return {"job_id": job.id, "status": job.status, "items_found": job.items_found}


@celery.task(name="app.scrapers.reddit.scrape_reddit_hotels")
def scrape_reddit_hotels() -> dict:
    """Celery entry-point for the Reddit hotel scraper."""
    job = RedditHotelScraper().run()
    return {"job_id": job.id, "status": job.status, "items_found": job.items_found}
