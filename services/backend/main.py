"""
Backend API Service
API REST para o frontend
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from pythonjsonlogger import jsonlogger

from database import Database
from routers import sites, cards, measurements, alarms, rules, config, collector

# Set db reference in routers
def set_db(database: Database):
    """Set database reference in routers"""
    sites.db = database
    cards.db = database
    measurements.db = database
    alarms.db = database
    rules.db = database
    config.db = database

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
    jwt_secret_key: str = "your-secret-key"
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
db: Optional[Database] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global db

    # Startup
    logger.info("Starting Backend API Service")
    
    # Initialize database
    db = Database(settings.database_url)
    await db.initialize()
    set_db(db)  # Set db reference in routers
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down Backend API Service")
    if db:
        await db.close()


# Create FastAPI app
app = FastAPI(
    title="Padtec Monitoring API",
    description="Backend API for Padtec Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sites.router, prefix="/api/sites", tags=["sites"])
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])
app.include_router(measurements.router, prefix="/api/measurements", tags=["measurements"])
app.include_router(alarms.router, prefix="/api/alarms", tags=["alarms"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(collector.router, prefix="/api/collector", tags=["collector"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Padtec Monitoring API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backend"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

