"""
Measurements router
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from database import Database

db: Database = None

router = APIRouter()


@router.get("/latest")
async def get_latest_measurements(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get latest measurements"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    measurements = await db.get_latest_measurements(limit=limit, offset=offset)
    return {"measurements": measurements, "count": len(measurements)}


@router.get("/history")
async def get_measurement_history(
    card_serial: str = Query(..., description="Card serial number"),
    measure_key: Optional[str] = Query(None, description="Measure key"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    interval: str = Query("1 hour", description="Time interval for aggregation")
):
    """Get measurement history"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    history = await db.get_measurement_history(
        card_serial=card_serial,
        measure_key=measure_key,
        start_time=start_time,
        end_time=end_time,
        interval=interval
    )
    
    return {"history": history, "count": len(history)}

