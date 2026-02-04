"""Health check endpoints."""

from typing import Dict

import structlog
from fastapi import APIRouter
from ollama import AsyncClient

logger = structlog.get_logger()

router = APIRouter()

# Initialize async Ollama client
_ollama_client = AsyncClient()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Dict[str, str]]:
    """Detailed health check including dependencies."""
    health_status = {
        "api": {"status": "healthy"},
        "ollama": {"status": "unknown"},
    }

    # Check Ollama connection (non-blocking)
    try:
        models = await _ollama_client.list()
        health_status["ollama"] = {
            "status": "healthy",
            "models": str(len(models.get("models", []))),
        }
    except Exception as e:
        logger.warning("ollama_health_check_failed", error=str(e))
        health_status["ollama"] = {"status": "unhealthy", "error": str(e)}

    return health_status


@router.get("/ready")
async def readiness_check() -> Dict[str, str]:
    """Kubernetes readiness probe."""
    # Check if essential services are available (non-blocking)
    try:
        await _ollama_client.list()
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}
