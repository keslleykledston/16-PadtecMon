"""
Notification Service
Envia notificações por múltiplos canais (Email, Telegram, SMS, Webhook)
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import pika
from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from pythonjsonlogger import jsonlogger

from notification_handler import NotificationHandler
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
    rabbitmq_url: str
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
rabbitmq_connection: Optional[pika.BlockingConnection] = None
notification_handler: Optional[NotificationHandler] = None
consumer: Optional[RabbitMQConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global rabbitmq_connection, notification_handler, consumer

    # Startup
    logger.info("Starting Notification Service")
    
    # Initialize RabbitMQ connection
    try:
        rabbitmq_params = pika.URLParameters(settings.rabbitmq_url)
        rabbitmq_connection = pika.BlockingConnection(rabbitmq_params)
        logger.info("RabbitMQ connection established")
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        rabbitmq_connection = None

    # Initialize notification handler
    notification_handler = NotificationHandler(settings)
    
    # Initialize RabbitMQ consumer
    if rabbitmq_connection:
        consumer = RabbitMQConsumer(
            connection=rabbitmq_connection,
            notification_handler=notification_handler
        )
        consumer.start_consuming()
        logger.info("RabbitMQ consumer started")

    yield

    # Shutdown
    logger.info("Shutting down Notification Service")
    if consumer:
        consumer.stop_consuming()
    if rabbitmq_connection and not rabbitmq_connection.is_closed:
        rabbitmq_connection.close()


app = FastAPI(
    title="Padtec Notification Service",
    description="Service for sending notifications",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "notifier"
    }


@app.post("/test/email")
async def test_email(email: str):
    """Test email notification"""
    if not notification_handler:
        raise HTTPException(status_code=503, detail="Notification handler not initialized")
    
    try:
        await notification_handler.send_email(
            to=email,
            subject="Test Notification",
            body="This is a test notification from Padtec Monitoring System"
        )
        return {"status": "success", "message": "Test email sent"}
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test/telegram")
async def test_telegram():
    """Test Telegram notification"""
    if not notification_handler:
        raise HTTPException(status_code=503, detail="Notification handler not initialized")
    
    try:
        await notification_handler.send_telegram(
            message="Test notification from Padtec Monitoring System"
        )
        return {"status": "success", "message": "Test Telegram message sent"}
    except Exception as e:
        logger.error(f"Error sending test Telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)




