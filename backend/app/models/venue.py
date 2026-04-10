import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ── Enums ────────────────────────────────────────────────────────────
EntityType = Enum("restaurant", "hotel", name="entity_type", create_constraint=True)
SourceType = Enum(
    "reddit", "infatuation", "eater", "beli", "michelin", "google", "conde_nast",
    name="source_type", create_constraint=True,
)
PlatformType = Enum(
    "resy", "opentable", "sevenrooms", "tock", "yelp_reservations",
    "booking_com", "hotels_com", "expedia", "hotel_direct",
    name="platform_type", create_constraint=True,
)


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(EntityType, nullable=False, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    country: Mapped[str | None] = mapped_column(String(255))
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    price_level: Mapped[int | None] = mapped_column(Integer)
    google_place_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)

    # Restaurant-specific
    cuisine_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Hotel-specific
    star_rating: Mapped[int | None] = mapped_column(Integer)
    room_count: Mapped[int | None] = mapped_column(Integer)
    hotel_brand: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    reservation_links: Mapped[list["ReservationLink"]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    rankings: Mapped[list["CityRanking"]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    summary: Mapped["VenueSummary | None"] = relationship(back_populates="venue", uselist=False, cascade="all, delete-orphan")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(SourceType, nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    snippet: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(Float)
    awards: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    venue: Mapped["Venue"] = relationship(back_populates="recommendations")


class ReservationLink(Base):
    __tablename__ = "reservation_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(PlatformType, nullable=False)
    booking_url: Mapped[str] = mapped_column(Text, nullable=False)
    venue_id_ext: Mapped[str | None] = mapped_column(String(255))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    venue: Mapped["Venue"] = relationship(back_populates="reservation_links")


class CityRanking(Base):
    __tablename__ = "city_rankings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(EntityType, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    source_scores: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    venue: Mapped["Venue"] = relationship(back_populates="rankings")


class VenueSummary(Base):
    __tablename__ = "venue_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    venue_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    highlights: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    sentiment_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    photo_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    venue: Mapped["Venue"] = relationship(back_populates="summary")
