"""
TNSE - Telegram News Search Engine

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.tnse.core.config import get_settings
from src.tnse.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


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
