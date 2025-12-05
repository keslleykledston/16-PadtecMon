"""
Configuration router
"""
from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx
import os
import logging
from database import Database

logger = logging.getLogger(__name__)

db: Database = None

router = APIRouter()

COLLECTOR_URL = os.getenv("COLLECTOR_URL", "http://collector:8001")


def _normalize_url(url: str) -> str:
    """Ensure URL has no trailing slash."""
    return url.rstrip("/")


def _build_test_urls(base_url: str) -> list[str]:
    """
    Generate possible endpoints for testing connectivity.

    Handles both Smart API (/api/v1) and legacy (/nms-api) patterns.
    """
    base = _normalize_url(base_url)

    candidates = [
        f"{base}/api/v1/inventory/state",
        f"{base}/inventory/state",
        f"{base}/api/v1/measures/state",
        f"{base}/cards",
        base,
    ]

    # Remove duplicates while preserving order
    seen = set()
    ordered = []
    for url in candidates:
        if url not in seen:
            ordered.append(url)
            seen.add(url)
    return ordered


async def _notify_collector_reload() -> None:
    """Ask collector service to reload configuration."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{COLLECTOR_URL}/config/reload")
    except Exception as exc:
        logger.warning("Unable to notify collector to reload config: %s", exc)


class ConfigUpdate(BaseModel):
    padtecApiUrl: str
    padtecApiToken: Optional[str] = None
    collectIntervalCritical: int
    collectIntervalNormal: int


class TestConnectionRequest(BaseModel):
    padtecApiUrl: str
    padtecApiToken: Optional[str] = None


@router.get("")
async def get_config():
    """Get current configuration"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        async with db.SessionLocal() as session:
            from sqlalchemy import text
            
            query = text("""
                SELECT config_key, config_value
                FROM system_config
                WHERE config_key IN ('PADTEC_API_URL', 'PADTEC_API_TOKEN', 'COLLECT_INTERVAL_CRITICAL', 'COLLECT_INTERVAL_NORMAL')
            """)
            result = await session.execute(query)
            rows = result.fetchall()
            
            # Build config dict
            config_dict = {}
            for row in rows:
                config_dict[row[0]] = row[1]
            
            # Return with defaults if not found
            config = {
                "padtecApiUrl": config_dict.get("PADTEC_API_URL", os.getenv("PADTEC_API_URL", "http://172.30.0.21:8181/nms-api/")),
                "padtecApiToken": config_dict.get("PADTEC_API_TOKEN", os.getenv("PADTEC_API_TOKEN", "")),
                "collectIntervalCritical": int(config_dict.get("COLLECT_INTERVAL_CRITICAL", os.getenv("COLLECT_INTERVAL_CRITICAL", "30"))),
                "collectIntervalNormal": int(config_dict.get("COLLECT_INTERVAL_NORMAL", os.getenv("COLLECT_INTERVAL_NORMAL", "300")))
            }
            
            return config
    except Exception as e:
        # Fallback to environment variables
        return {
            "padtecApiUrl": os.getenv("PADTEC_API_URL", "http://172.30.0.21:8181/nms-api/"),
            "padtecApiToken": os.getenv("PADTEC_API_TOKEN", ""),
            "collectIntervalCritical": int(os.getenv("COLLECT_INTERVAL_CRITICAL", "30")),
            "collectIntervalNormal": int(os.getenv("COLLECT_INTERVAL_NORMAL", "300"))
        }


