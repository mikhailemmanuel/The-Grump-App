"""Initial schema — create all tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-04-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS extension (Supabase supports this)
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── Enum types ────────────────────────────────────────────────────
    # Created via raw SQL with IF NOT EXISTS for idempotency.
    # Column types use sa.String() to avoid SQLAlchemy DDL events;
    # the ORM models enforce enum values at the application level.
    # These types are kept for documentation / potential future use.
    op.execute("DO $$ BEGIN CREATE TYPE entity_type AS ENUM ('restaurant', 'hotel'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE source_type AS ENUM ('reddit', 'infatuation', 'eater', 'beli', 'michelin', 'google', 'conde_nast'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE platform_type AS ENUM ('resy', 'opentable', 'sevenrooms', 'tock', 'yelp_reservations', 'booking_com', 'hotels_com', 'expedia', 'hotel_direct'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE verdict_type AS ENUM ('go_back', 'iffy', 'would_not_go_back'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE list_entity_type AS ENUM ('restaurant', 'hotel', 'mixed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE scrape_status AS ENUM ('pending', 'running', 'done', 'failed'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # ── venues ────────────────────────────────────────────────────────
    op.create_table(
        "venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(20), nullable=False, index=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("normalized_name", sa.Text, nullable=False, index=True),
        sa.Column("address", sa.Text),
        sa.Column("city", sa.String(255), nullable=False, index=True),
        sa.Column("country", sa.String(255)),
        sa.Column("location", sa.Text, nullable=True),  # stored as WKT string; PostGIS POINT
        sa.Column("tags", postgresql.ARRAY(sa.Text)),
        sa.Column("price_level", sa.Integer),
        sa.Column("google_place_id", sa.String(255), unique=True, index=True),
        sa.Column("cuisine_tags", postgresql.ARRAY(sa.Text)),
        sa.Column("star_rating", sa.Integer),
        sa.Column("room_count", sa.Integer),
        sa.Column("hotel_brand", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── recommendations ───────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source", sa.String(20), nullable=False, index=True),
        sa.Column("source_url", sa.Text),
        sa.Column("title", sa.Text),
        sa.Column("snippet", sa.Text),
        sa.Column("rating", sa.Float),
        sa.Column("awards", postgresql.ARRAY(sa.Text)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── reservation_links ─────────────────────────────────────────────
    op.create_table(
        "reservation_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("booking_url", sa.Text, nullable=False),
        sa.Column("venue_id_ext", sa.String(255)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
    )

    # ── city_rankings ─────────────────────────────────────────────────
    op.create_table(
        "city_rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("entity_type", sa.String(20), nullable=False, index=True),
        sa.Column("city", sa.String(255), nullable=False, index=True),
        sa.Column("composite_score", sa.Float, nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("source_scores", postgresql.JSONB),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text),
        sa.Column("reviews_public", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── user_reviews ──────────────────────────────────────────────────
    op.create_table(
        "user_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("visited_at", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── review_photos ─────────────────────────────────────────────────
    op.create_table(
        "review_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_reviews.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.Text, nullable=False),
        sa.Column("caption", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── venue_summaries ───────────────────────────────────────────────
    op.create_table(
        "venue_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("ai_summary", sa.Text),
        sa.Column("highlights", postgresql.ARRAY(sa.Text)),
        sa.Column("sentiment_breakdown", postgresql.JSONB),
        sa.Column("photo_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("review_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── want_to_go ────────────────────────────────────────────────────
    op.create_table(
        "want_to_go",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── saved_venues ──────────────────────────────────────────────────
    op.create_table(
        "saved_venues",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── custom_lists ──────────────────────────────────────────────────
    op.create_table(
        "custom_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False, server_default=sa.text("'mixed'")),
        sa.Column("description", sa.Text),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── custom_list_items ─────────────────────────────────────────────
    op.create_table(
        "custom_list_items",
        sa.Column("list_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("custom_lists.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── scrape_jobs ───────────────────────────────────────────────────
    op.create_table(
        "scrape_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("items_found", sa.Integer, server_default=sa.text("0")),
        sa.Column("error", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("scrape_jobs")
    op.drop_table("custom_list_items")
    op.drop_table("custom_lists")
    op.drop_table("saved_venues")
    op.drop_table("want_to_go")
    op.drop_table("venue_summaries")
    op.drop_table("review_photos")
    op.drop_table("user_reviews")
    op.drop_table("users")
    op.drop_table("city_rankings")
    op.drop_table("reservation_links")
    op.drop_table("recommendations")
    op.drop_table("venues")
    op.execute("DROP TYPE IF EXISTS scrape_status")
    op.execute("DROP TYPE IF EXISTS list_entity_type")
    op.execute("DROP TYPE IF EXISTS verdict_type")
    op.execute("DROP TYPE IF EXISTS platform_type")
    op.execute("DROP TYPE IF EXISTS source_type")
    op.execute("DROP TYPE IF EXISTS entity_type")
