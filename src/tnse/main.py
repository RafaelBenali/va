"""
TNSE - Telegram News Search Engine

Main FastAPI application entry point.

Work Stream: WS-4.1 - Render.com Configuration
Provides health check endpoints for Render.com deployment.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from src.tnse.core.config import get_settings
from src.tnse.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


def get_database_engine():
    """Get a SQLAlchemy engine for database connection checks.

    Returns:
        SQLAlchemy engine instance.
    """
    return create_engine(settings.database.url)


def get_redis_client():
    """Get a Redis client for connection checks.

    Returns:
        Redis client instance.
    """
    return redis.from_url(settings.redis.url)


def check_database_connection() -> bool:
    """Check if the database connection is available.

    Returns:
        True if database is accessible, False otherwise.
    """
    try:
        engine = get_database_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as error:
        logger.warning("Database connection check failed", error=str(error))
        return False


def check_redis_connection() -> bool:
    """Check if the Redis connection is available.

    Returns:
        True if Redis is accessible, False otherwise.
    """
    try:
        client = get_redis_client()
        client.ping()
        return True
    except Exception as error:
        logger.warning("Redis connection check failed", error=str(error))
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    logger.info(
        "Starting TNSE application",
        app_env=settings.app_env,
        debug=settings.debug,
    )
    yield
    logger.info("Shutting down TNSE application")


app = FastAPI(
    title="TNSE - Telegram News Search Engine",
    description="News aggregation and search engine for public Telegram channels",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for monitoring and container orchestration.

    Returns:
        JSON response with health status.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "app": settings.app_name,
            "version": "0.1.0",
        }
    )


@app.get("/")
async def root() -> JSONResponse:
    """
    Root endpoint with API information.

    Returns:
        JSON response with API details.
    """
    return JSONResponse(
        content={
            "name": "TNSE - Telegram News Search Engine",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }
    )


@app.get("/liveness")
async def liveness_check() -> JSONResponse:
    """
    Liveness probe for Render.com deployment.

    This endpoint indicates whether the application is running.
    It always returns OK if the app process is alive.
    Used by Render to determine if the container needs to be restarted.

    Returns:
        JSON response with alive status.
    """
    return JSONResponse(
        content={
            "status": "alive",
        }
    )


@app.get("/readiness")
async def readiness_check() -> JSONResponse:
    """
    Readiness probe for Render.com deployment.

    This endpoint checks if the application is ready to receive traffic.
    It verifies connections to PostgreSQL and Redis.
    Used by Render to determine if traffic should be routed to this instance.

    Returns:
        JSON response with service status (200 if healthy, 503 if not).
    """
    database_healthy = check_database_connection()
    redis_healthy = check_redis_connection()

    all_healthy = database_healthy and redis_healthy
    status = "healthy" if all_healthy else "unhealthy"
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "services": {
                "database": database_healthy,
                "redis": redis_healthy,
            },
        },
    )
