"""
Alert rules router
"""
from fastapi import APIRouter, HTTPException
from database import Database

db: Database = None

router = APIRouter()


@router.get("")
async def get_rules():
    """Get all alert rules"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    rules = await db.get_alert_rules()
    return {"rules": rules, "count": len(rules)}

