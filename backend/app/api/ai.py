"""AI service API endpoints for completion, usage tracking, and connectivity testing."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, extract
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.ai_usage import AIUsageLog
from app.services.ai_service import AIService

router = APIRouter()


class CompleteRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 500
    endpoint: str = "api"


class CompleteResponse(BaseModel):
    response: str
    cached: bool
    provider: str
    model: Optional[str]
    estimate: dict


class EstimateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 500


class EstimateResponse(BaseModel):
    input_tokens_est: int
    output_tokens_est: int
    cost_est_usd: float
    provider: str
    model: Optional[str]


class UsageSummary(BaseModel):
    month: str
    total_requests: int
    cached_requests: int
    total_input_tokens_est: int
    total_output_tokens_est: int
    total_cost_est_usd: float


@router.post("/api/complete", response_model=CompleteResponse)
async def ai_complete(
    data: CompleteRequest,
    db: Session = Depends(get_db),
):
    """General purpose AI completion endpoint. Requires AI to be configured."""
    if not AIService.is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set up a provider in settings.",
        )

    cache_key = AIService._make_cache_key(data.prompt, data.system_prompt)
    cached = AIService._get_cached(cache_key) is not None

    try:
        response = await AIService.complete(
            prompt=data.prompt,
            system_prompt=data.system_prompt,
            max_tokens=data.max_tokens,
            db=db,
            endpoint=data.endpoint,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI completion failed: {e}")

    estimate = AIService.estimate_tokens(data.prompt, data.system_prompt, data.max_tokens)

    return CompleteResponse(
        response=response,
        cached=cached,
        provider=AIService.get_provider().value,
        model=AIService.get_model(),
        estimate=estimate,
    )


@router.get("/api/usage")
async def ai_usage(
    year: Optional[int] = Query(None, description="Year to query (defaults to current year)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month to query (defaults to current month)"),
    db: Session = Depends(get_db),
):
    """Monthly AI usage summary."""
    now = datetime.utcnow()
    query_year = year or now.year
    query_month = month or now.month

    rows = (
        db.query(
            sql_func.count(AIUsageLog.id).label("total_requests"),
            sql_func.sum(
                sql_func.cast(AIUsageLog.cached, type_=None)
            ).label("cached_requests"),
            sql_func.sum(AIUsageLog.input_tokens_est).label("total_input_tokens_est"),
            sql_func.sum(AIUsageLog.output_tokens_est).label("total_output_tokens_est"),
            sql_func.sum(AIUsageLog.cost_est_usd).label("total_cost_est_usd"),
        )
        .filter(
            extract("year", AIUsageLog.created_at) == query_year,
            extract("month", AIUsageLog.created_at) == query_month,
        )
        .first()
    )

    return UsageSummary(
        month=f"{query_year}-{query_month:02d}",
        total_requests=rows.total_requests or 0,
        cached_requests=int(rows.cached_requests or 0),
        total_input_tokens_est=int(rows.total_input_tokens_est or 0),
        total_output_tokens_est=int(rows.total_output_tokens_est or 0),
        total_cost_est_usd=round(float(rows.total_cost_est_usd or 0), 8),
    )


@router.post("/api/test")
async def ai_test():
    """Test AI provider connectivity by sending a simple prompt."""
    if not AIService.is_configured():
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set up a provider in settings.",
        )

    try:
        response = await AIService.complete(
            prompt="Respond with exactly: OK",
            max_tokens=10,
            endpoint="connectivity_test",
        )
        return {
            "status": "ok",
            "provider": AIService.get_provider().value,
            "model": AIService.get_model(),
            "response": response.strip(),
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": AIService.get_provider().value,
            "model": AIService.get_model(),
            "error": str(e),
        }


@router.get("/api/estimate", response_model=EstimateResponse)
async def ai_estimate(
    prompt: str = Query(..., description="The prompt text to estimate"),
    system_prompt: Optional[str] = Query(None, description="Optional system prompt"),
    max_tokens: int = Query(500, description="Max output tokens"),
):
    """Estimate tokens and cost for a prompt without running the completion."""
    estimate = AIService.estimate_tokens(prompt, system_prompt, max_tokens)

    return EstimateResponse(
        input_tokens_est=estimate["input_tokens_est"],
        output_tokens_est=estimate["output_tokens_est"],
        cost_est_usd=estimate["cost_est_usd"],
        provider=AIService.get_provider().value,
        model=AIService.get_model(),
    )
