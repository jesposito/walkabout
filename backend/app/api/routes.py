from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Route
from app.schemas import RouteCreate, RouteResponse, RouteUpdate

router = APIRouter()


@router.get("", response_model=List[RouteResponse])
async def list_routes(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    query = db.query(Route)
    if active_only:
        query = query.filter(Route.is_active == True)
    return query.all()


@router.post("", response_model=RouteResponse)
async def create_route(
    route: RouteCreate,
    db: Session = Depends(get_db)
):
    if not route.name:
        route.name = f"{route.origin} to {route.destination}"
    
    db_route = Route(**route.model_dump())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route


@router.get("/{route_id}", response_model=RouteResponse)
async def get_route(
    route_id: int,
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    return route


@router.put("/{route_id}", response_model=RouteResponse)
async def update_route(
    route_id: int,
    route_update: RouteUpdate,
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    update_data = route_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)
    
    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}")
async def delete_route(
    route_id: int,
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    db.delete(route)
    db.commit()
    return {"status": "deleted", "id": route_id}
