"""
Data Collector Service
Coleta dados da API Padtec NMS e armazena no TimescaleDB
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import pika
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from pythonjsonlogger import jsonlogger

from database import Database
from padtec_client import PadtecClient
from scheduler import CollectorScheduler

# Configure logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    handlers=[logHandler]
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings"""
    padtec_api_url: str
    padtec_api_token: str
    database_url: str
    rabbitmq_url: str
    collect_interval_critical: int = 30
    collect_interval_normal: int = 300
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
scheduler: Optional[AsyncIOScheduler] = None
db: Optional[Database] = None
padtec_client: Optional[PadtecClient] = None
rabbitmq_connection: Optional[pika.BlockingConnection] = None
collector_scheduler: Optional[CollectorScheduler] = None


async def _load_runtime_config() -> dict:
    """Load Padtec credentials and intervals from database (fallback to env)."""
    config = {
        "padtec_api_url": settings.padtec_api_url,
        "padtec_api_token": settings.padtec_api_token,
        "collect_interval_critical": settings.collect_interval_critical,
        "collect_interval_normal": settings.collect_interval_normal,
    }

    if not db:
        return config

    db_config = await db.get_system_config()
    if not db_config:
        return config

    config["padtec_api_url"] = db_config.get("PADTEC_API_URL", config["padtec_api_url"])
    config["padtec_api_token"] = db_config.get("PADTEC_API_TOKEN", config["padtec_api_token"])
    config["collect_interval_critical"] = int(
        db_config.get("COLLECT_INTERVAL_CRITICAL", config["collect_interval_critical"])
    )
    config["collect_interval_normal"] = int(
        db_config.get("COLLECT_INTERVAL_NORMAL", config["collect_interval_normal"])
    )

    return config


async def _reload_runtime_config() -> dict:
    """Reload configuration and apply to running services."""
    if not db or not padtec_client or not collector_scheduler:
        raise RuntimeError("Collector services not initialized")

    config = await _load_runtime_config()

    padtec_client.update_credentials(
        base_url=config.get("padtec_api_url"),
        token=config.get("padtec_api_token")
    )
    collector_scheduler.critical_interval = config.get("collect_interval_critical", settings.collect_interval_critical)
    collector_scheduler.normal_interval = config.get("collect_interval_normal", settings.collect_interval_normal)

    if scheduler:
        try:
            from apscheduler.triggers.interval import IntervalTrigger
            scheduler.reschedule_job(
                "collect_measurements_critical",
                trigger=IntervalTrigger(seconds=collector_scheduler.critical_interval)
            )
            scheduler.reschedule_job(
                "collect_measurements_normal",
                trigger=IntervalTrigger(seconds=collector_scheduler.normal_interval)
            )
        except Exception as exc:
            logger.warning(f"Failed to reschedule jobs with new intervals: {exc}")

    logger.info("Collector configuration reloaded")
    return config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global scheduler, db, padtec_client, rabbitmq_connection, collector_scheduler

    # Startup
    logger.info("Starting Data Collector Service")
    
    # Initialize database
    db = Database(settings.database_url)
    await db.initialize()
    logger.info("Database initialized")

    runtime_config = await _load_runtime_config()

    # Initialize Padtec client
    padtec_client = PadtecClient(
        base_url=runtime_config.get("padtec_api_url", settings.padtec_api_url),
        token=runtime_config.get("padtec_api_token", settings.padtec_api_token)
    )
    logger.info("Padtec client initialized")

    # Initialize RabbitMQ connection
    try:
        rabbitmq_params = pika.URLParameters(settings.rabbitmq_url)
        rabbitmq_connection = pika.BlockingConnection(rabbitmq_params)
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        rabbitmq_connection = None

    # Initialize scheduler
    collector_scheduler = CollectorScheduler(
        db=db,
        padtec_client=padtec_client,
        rabbitmq_connection=rabbitmq_connection,
        critical_interval=runtime_config.get("collect_interval_critical", settings.collect_interval_critical),
        normal_interval=runtime_config.get("collect_interval_normal", settings.collect_interval_normal)
    )
    
    scheduler = AsyncIOScheduler()
    await collector_scheduler.setup_jobs(scheduler)
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down Data Collector Service")
    if scheduler:
        scheduler.shutdown()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        rabbitmq_connection.close()
    if db:
        await db.close()


app = FastAPI(
    title="Padtec Data Collector",
    description="Service for collecting data from Padtec NMS API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "collector"
    }


@app.get("/status")
async def get_status():
    """Get collector status"""
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs
    }


@app.post("/collector/start")
async def start_collection():
    """Manually trigger collection"""
    global collector_scheduler
    if not padtec_client or not db or not collector_scheduler:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Trigger immediate collection
        await collector_scheduler.collect_all()
        return {"status": "success", "message": "Collection started"}
    except Exception as e:
        logger.error(f"Error starting collection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collector/sync-sites")
async def sync_sites():
    """Manually trigger sites (cards) synchronization"""
    global collector_scheduler
    if not padtec_client or not db or not collector_scheduler:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Trigger card collection (which updates sites)
        await collector_scheduler.collect_cards()
        return {"status": "success", "message": "Sites synchronization started"}
    except Exception as e:
        logger.error(f"Error syncing sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/reload")
async def reload_collector_config():
    """Reload configuration from system_config table."""
    if not db or not padtec_client:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        config = await _reload_runtime_config()
        return {
            "status": "success",
            "message": "Configuration reloaded",
            "config": config
        }
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/collector/restart")
async def restart_collector():
    """
    Compatibility endpoint used by backend.
    Performs a configuration reload instead of a full restart.
    """
    return await reload_collector_config()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

