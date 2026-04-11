"""AI-powered review summary generation for venues using GPT-4o-mini."""

import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import openai
from sqlalchemy import func

from app.celery_app import celery
from app.config import settings
from app.db_sync import SyncSessionLocal
from app.models.user import ReviewPhoto, UserReview
from app.models.venue import Venue, VenueSummary

logger = logging.getLogger(__name__)

RESTAURANT_PROMPT = (
    "You are summarizing user reviews for a restaurant. "
    "Given these reviews, write a 2-3 sentence summary highlighting the most-praised "
    "dishes and any recurring complaints. Also list the top 5 most-mentioned dishes "
    'as a JSON array. Return JSON: {"summary": string, "highlights": string[]}'
)

HOTEL_PROMPT = (
    "You are summarizing user reviews for a hotel. "
    "Given these reviews, write a 2-3 sentence summary highlighting the most-praised "
    "amenities, room quality, and location. Note any recurring complaints. Also list "
    "the top 5 most-mentioned amenities/features as a JSON array. "
    'Return JSON: {"summary": string, "highlights": string[]}'
)

MIN_REVIEWS_FOR_AI = 3


def generate_venue_summary(venue_id: UUID) -> None:
    """Fetch reviews for a venue, compute sentiment, and generate an AI summary."""
    with SyncSessionLocal() as session:
        # Fetch venue to determine entity_type
        venue = session.query(Venue).filter(Venue.id == venue_id).first()
        if venue is None:
            logger.warning("Venue %s not found, skipping summary generation", venue_id)
            return

        entity_type: str = venue.entity_type

        # Fetch all reviews for this venue
        reviews = (
            session.query(UserReview)
            .filter(UserReview.venue_id == venue_id)
            .all()
        )

        review_count = len(reviews)
        review_ids = [r.id for r in reviews]

        # Fetch all photos for those reviews
        photos = (
            session.query(ReviewPhoto)
            .filter(ReviewPhoto.review_id.in_(review_ids))
            .all()
        ) if review_ids else []

        photo_count = len(photos)

        # Compute sentiment breakdown from all reviews
        sentiment_breakdown = {"positive": 0, "mixed": 0, "negative": 0}
        for review in reviews:
            if review.verdict == "go_back":
                sentiment_breakdown["positive"] += 1
            elif review.verdict == "iffy":
                sentiment_breakdown["mixed"] += 1
            elif review.verdict == "would_not_go_back":
                sentiment_breakdown["negative"] += 1

        # Collect comments from public reviews only (for AI input)
        public_comments = [
            r.comment for r in reviews if r.is_public and r.comment
        ]

        # Collect photo captions
        captions = [p.caption for p in photos if p.caption]

        ai_summary = None
        highlights = None

        if review_count >= MIN_REVIEWS_FOR_AI and public_comments:
            ai_summary, highlights = _call_openai(
                entity_type, public_comments, captions
            )

        # Upsert VenueSummary
        existing = (
            session.query(VenueSummary)
            .filter(VenueSummary.venue_id == venue_id)
            .first()
        )

        now = datetime.now(timezone.utc)

        if existing:
            if ai_summary is not None:
                existing.ai_summary = ai_summary
                existing.highlights = highlights
            existing.sentiment_breakdown = sentiment_breakdown
            existing.photo_count = photo_count
            existing.review_count = review_count
            existing.computed_at = now
        else:
            summary = VenueSummary(
                venue_id=venue_id,
                ai_summary=ai_summary,
                highlights=highlights,
                sentiment_breakdown=sentiment_breakdown,
                photo_count=photo_count,
                review_count=review_count,
                computed_at=now,
            )
            session.add(summary)

        session.commit()
        logger.info(
            "Updated summary for venue %s (reviews=%d, photos=%d)",
            venue_id, review_count, photo_count,
        )


def _call_openai(
    entity_type: str,
    comments: list[str],
    captions: list[str],
) -> tuple[str | None, list[str] | None]:
    """Call GPT-4o-mini and return (summary, highlights)."""
    system_prompt = RESTAURANT_PROMPT if entity_type == "restaurant" else HOTEL_PROMPT

    user_content_parts = ["Reviews:\n" + "\n---\n".join(comments)]
    if captions:
        user_content_parts.append("Photo captions:\n" + "\n".join(captions))
    user_content = "\n\n".join(user_content_parts)

    try:
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
            max_tokens=512,
        )

        raw = response.choices[0].message.content
        data = json.loads(raw)
        summary = data.get("summary", "")
        highlights = data.get("highlights", [])
        # Ensure highlights is a list of strings, capped at 5
        highlights = [str(h) for h in highlights[:5]] if highlights else []
        return summary, highlights

    except (openai.OpenAIError, json.JSONDecodeError, KeyError) as exc:
        logger.error("OpenAI call failed for entity_type=%s: %s", entity_type, exc)
        return None, None


# ── Celery Tasks ─────────────────────────────────────────────────────


@celery.task(name="app.scrapers.ai_summary.generate_summary_for_venue", bind=True, max_retries=2)
def generate_summary_for_venue(self, venue_id_str: str) -> None:  # noqa: ANN001
    """On-demand task to generate a summary for a single venue.

    Debounces by skipping if the summary was computed less than 1 hour ago.
    """
    venue_id = UUID(venue_id_str)

    with SyncSessionLocal() as session:
        existing = (
            session.query(VenueSummary)
            .filter(VenueSummary.venue_id == venue_id)
            .first()
        )
        if existing and existing.computed_at:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            if existing.computed_at.replace(tzinfo=timezone.utc) > cutoff:
                logger.info(
                    "Skipping venue %s — summary computed at %s (within 1h debounce)",
                    venue_id, existing.computed_at,
                )
                return

    try:
        generate_venue_summary(venue_id)
    except Exception as exc:
        logger.exception("Failed to generate summary for venue %s", venue_id)
        raise self.retry(exc=exc, countdown=60) from exc


@celery.task(name="app.scrapers.ai_summary.generate_all_summaries")
def generate_all_summaries() -> None:
    """Nightly batch task: regenerate summaries for venues with >= 5 reviews."""
    BATCH_SIZE = 20

    with SyncSessionLocal() as session:
        # Find venue IDs with at least 5 reviews
        venue_ids = (
            session.query(UserReview.venue_id)
            .group_by(UserReview.venue_id)
            .having(func.count(UserReview.id) >= 5)
            .all()
        )

    venue_id_list = [row[0] for row in venue_ids]
    total = len(venue_id_list)
    logger.info("Nightly AI summary: %d venues to process", total)

    for i in range(0, total, BATCH_SIZE):
        batch = venue_id_list[i : i + BATCH_SIZE]
        for vid in batch:
            try:
                generate_venue_summary(vid)
            except Exception:
                logger.exception("Failed summary for venue %s, continuing", vid)

        logger.info("Processed batch %d–%d of %d", i + 1, min(i + BATCH_SIZE, total), total)

    logger.info("Nightly AI summary complete: %d venues processed", total)
