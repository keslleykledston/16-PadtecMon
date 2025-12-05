"""
Cards router
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from database import Database

db: Database = None

router = APIRouter()


@router.get("")
async def get_cards(
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    family: Optional[str] = Query(None, description="Filter by card family"),
    model: Optional[str] = Query(None, description="Filter by card model")
):
    """Get cards with optional filters"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    cards = await db.get_cards(site_id=site_id, family=family, model=model)
    return {"cards": cards, "count": len(cards)}


@router.get("/{card_serial}")
async def get_card(card_serial: str):
    """Get a single card by serial"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    card = await db.get_card(card_serial)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    return card


@router.get("/{card_serial}/measurements")
async def get_card_measurements(
    card_serial: str,
    measure_key: Optional[str] = Query(None, description="Filter by measure key")
):
    """Get measurements for a specific card"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    from datetime import datetime, timedelta
    
    # Get last 24 hours by default
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    history = await db.get_measurement_history(
        card_serial=card_serial,
        measure_key=measure_key,
        start_time=start_time,
        end_time=end_time,
        interval=None  # Raw data
    )
    
    return {"measurements": history, "count": len(history)}

