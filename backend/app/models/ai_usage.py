"""AI usage tracking model for logging completion requests and costs."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.sql import func
from app.database import Base


class AIUsageLog(Base):
    """Tracks each AI completion request for usage monitoring and cost estimation."""
    __tablename__ = "ai_usage_log"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    endpoint = Column(String(100), nullable=False)  # which feature triggered it
    provider = Column(String(30), nullable=False)  # which AI provider was used
    model = Column(String(50), nullable=False)  # which model
    input_tokens_est = Column(Integer, nullable=False, default=0)
    output_tokens_est = Column(Integer, nullable=False, default=0)
    cost_est_usd = Column(Float, nullable=False, default=0.0)
    cached = Column(Boolean, nullable=False, default=False)
    prompt_hash = Column(String(64), nullable=False, index=True)  # for cache key reference
