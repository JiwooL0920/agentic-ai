"""
FastAPI Application Factory.

Creates the main API application with all routes and middleware.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from redis.exceptions import RedisError

from ..agents.registry import AgentRegistry
from ..cache.redis_client import init_redis, close_redis
from ..config import get_settings
from .routes import agents, blueprints, chat, health, sessions

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    logger.info("starting_application")

    # Initialize Redis Sentinel connection
    try:
        await init_redis()
        logger.info("redis_sentinel_initialized")
    except (RedisError, ConnectionError, OSError) as e:
        logger.warning("redis_init_failed", error=str(e))

    # Initialize settings and registry using cached singleton
    settings = get_settings()
    blueprints_path = Path(settings.blueprints_path)
    
    # Resolve blueprints path relative to workspace root if not absolute
    if not blueprints_path.is_absolute():
        # Find workspace root: packages/core/src/api/app.py -> go up 4 levels
        workspace_root = Path(__file__).parent.parent.parent.parent.parent
        blueprints_path = workspace_root / blueprints_path
    
    blueprints_path = blueprints_path.resolve()

    app.state.settings = settings
    app.state.registry = AgentRegistry(blueprints_path)

    logger.info(
        "application_ready",
        blueprints_path=str(blueprints_path),
        blueprints=app.state.registry.list_blueprints(),
    )

    yield

    logger.info("shutting_down_application")
    
    # Close Redis connection
    try:
        await close_redis()
        logger.info("redis_closed")
    except (RedisError, ConnectionError, OSError) as e:
        logger.warning("redis_close_failed", error=str(e))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Agentic AI Platform",
        description="Multi-Agent AI Platform with Ollama",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(blueprints.router, prefix="/api", tags=["Blueprints"])
    app.include_router(agents.router, prefix="/api", tags=["Agents"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(sessions.router, prefix="/api", tags=["Sessions"])

    return app
