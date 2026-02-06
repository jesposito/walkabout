"""Award flight tracking models for Seats.aero integration."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Float, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AwardProgram(str, enum.Enum):
    """Supported loyalty/mileage programs.

    Values must match Seats.aero 'Source' identifiers used in the /search endpoint.
    See: https://developers.seats.aero
    """
    AEROPLAN = "aeroplan"
    ALASKA = "alaska"
    AMERICAN = "american"
    ASIA_MILES = "asiamiles"
    CONNECT_MILES = "connectmiles"
    DELTA = "delta"
    EMIRATES = "emirates"
    ETIHAD = "etihad"
    EUROBONUS = "eurobonus"
    FLYING_BLUE = "flyingblue"
    JETBLUE = "jetblue"
    LIFE_MILES = "lifemiles"
    QANTAS = "qantas"
    QATAR = "qatar"
    SAUDIA = "saudia"
    SINGAPORE = "singapore"
    SMILES = "smiles"
    TURKISH = "turkish"
    UNITED = "united"
    VELOCITY = "velocity"
    VIRGIN_ATLANTIC = "virginatlantic"
    AEROMEXICO = "aeromexico"


class TrackedAwardSearch(Base):
    """
    A saved award search to poll periodically via Seats.aero.

    Similar to SearchDefinition but for award flights.
    Users configure these to get alerts when award seats become available.
    """
    __tablename__ = "tracked_award_searches"

    id = Column(Integer, primary_key=True, index=True)

    # Route
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)

    # Program filter (null = all programs)
    program = Column(String(30), nullable=True)

    # Date range to search
    date_start = Column(DateTime, nullable=True)
    date_end = Column(DateTime, nullable=True)

    # Cabin preference
    cabin_class = Column(String(20), default="business")  # economy, premium_economy, business, first

    # Family filter: minimum seats needed in same cabin
    min_seats = Column(Integer, default=1)

    # Whether to only show direct flights
    direct_only = Column(Boolean, default=False)

    # Active / notification settings
    is_active = Column(Boolean, default=True)
    notify_on_change = Column(Boolean, default=True)

    # Polling
    last_polled_at = Column(DateTime, nullable=True)
    last_hash = Column(String(64), nullable=True)  # Hash of last result for change detection

    # Metadata
    name = Column(String(128), nullable=True)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    observations = relationship(
        "AwardObservation",
        back_populates="search",
        cascade="all, delete-orphan",
        order_by="desc(AwardObservation.observed_at)",
    )


class AwardObservation(Base):
    """
    A snapshot of award availability at a point in time.

    Stores the raw API response payload plus extracted key fields
    for efficient querying without deserializing JSON.
    """
    __tablename__ = "award_observations"

    id = Column(Integer, primary_key=True, index=True)

    search_id = Column(
        Integer,
        ForeignKey("tracked_award_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When this observation was recorded
    observed_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Change detection
    payload_hash = Column(String(64), nullable=False)  # SHA256 of normalized results
    is_changed = Column(Boolean, default=False)  # True if different from previous observation

    # Extracted summary fields for quick access
    programs_with_availability = Column(JSON, default=list)  # e.g., ["united", "aeroplan"]
    best_economy_miles = Column(Integer, nullable=True)
    best_business_miles = Column(Integer, nullable=True)
    best_first_miles = Column(Integer, nullable=True)
    total_options = Column(Integer, default=0)
    max_seats_available = Column(Integer, default=0)

    # Raw API response (for detailed inspection)
    raw_results = Column(JSON, nullable=True)

    # Relationships
    search = relationship("TrackedAwardSearch", back_populates="observations")

    __table_args__ = (
        Index("ix_award_obs_search_time", "search_id", "observed_at"),
    )
