from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.models import ManualCargo, User
from app.schemas import ManualCargoIn
from app.authentication.dependencies import current_user

router = APIRouter(prefix="/cargo", tags=["cargo"])

def serialize(row: ManualCargo) -> dict:
    return {"id": row.id, "title": row.title, "category": row.category, "weight_kg": row.weight_kg,
            "rate_inr": row.rate_inr, "pickup": row.pickup, "drop": row.drop,
            "pickup_window_start": row.pickup_window_start, "pickup_window_end": row.pickup_window_end,
            "loading_minutes": row.loading_minutes, "unloading_minutes": row.unloading_minutes, "waiting_minutes": row.waiting_minutes, "hazardous": row.hazardous, "hazardous_details": row.hazardous_details,
            "created_at": row.created_at.isoformat()}

@router.get("/manual")
async def list_manual(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(ManualCargo).where(ManualCargo.owner_id == user.id).order_by(ManualCargo.created_at.desc()))).all()
    return [serialize(row) for row in rows]

@router.post("/manual", status_code=201)
async def create_manual(payload: ManualCargoIn, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = ManualCargo(owner_id=user.id, title=payload.title.strip(), category=payload.category.strip(),
                      weight_kg=payload.weight_kg, rate_inr=payload.rate_inr,
                      pickup=payload.pickup.model_dump(), drop=payload.drop.model_dump(),
                      pickup_window_start=payload.pickup_window_start, pickup_window_end=payload.pickup_window_end,
                      loading_minutes=payload.loading_minutes, unloading_minutes=payload.unloading_minutes, waiting_minutes=payload.waiting_minutes, hazardous=payload.hazardous, hazardous_details={"description": payload.hazardous_description} if payload.hazardous else None)
    db.add(row); await db.commit(); await db.refresh(row)
    return serialize(row)

@router.delete("/manual/{cargo_id}", status_code=204)
async def delete_manual(cargo_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    row = await db.scalar(select(ManualCargo).where(ManualCargo.id == cargo_id, ManualCargo.owner_id == user.id))
    if not row: raise HTTPException(404, "Cargo listing not found.")
    await db.delete(row); await db.commit()
    return Response(status_code=204)
