"""Composite scoring pipeline for FoodGrump venue rankings."""

import logging
from datetime import datetime, timezone

from sqlalchemy import distinct, select, delete

from app.celery_app import celery
from app.db_sync import SyncSessionLocal
from app.models.user import UserReview
from app.models.venue import CityRanking, Recommendation, Venue

logger = logging.getLogger(__name__)

# ── Weight tables ────────────────────────────────────────────────────
RESTAURANT_WEIGHTS: dict[str, float] = {
    "foodgrump": 0.20,
    "michelin": 0.15,
    "reddit": 0.15,
    "beli": 0.15,
    "google": 0.15,
    "infatuation": 0.10,
    "eater": 0.10,
}

HOTEL_WEIGHTS: dict[str, float] = {
    "foodgrump": 0.25,
    "conde_nast": 0.20,
    "michelin": 0.20,
    "google": 0.20,
    "reddit": 0.15,
}

# ── Award mappings ───────────────────────────────────────────────────
MICHELIN_AWARD_SCORES: dict[str, float] = {
    "3_stars": 100, "3_keys": 100,
    "2_stars": 90, "2_keys": 90,
    "1_star": 80, "1_key": 80,
    "bib_gourmand": 65,
    "listed": 50,
}

EATER_AWARD_SCORES: dict[str, float] = {
    "eater_38": 100,
    "best_of": 75,
    "mentioned": 40,
}

CONDE_NAST_AWARD_SCORES: dict[str, float] = {
    "cn_gold_list": 100,
    "cn_hot_list": 90,
    "cn_readers_choice": 85,
    "reviewed": 50,
}

VERDICT_SCORES: dict[str, float] = {
    "go_back": 100,
    "iffy": 50,
    "would_not_go_back": 0,
}


def _recency_factor(published_at: datetime | None) -> float:
    """Return a decay multiplier based on recommendation age."""
    if published_at is None:
        return 1.0
    now = datetime.now(timezone.utc)
    age_days = (now - published_at).days
    if age_days > 3 * 365:
        return 0.5
    if age_days > 18 * 30:  # ~18 months
        return 0.8
    return 1.0


def _best_award_score(awards: list[str] | None, mapping: dict[str, float]) -> float:
    """Return the highest matching award score, or 0."""
    if not awards:
        return 0.0
    return max((mapping.get(a, 0.0) for a in awards), default=0.0)


def _source_score_from_rec(rec: Recommendation, source: str) -> float:
    """Compute raw 0-100 score for a single recommendation by source type."""
    if source == "michelin":
        return _best_award_score(rec.awards, MICHELIN_AWARD_SCORES)
    if source == "eater":
        return _best_award_score(rec.awards, EATER_AWARD_SCORES)
    if source == "conde_nast":
        return _best_award_score(rec.awards, CONDE_NAST_AWARD_SCORES)
    if source in ("reddit", "beli", "infatuation"):
        # 0-10 → 0-100
        return (rec.rating or 0.0) * 10.0
    if source == "google":
        # 1-5 → 0-100
        if rec.rating is not None:
            return (rec.rating - 1.0) * 25.0
        return 0.0
    return 0.0


def compute_venue_score(session, venue: Venue, entity_type: str) -> tuple[float, dict]:
    """Compute composite score and per-source breakdown for a venue.

    Returns:
        (composite_score, source_scores_dict)
    """
    weights = RESTAURANT_WEIGHTS if entity_type == "restaurant" else HOTEL_WEIGHTS

    # ── FoodGrump user reviews ───────────────────────────────────────
    reviews = session.execute(
        select(UserReview.verdict).where(UserReview.venue_id == venue.id)
    ).scalars().all()

    source_scores: dict[str, float] = {}

    if reviews:
        avg = sum(VERDICT_SCORES.get(v, 0) for v in reviews) / len(reviews)
        source_scores["foodgrump"] = avg
    else:
        source_scores["foodgrump"] = 0.0

    # ── External recommendations ─────────────────────────────────────
    recs = session.execute(
        select(Recommendation).where(Recommendation.venue_id == venue.id)
    ).scalars().all()

    # Group by source, keep best score per source (with recency decay)
    for src in weights:
        if src == "foodgrump":
            continue
        best = 0.0
        for rec in recs:
            if rec.source != src:
                continue
            raw = _source_score_from_rec(rec, src)
            decayed = raw * _recency_factor(rec.published_at)
            best = max(best, decayed)
        source_scores[src] = best

    # ── Weighted composite with re-normalization ─────────────────────
    present = {s: w for s, w in weights.items() if source_scores.get(s, 0) > 0}
    if present:
        total_weight = sum(present.values())
        weighted_sum = sum(
            (w / total_weight) * source_scores[s] for s, w in present.items()
        )
    else:
        weighted_sum = 0.0

    # ── Source count bonus ───────────────────────────────────────────
    nonzero_count = sum(1 for s in weights if source_scores.get(s, 0) > 0)
    bonus = min((max(nonzero_count - 2, 0)) * 5, 15)

    composite = min(max(weighted_sum + bonus, 0.0), 100.0)

    return composite, source_scores


def compute_city_rankings(session, city: str, entity_type: str) -> None:
    """Compute and persist rankings for all venues in a city + entity_type."""
    venues = session.execute(
        select(Venue).where(Venue.city == city, Venue.entity_type == entity_type)
    ).scalars().all()

    scored: list[tuple[Venue, float, dict]] = []
    for venue in venues:
        composite, source_scores = compute_venue_score(session, venue, entity_type)
        scored.append((venue, composite, source_scores))

    # Sort descending by composite score
    scored.sort(key=lambda x: x[1], reverse=True)

    # Delete old rankings for this city + entity_type
    session.execute(
        delete(CityRanking).where(
            CityRanking.city == city,
            CityRanking.entity_type == entity_type,
        )
    )

    # Insert new rankings
    now = datetime.now(timezone.utc)
    for rank, (venue, composite, source_scores) in enumerate(scored, start=1):
        session.add(CityRanking(
            venue_id=venue.id,
            entity_type=entity_type,
            city=city,
            composite_score=composite,
            rank=rank,
            source_scores=source_scores,
            computed_at=now,
        ))

    session.flush()


@celery.task(name="app.scrapers.scoring.compute_all_rankings")
def compute_all_rankings() -> None:
    """Celery task: recompute rankings for every (city, entity_type) pair."""
    with SyncSessionLocal() as session:
        pairs = session.execute(
            select(distinct(Venue.city), Venue.entity_type)
        ).all()

        for city, entity_type in pairs:
            logger.info("Computing rankings: city=%s entity_type=%s", city, entity_type)
            compute_city_rankings(session, city, entity_type)

        session.commit()
    logger.info("All rankings computed for %d city/type pairs", len(pairs))
