"""
Alarms router
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from database import Database

db: Database = None

router = APIRouter()


@router.get("")
async def get_alarms(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    card_serial: Optional[str] = Query(None, description="Filter by card serial"),
    start_time: Optional[datetime] = Query(None, description="Start time")
):
    """Get alarms with optional filters"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    alarms = await db.get_alarms(
        status=status,
        severity=severity,
        card_serial=card_serial,
        start_time=start_time
    )
    return {"alarms": alarms, "count": len(alarms)}


@router.post("/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: str):
    """Acknowledge an alarm"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    success = await db.acknowledge_alarm(alarm_id)
    if success:
        return {"status": "success", "message": f"Alarm {alarm_id} acknowledged"}
    else:
        raise HTTPException(status_code=404, detail="Alarm not found")


@router.post("/{alarm_id}/clear")
async def clear_alarm(alarm_id: str):
    """Clear an alarm"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    success = await db.clear_alarm(alarm_id)
    if success:
        return {"status": "success", "message": f"Alarm {alarm_id} cleared"}
    else:
        raise HTTPException(status_code=404, detail="Alarm not found")

