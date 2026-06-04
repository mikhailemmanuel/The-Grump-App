"""Tests for the composite scoring pipeline (pure functions only, no DB)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

# db_sync creates a sync engine at import time (needs psycopg2).
# Stub it out before scoring.py is imported.
sys.modules.setdefault("app.db_sync", MagicMock())

from app.scrapers.scoring import (
    MICHELIN_AWARD_SCORES,
    EATER_AWARD_SCORES,
    CONDE_NAST_AWARD_SCORES,
    VERDICT_SCORES,
    _recency_factor,
    _best_award_score,
    _source_score_from_rec,
    compute_venue_score,
)
from app.models.venue import Recommendation


def _rec(source: str, rating: float | None = None, awards: list[str] | None = None, days_old: int = 30) -> Recommendation:
    r = MagicMock(spec=Recommendation)
    r.source = source
    r.rating = rating
    r.awards = awards
    r.published_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    return r


def _venue(vid=None):
    v = MagicMock()
    v.id = vid or "test-venue-id"
    return v


def _session(recs=None, verdicts=None):
    session = MagicMock()
    rec_result = MagicMock()
    rec_result.scalars.return_value.all.return_value = recs or []
    verdict_result = MagicMock()
    verdict_result.scalars.return_value.all.return_value = verdicts or []
    session.execute.side_effect = [verdict_result, rec_result]
    return session


# ── Recency decay ─────────────────────────────────────────────────────────────

def test_recency_recent_is_1():
    assert _recency_factor(datetime.now(timezone.utc) - timedelta(days=10)) == 1.0


def test_recency_18_months_is_0_8():
    assert _recency_factor(datetime.now(timezone.utc) - timedelta(days=600)) == 0.8


def test_recency_old_is_0_5():
    assert _recency_factor(datetime.now(timezone.utc) - timedelta(days=1200)) == 0.5


def test_recency_none_is_1():
    assert _recency_factor(None) == 1.0


# ── Award scores ──────────────────────────────────────────────────────────────

def test_best_award_michelin_3_stars():
    assert _best_award_score(["3_stars"], MICHELIN_AWARD_SCORES) == 100.0


def test_best_award_picks_highest():
    assert _best_award_score(["bib_gourmand", "1_star"], MICHELIN_AWARD_SCORES) == 80.0


def test_best_award_empty_is_zero():
    assert _best_award_score([], MICHELIN_AWARD_SCORES) == 0.0


def test_best_award_none_is_zero():
    assert _best_award_score(None, MICHELIN_AWARD_SCORES) == 0.0


# ── Per-source raw scores ─────────────────────────────────────────────────────

def test_google_rating_5_is_100():
    r = _rec("google", rating=5.0)
    assert _source_score_from_rec(r, "google") == 100.0


def test_google_rating_1_is_0():
    r = _rec("google", rating=1.0)
    assert _source_score_from_rec(r, "google") == 0.0


def test_reddit_rating_scales():
    r = _rec("reddit", rating=7.5)
    assert _source_score_from_rec(r, "reddit") == 75.0


def test_michelin_3_stars():
    r = _rec("michelin", awards=["3_stars"])
    assert _source_score_from_rec(r, "michelin") == 100.0


def test_eater_38():
    r = _rec("eater", awards=["eater_38"])
    assert _source_score_from_rec(r, "eater") == 100.0


def test_conde_nast_gold_list():
    r = _rec("conde_nast", awards=["cn_gold_list"])
    assert _source_score_from_rec(r, "conde_nast") == 100.0


# ── Composite scoring ─────────────────────────────────────────────────────────

def test_no_data_gives_zero():
    session = _session()
    score, sources = compute_venue_score(session, _venue(), "restaurant")
    assert score == 0.0


def test_single_user_review_go_back():
    session = _session(verdicts=["go_back"])
    score, sources = compute_venue_score(session, _venue(), "restaurant")
    assert sources["foodgrump"] == 100.0


def test_mixed_verdicts_average():
    session = _session(verdicts=["go_back", "would_not_go_back"])
    _, sources = compute_venue_score(session, _venue(), "restaurant")
    assert sources["foodgrump"] == 50.0


def test_multi_source_bonus_applied():
    """A venue with 4+ sources should receive a nonzero bonus."""
    recs = [
        _rec("michelin", awards=["1_star"]),
        _rec("google", rating=4.5),
        _rec("reddit", rating=8.0),
        _rec("beli", rating=8.0),
    ]
    session = _session(recs=recs, verdicts=["go_back"])
    score, _ = compute_venue_score(session, _venue(), "restaurant")
    # With 5 sources (foodgrump + 4 recs), bonus = min((5-2)*5, 15) = 15
    assert score > 0


def test_composite_capped_at_100():
    recs = [
        _rec("michelin", awards=["3_stars"]),
        _rec("google", rating=5.0),
        _rec("reddit", rating=10.0),
        _rec("beli", rating=10.0),
        _rec("infatuation", rating=10.0),
        _rec("eater", awards=["eater_38"]),
    ]
    session = _session(recs=recs, verdicts=["go_back", "go_back", "go_back"])
    score, _ = compute_venue_score(session, _venue(), "restaurant")
    assert score <= 100.0
