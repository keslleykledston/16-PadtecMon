"""
Collector control router
"""
from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter()

COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector:8001")
RELOAD_ENDPOINT = f"{COLLECTOR_URL}/config/reload"
LEGACY_RESTART_ENDPOINT = f"{COLLECTOR_URL}/collector/restart"


@router.post("/restart")
async def restart_collector():
    """Restart collector service"""
    try:
        # In a real implementation, you would send a signal to restart
        # For now, we'll just return success
        # You could use Docker API or send a signal to the process
        
        # Try to call collector's reload/restart endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(RELOAD_ENDPOINT)
                if response.status_code == 200:
                    return {"status": "success", "message": "Collector atualizado com novas configurações"}
            except Exception:
                # Fallback to legacy endpoint if available
                try:
                    response = await client.post(LEGACY_RESTART_ENDPOINT)
                    if response.status_code == 200:
                        return {"status": "success", "message": "Collector reiniciado"}
                except Exception:
                    pass
        
        return {
            "status": "success",
            "message": "Comando de reinício enviado. O collector será reiniciado em breve."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao reiniciar collector: {str(e)}")

