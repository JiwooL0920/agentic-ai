"""Health check endpoints."""


import time

import httpx
import psutil
import structlog
from fastapi import APIRouter
from ollama import AsyncClient

from ...config import get_settings
from ...schemas import ResourceUsage, SystemStats

logger = structlog.get_logger()

router = APIRouter()

# Initialize async Ollama client with configured host
settings = get_settings()
_ollama_client = AsyncClient(host=settings.ollama_host)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy"}


@router.get("/health/detailed")
async def detailed_health_check() -> dict[str, dict[str, str]]:
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
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException, ConnectionError) as e:
        logger.warning("ollama_health_check_failed", error=str(e))
        health_status["ollama"] = {"status": "unhealthy", "error": str(e)}

    return health_status


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe."""
    # Check if essential services are available (non-blocking)
    try:
        await _ollama_client.list()
        return {"status": "ready"}
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException, ConnectionError):
        return {"status": "not_ready"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}


def _format_bytes(bytes_val: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024:
            return f"{bytes_val:.1f}{unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f}PB"


async def _get_ollama_gpu_usage() -> ResourceUsage:
    """Get GPU/VRAM usage from Ollama's running models."""
    try:
        response = await _ollama_client.ps()
        models = response.get("models", [])

        if not models:
            return ResourceUsage(name="gpu", percent=0.0, used="0B", total="N/A")

        total_vram_used = sum(m.get("size_vram", 0) for m in models)
        model_count = len(models)
        model_names = ", ".join(m.get("name", "unknown") for m in models)

        return ResourceUsage(
            name="gpu",
            percent=float(model_count),
            used=_format_bytes(total_vram_used),
            total=f"{model_count} model(s): {model_names}",
        )
    except Exception:
        return ResourceUsage(name="gpu", percent=0.0, used="N/A", total="N/A")


@router.get("/health/stats")
async def system_stats() -> SystemStats:
    cpu_percent = psutil.cpu_percent(interval=0.1)

    mem = psutil.virtual_memory()
    mem_usage = ResourceUsage(
        name="memory",
        percent=mem.percent,
        used=_format_bytes(mem.used),
        total=_format_bytes(mem.total),
    )

    disk = psutil.disk_usage("/")
    disk_usage = ResourceUsage(
        name="storage",
        percent=disk.percent,
        used=_format_bytes(disk.used),
        total=_format_bytes(disk.total),
    )

    gpu_usage = await _get_ollama_gpu_usage()

    return SystemStats(
        cpu=ResourceUsage(name="cpu", percent=cpu_percent, used=None, total=None),
        memory=mem_usage,
        gpu=gpu_usage,
        storage=disk_usage,
        timestamp=time.time(),
    )
