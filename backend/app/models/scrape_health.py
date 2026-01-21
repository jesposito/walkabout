from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class ScrapeHealth(Base):
    """
    First-class scrape health tracking per search definition.
    
    Oracle Review: "Scraping is single point of failure. Missing first-class scrape health model."
    
    Key features:
    - Track success/failure metrics per search definition
    - Store failure reason classification
    - Track last-good-data timestamp for stale data alerts
    - Store screenshot + HTML snapshot paths on failure for debugging
    """
    __tablename__ = "scrape_health"
    
    id = Column(Integer, primary_key=True, index=True)
    search_definition_id = Column(
        Integer, 
        ForeignKey("search_definitions.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True,
        index=True
    )
    
    # Success/failure tracking
    total_attempts = Column(Integer, default=0, nullable=False)
    total_successes = Column(Integer, default=0, nullable=False)
    total_failures = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    
    # Last failure details
    last_failure_reason = Column(String(50), nullable=True)  # captcha, timeout, layout_change, no_results, blocked, unknown
    last_failure_message = Column(Text, nullable=True)
    last_screenshot_path = Column(String(500), nullable=True)  # Path to failure screenshot
    last_html_snapshot_path = Column(String(500), nullable=True)  # Path to HTML snapshot
    
    # Stale data tracking
    stale_alert_sent_at = Column(DateTime(timezone=True), nullable=True)  # When we last alerted about stale data
    
    # Circuit breaker state
    circuit_open = Column(Integer, default=0, nullable=False)  # 0=closed, 1=open (paused scraping)
    circuit_opened_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    search_definition = relationship("SearchDefinition", back_populates="scrape_health")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.total_successes / self.total_attempts) * 100
    
    @property
    def is_healthy(self) -> bool:
        """
        Healthy if:
        - Circuit is closed
        - Less than 3 consecutive failures
        - Success rate > 50% (if enough attempts)
        """
        if self.circuit_open:
            return False
        if self.consecutive_failures >= 3:
            return False
        if self.total_attempts >= 10 and self.success_rate < 50:
            return False
        return True
    
    def record_success(self) -> None:
        """Call after a successful scrape."""
        self.total_attempts += 1
        self.total_successes += 1
        self.consecutive_failures = 0
        self.last_attempt_at = func.now()
        self.last_success_at = func.now()
        
        # Close circuit on success
        if self.circuit_open:
            self.circuit_open = 0
            self.circuit_opened_at = None
    
    def record_failure(
        self,
        reason: str,
        message: str | None = None,
        screenshot_path: str | None = None,
        html_snapshot_path: str | None = None
    ) -> None:
        """Call after a failed scrape."""
        self.total_attempts += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_attempt_at = func.now()
        self.last_failure_at = func.now()
        self.last_failure_reason = reason
        self.last_failure_message = message
        self.last_screenshot_path = screenshot_path
        self.last_html_snapshot_path = html_snapshot_path
        
        # Open circuit after 5 consecutive failures
        if self.consecutive_failures >= 5 and not self.circuit_open:
            self.circuit_open = 1
            self.circuit_opened_at = func.now()
    
    def __repr__(self) -> str:
        status = "healthy" if self.is_healthy else "unhealthy"
        return f"<ScrapeHealth {self.search_definition_id}: {status}, {self.success_rate:.0f}% success>"
