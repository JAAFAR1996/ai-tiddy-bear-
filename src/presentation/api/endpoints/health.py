# Standard library imports
import logging
from datetime import datetime
from typing import Any

# Third-party imports - production required
try:
    from fastapi import APIRouter, HTTPException, status
    from pydantic import BaseModel
except ImportError as e:
    logging.getLogger(__name__).critical(
        f"CRITICAL ERROR: FastAPI and Pydantic required: {e}",
    )
    logging.getLogger(__name__).critical(
        "Install required dependencies: pip install fastapi pydantic",
    )
    raise ImportError(
        f"Missing required dependencies for health endpoints: {e}"
    ) from e

# Local imports - optional infrastructure
try:
    from infrastructure.config.settings import get_settings
    from infrastructure.monitoring.performance_monitor import (
        get_performance_monitor,
    )
except ImportError as e:
    logging.getLogger(__name__).error(
        f"Health check infrastructure import error: {e}"
    )
    # Continue without optional monitoring features

logger = logging.getLogger(__name__)

"""Production Health Check Endpoints
Enterprise-grade health monitoring with dependency checks"""

router = APIRouter(prefix="/api/v1/health", tags=["Health v1"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    checks: dict[str, dict[str, Any]]
    metrics: dict[str, Any]
    uptime_seconds: float
    version: str


from src.infrastructure.health.checks import (
    check_all_dependencies,
    check_database,
    check_redis,
)


@router.get("/", response_model=HealthStatus)
async def basic_health_check() -> HealthStatus:
    """Basic health check endpoint.
    Returns overall system health status.
    """
    try:
        settings = get_settings()
        monitor = get_performance_monitor()

        # Get performance metrics
        if monitor:
            health_data = await monitor.get_health_status()
            metrics = health_data.get("metrics", {})
            uptime = metrics.get("uptime_seconds", 0)
        else:
            metrics = {}
            uptime = 0

        # Check critical dependencies
        dependency_checks = await check_all_dependencies()

        # Format checks
        checks = {}
        overall_healthy = True

        for check in dependency_checks:
            checks[check.name] = {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "details": check.details,
                "error": check.error,
            }
            if check.status != "healthy":
                overall_healthy = False

        # Determine overall status
        if overall_healthy:
            status = "healthy"
        elif any(
            check.status == "unhealthy"
            for check in dependency_checks
            if check.name in ["database", "redis"]
        ):
            status = "unhealthy"  # Critical dependencies failing
        else:
            status = "degraded"  # Non-critical dependencies failing

        return HealthStatus(
            status=status,
            timestamp=datetime.now(),
            checks=checks,
            metrics=metrics,
            uptime_seconds=uptime,
            version=settings.APP_VERSION,
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {e!s}",
        )


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Kubernetes readiness probe endpoint.
    Checks if the application is ready to serve traffic.
    """
    try:
        # Check critical dependencies only
        db_check = await check_database()
        redis_check = await check_redis()

        ready = (
            db_check.status == "healthy" and redis_check.status == "healthy"
        )

        if ready:
            return {
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "checks": {
                    "database": db_check.status,
                    "redis": redis_check.status,
                },
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Readiness check failed: {e!s}",
        )


@router.get("/live")
async def liveness_check() -> dict[str, Any]:
    """Kubernetes liveness probe endpoint.
    Simple check to verify the application is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid() if "os" in globals() else None,
    }


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    """Get application performance metrics."""
    try:
        monitor = get_performance_monitor()
        if monitor:
            metrics = await monitor.get_performance_summary()
            return {
                "request_count": metrics.request_count,
                "avg_response_time": metrics.avg_response_time,
                "error_count": metrics.error_count,
                "memory_usage_mb": metrics.memory_usage_mb,
                "cpu_usage_percent": metrics.cpu_usage_percent,
                "active_connections": metrics.active_connections,
                "cache_hit_rate": metrics.cache_hit_rate,
                "timestamp": metrics.timestamp.isoformat(),
            }
        return {
            "error": "Performance monitoring not available",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Metrics endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metrics collection failed: {e!s}",
        )


@router.get("/dependencies")
async def check_dependencies() -> dict[str, Any]:
    """Detailed dependency health checks."""
    try:
        dependency_checks = await check_all_dependencies()
        return {
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                check.name: {
                    "status": check.status,
                    "response_time_ms": check.response_time_ms,
                    "details": check.details,
                    "error": check.error,
                }
                for check in dependency_checks
            },
        }
    except Exception as e:
        logger.error(f"Dependencies check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dependencies check failed: {e!s}",
        )