@router.put("")
async def update_config(config: ConfigUpdate):
    """Update configuration"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    # Validate
    if not config.padtecApiUrl or not config.padtecApiUrl.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL da API inválida")
    
    if config.collectIntervalCritical < 10 or config.collectIntervalCritical > 300:
        raise HTTPException(status_code=400, detail="Intervalo crítico deve estar entre 10 e 300 segundos")
    
    if config.collectIntervalNormal < 60 or config.collectIntervalNormal > 3600:
        raise HTTPException(status_code=400, detail="Intervalo normal deve estar entre 60 e 3600 segundos")
    
    try:
        async with db.SessionLocal() as session:
            from sqlalchemy import text
            
            normalized_url = _normalize_url(config.padtecApiUrl)
            
            # Update or insert configuration
            updates = [
                ("PADTEC_API_URL", normalized_url),
                ("PADTEC_API_TOKEN", config.padtecApiToken or ""),
                ("COLLECT_INTERVAL_CRITICAL", str(config.collectIntervalCritical)),
                ("COLLECT_INTERVAL_NORMAL", str(config.collectIntervalNormal))
            ]
            
            for key, value in updates:
                query = text("""
                    INSERT INTO system_config (config_key, config_value, updated_at)
                    VALUES (:key, :value, NOW())
                    ON CONFLICT (config_key) DO UPDATE SET
                        config_value = EXCLUDED.config_value,
                        updated_at = NOW()
                """)
                await session.execute(query, {"key": key, "value": value})
            
            await session.commit()
            
            # Notify collector to reload configuration (best effort)
            await _notify_collector_reload()
            
            return {
                "status": "success",
                "message": "Configurações salvas e enviadas ao coletor.",
                "config": {
                    "padtecApiUrl": normalized_url,
                    "padtecApiToken": config.padtecApiToken or "",
                    "collectIntervalCritical": config.collectIntervalCritical,
                    "collectIntervalNormal": config.collectIntervalNormal
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configurações: {str(e)}")


async def _check_padtec_connection(url: str, token: str) -> dict:
    """Helper function to test Padtec API connection"""
    try:
        if not token:
            return {
                "connected": False,
                "message": "Token não fornecido"
            }
        
        # Try to connect to the API with CSRF token handling
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        test_urls = _build_test_urls(url)
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Try multiple endpoints (Smart API documented endpoints first)
            response = None
            last_error = None
            
            for test_url in test_urls:
                try:
                    response = await client.get(test_url, headers=headers)
                    if response.status_code in [200, 401, 403]:  # Got a meaningful response
                        break  # Success or clear error, exit loop
                except httpx.HTTPStatusError as e:
                    response = e.response
                    if response.status_code in [200, 401, 403]:
                        break
                    last_error = e
                except Exception as e:
                    last_error = e
                    continue  # Try next URL
            
            if response is None:
                if last_error:
                    raise last_error
                raise Exception("Nenhum endpoint respondeu")
            
            # Check response
            response_text = response.text.lower()
            
            if response.status_code == 200:
                return {
                    "connected": True,
                    "message": "Conexão bem-sucedida com a API Padtec",
                    "statusCode": response.status_code
                }
            elif response.status_code == 401:
                return {
                    "connected": False,
                    "message": "Token inválido ou expirado. Verifique o token de autenticação.",
                    "statusCode": response.status_code
                }
            elif response.status_code == 403:
                # Check if it's CSRF related
                if "csrf" in response_text:
                    # Try to get CSRF token from a GET request first
                    try:
                        # Some APIs require a GET to / first to get CSRF token
                        csrf_response = await client.get(f"{url}/", headers=headers)
                        csrf_token = None
                        
                        # Try to extract CSRF token from cookies or headers
                        for cookie in client.cookies:
                            if 'csrf' in cookie.name.lower():
                                csrf_token = cookie.value
                                break
                        
                        # Or from response headers
                        if not csrf_token:
                            csrf_token = csrf_response.headers.get('X-CSRF-Token') or \
                                        csrf_response.headers.get('CSRF-Token')
                        
                        if csrf_token:
                            headers['X-CSRF-Token'] = csrf_token
                            headers['X-Requested-With'] = 'XMLHttpRequest'
                            # Retry with CSRF token
                            response = await client.get(test_url, headers=headers)
                            if response.status_code == 200:
                                return {
                                    "connected": True,
                                    "message": "Conexão bem-sucedida com a API Padtec (com CSRF token)",
                                    "statusCode": response.status_code
                                }
                    except:
                        pass
                    
                    return {
                        "connected": False,
                        "message": "Erro CSRF: A API requer token CSRF. Verifique se a URL está correta e se o token é válido.",
                        "statusCode": response.status_code
                    }
                else:
                    return {
                        "connected": False,
                        "message": "Acesso negado (403). Verifique as permissões do token.",
                        "statusCode": response.status_code
                    }
            elif response.status_code == 404:
                return {
                    "connected": False,
                    "message": "Endpoint não encontrado. Verifique a URL da API. Smart API usa /api/v1/ (ex: http://ip:port/api/v1/)",
                    "statusCode": response.status_code
                }
            else:
                # Try to parse error message
                error_msg = f"Erro na API: Status {response.status_code}"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict) and "message" in error_data:
                        error_msg = error_data["message"]
                    elif isinstance(error_data, dict) and "error" in error_data:
                        error_msg = error_data["error"]
                except:
                    if response.text:
                        error_msg = response.text[:200]
                
                return {
                    "connected": False,
                    "message": error_msg,
                    "statusCode": response.status_code
                }
    except httpx.ConnectError as e:
        return {
            "connected": False,
            "message": f"Não foi possível conectar à API. Verifique a URL ({url}) e a conectividade de rede. Erro: {str(e)}"
        }
    except httpx.TimeoutException:
        return {
            "connected": False,
            "message": "Timeout ao conectar à API (15s). A API pode estar indisponível ou a rede está lenta."
        }
    except Exception as e:
        error_msg = str(e)
        if "CSRF" in error_msg or "csrf" in error_msg.lower():
            return {
                "connected": False,
                "message": f"Erro CSRF: {error_msg}. A API pode requerer autenticação adicional."
            }
        return {
            "connected": False,
            "message": f"Erro ao testar conexão: {error_msg}"
        }


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """Test connection to Padtec API using provided credentials"""
    return await _check_padtec_connection(
        request.padtecApiUrl.rstrip('/'),
        request.padtecApiToken
    )


@router.get("/padtec-status")
async def get_padtec_status():
    """Get connection status using saved configuration"""
    config = await get_config()
    return await _check_padtec_connection(
        config["padtecApiUrl"].rstrip('/'),
        config["padtecApiToken"]
    )

