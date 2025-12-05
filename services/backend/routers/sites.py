"""
Sites router
"""
from fastapi import APIRouter, HTTPException
from database import Database

router = APIRouter()

# This will be set by main.py
db: Database = None


@router.get("")
async def get_sites():
    """Get all sites"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    sites = await db.get_sites()
    return {"sites": sites, "count": len(sites)}


@router.post("/sync")
async def sync_sites():
    """Trigger sites synchronization via collector"""
    import os
    import httpx
    
    COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector:8001")
    SYNC_ENDPOINT = f"{COLLECTOR_URL}/collector/sync-sites"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(SYNC_ENDPOINT)
            
            if response.status_code == 200:
                # After sync, fetch updated sites
                if db:
                    sites = await db.get_sites()
                    return {
                        "status": "success", 
                        "message": "Sites synchronized successfully",
                        "sites": sites,
                        "count": len(sites)
                    }
                return {"status": "success", "message": "Sites synchronized successfully"}
            else:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Collector error: {response.text}"
                )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Collector unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing sites: {str(e)}")

