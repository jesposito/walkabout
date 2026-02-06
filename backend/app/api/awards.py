"""Award flight tracking API endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.award import TrackedAwardSearch, AwardObservation
from app.services.award_poller import AwardPoller

router = APIRouter()


class AwardSearchCreate(BaseModel):
    name: Optional[str] = None
    origin: str
    destination: str
    program: Optional[str] = None
    date_start: Optional[datetime] = None
    date_end: Optional[datetime] = None
    cabin_class: str = "business"
    min_seats: int = 1
    direct_only: bool = False
    notify_on_change: bool = True
    notes: Optional[str] = None


class AwardSearchResponse(BaseModel):
    id: int
    name: Optional[str]
    origin: str
    destination: str
    program: Optional[str]
    date_start: Optional[datetime]
    date_end: Optional[datetime]
    cabin_class: str
    min_seats: int
    direct_only: bool
    is_active: bool
    notify_on_change: bool
    last_polled_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ObservationResponse(BaseModel):
    id: int
    search_id: int
    observed_at: datetime
    is_changed: bool
    programs_with_availability: list
    best_economy_miles: Optional[int]
    best_business_miles: Optional[int]
    best_first_miles: Optional[int]
    total_options: int
    max_seats_available: int

    class Config:
        from_attributes = True


@router.get("/api/awards")
async def list_award_searches(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(TrackedAwardSearch).order_by(TrackedAwardSearch.created_at.desc())
    if active_only:
        query = query.filter(TrackedAwardSearch.is_active == True)
    searches = query.all()
    return [AwardSearchResponse.model_validate(s) for s in searches]


@router.post("/api/awards")
async def create_award_search(
    data: AwardSearchCreate,
    db: Session = Depends(get_db),
):
    search = TrackedAwardSearch(
        name=data.name or f"{data.origin}-{data.destination} {data.cabin_class}",
        origin=data.origin.upper(),
        destination=data.destination.upper(),
        program=data.program,
        date_start=data.date_start,
        date_end=data.date_end,
        cabin_class=data.cabin_class,
        min_seats=data.min_seats,
        direct_only=data.direct_only,
        notify_on_change=data.notify_on_change,
        notes=data.notes,
    )
    db.add(search)
    db.commit()
    db.refresh(search)
    return AwardSearchResponse.model_validate(search)


@router.get("/api/awards/{search_id}")
async def get_award_search(search_id: int, db: Session = Depends(get_db)):
    search = db.query(TrackedAwardSearch).filter(TrackedAwardSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Award search not found")
    return AwardSearchResponse.model_validate(search)


@router.delete("/api/awards/{search_id}")
async def delete_award_search(search_id: int, db: Session = Depends(get_db)):
    search = db.query(TrackedAwardSearch).filter(TrackedAwardSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Award search not found")
    db.delete(search)
    db.commit()
    return {"deleted": True}


@router.put("/api/awards/{search_id}/toggle")
async def toggle_award_search(search_id: int, db: Session = Depends(get_db)):
    search = db.query(TrackedAwardSearch).filter(TrackedAwardSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Award search not found")
    search.is_active = not search.is_active
    db.commit()
    return {"is_active": search.is_active}


@router.post("/api/awards/{search_id}/poll")
async def poll_award_search(search_id: int, db: Session = Depends(get_db)):
    """Manually trigger a poll for a specific award search."""
    poller = AwardPoller(db)
    observation = await poller.poll_single(search_id)
    if observation is None:
        return {"status": "error", "message": "Failed to poll. Check API key configuration."}
    return {
        "status": "success",
        "changed": observation.is_changed,
        "total_options": observation.total_options,
        "max_seats": observation.max_seats_available,
    }


@router.get("/api/awards/{search_id}/observations")
async def get_observations(
    search_id: int,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    search = db.query(TrackedAwardSearch).filter(TrackedAwardSearch.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Award search not found")

    observations = db.query(AwardObservation).filter(
        AwardObservation.search_id == search_id
    ).order_by(AwardObservation.observed_at.desc()).limit(limit).all()

    return {
        "search": AwardSearchResponse.model_validate(search),
        "observations": [ObservationResponse.model_validate(o) for o in observations],
    }


@router.get("/api/awards/{search_id}/latest")
async def get_latest_observation(search_id: int, db: Session = Depends(get_db)):
    """Get the most recent observation with full results."""
    obs = db.query(AwardObservation).filter(
        AwardObservation.search_id == search_id
    ).order_by(AwardObservation.observed_at.desc()).first()

    if not obs:
        return {"observation": None, "results": []}

    return {
        "observation": ObservationResponse.model_validate(obs),
        "results": obs.raw_results or [],
    }
