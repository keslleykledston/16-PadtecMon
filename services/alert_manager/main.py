"""
Alert Manager Service
Monitora medições e gera alertas baseados em regras configuráveis
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import pika
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from pythonjsonlogger import jsonlogger

from database import Database
from alert_processor import AlertProcessor
from rabbitmq_consumer import RabbitMQConsumer

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
    database_url: str
    rabbitmq_url: str
    check_interval: int = 60
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
scheduler: Optional[AsyncIOScheduler] = None
db: Optional[Database] = None
alert_processor: Optional[AlertProcessor] = None
rabbitmq_connection: Optional[pika.BlockingConnection] = None
consumer: Optional[RabbitMQConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global scheduler, db, alert_processor, rabbitmq_connection, consumer

    # Startup
    logger.info("Starting Alert Manager Service")
    
    # Initialize database
    db = Database(settings.database_url)
    await db.initialize()
    logger.info("Database initialized")

    # Initialize RabbitMQ connection
    try:
        rabbitmq_params = pika.URLParameters(settings.rabbitmq_url)
        rabbitmq_connection = pika.BlockingConnection(rabbitmq_params)
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        rabbitmq_connection = None

    # Initialize alert processor
    alert_processor = AlertProcessor(db, rabbitmq_connection)
    
    # Initialize RabbitMQ consumer
    if rabbitmq_connection:
        consumer = RabbitMQConsumer(
            connection=rabbitmq_connection,
            alert_processor=alert_processor
        )
        consumer.start_consuming()
        logger.info("RabbitMQ consumer started")

    # Initialize scheduler for periodic checks
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        alert_processor.check_all_rules,
        'interval',
        seconds=settings.check_interval,
        id='check_alerts',
        name='Check Alert Rules',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down Alert Manager Service")
    if consumer:
        consumer.stop_consuming()
    if scheduler:
        scheduler.shutdown()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        rabbitmq_connection.close()
    if db:
        await db.close()


app = FastAPI(
    title="Padtec Alert Manager",
    description="Service for processing alerts and rules",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "alert_manager"
    }


@app.get("/alerts/active")
async def get_active_alerts():
    """Get active alerts"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        alerts = await db.get_active_alerts()
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alarm_id}/acknowledge")
async def acknowledge_alert(alarm_id: str):
    """Acknowledge an alert"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        success = await db.acknowledge_alarm(alarm_id)
        if success:
            return {"status": "success", "message": f"Alert {alarm_id} acknowledged"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alarm_id}/clear")
async def clear_alert(alarm_id: str):
    """Clear an alert"""
    if not db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    try:
        success = await db.clear_alarm(alarm_id)
        if success:
            return {"status": "success", "message": f"Alert {alarm_id} cleared"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except Exception as e:
        logger.error(f"Error clearing alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)




