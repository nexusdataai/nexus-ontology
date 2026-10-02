"""
Health and Monitoring REST API
System health checks, liveness/readiness probes, and metrics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import psutil
import os
from loguru import logger

# FDW service references (set during app startup)
_fdw_connection_manager = None
_fdw_discovery_service = None


def configure_fdw(connection_manager=None, discovery_service=None):
    """Configure FDW health check with service instances."""
    global _fdw_connection_manager, _fdw_discovery_service
    _fdw_connection_manager = connection_manager
    _fdw_discovery_service = discovery_service


fdw_logger = logger.bind(component="fdw")

# Import LocalStack utilities
try:
    from ..utils.aws_client_utils import get_default_client_manager
    from ..config.localstack_config import is_localstack_enabled
    HAS_LOCALSTACK = True
except ImportError:
    HAS_LOCALSTACK = False
    def is_localstack_enabled():
        return os.getenv('USE_LOCALSTACK', 'false').lower() == 'true'
    def get_default_client_manager():
        return None

# Create router
router = APIRouter()


# ==========================================
# Health Check Endpoints
# ==========================================

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint
    
    Returns 200 if service is operational.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "message": "Service is operational",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/live")
async def liveness_probe() -> Dict[str, Any]:
    """
    Kubernetes liveness probe
    
    Returns 200 if the service is alive.
    Returns 503 if the service should be restarted.
    """
    try:
        # Basic liveness check
        # In production, check critical dependencies
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@router.get("/ready")
async def readiness_probe() -> Dict[str, Any]:
    """
    Kubernetes readiness probe
    
    Returns 200 if ready to serve traffic.
    Returns 503 if warming up or not ready.
    """
    try:
        # Check if service is ready
        # In production, verify all dependencies are available
        checks = {
            "api": True,
            "models": True,
            "services": True  # Would check actual service availability
        }
        
        all_ready = all(checks.values())
        
        if not all_ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "checks": checks
                }
            )
        
        return {
            "status": "ready",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get system metrics and statistics
    
    Returns CPU, memory, and application-specific metrics.
    """
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        # Get process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        metrics = {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_total_gb": memory.total / (1024**3)
            },
            "process": {
                "memory_rss_mb": process_memory.rss / (1024**2),
                "memory_vms_mb": process_memory.vms / (1024**2),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "num_threads": process.num_threads()
            },
            "application": {
                "uptime_seconds": (datetime.utcnow() - datetime(2024, 1, 1)).total_seconds(),  # Mock uptime
                "requests_total": 1000,  # Mock metrics
                "requests_per_second": 10.5,
                "average_response_time_ms": 125.3,
                "error_rate": 0.01
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "error": "Could not retrieve metrics",
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/dependencies")
async def check_dependencies() -> Dict[str, Any]:
    """
    Check status of external dependencies
    
    Verifies connectivity to databases, APIs, and other services.
    """
    dependencies = {}
    
    # Check MCP workers (mock)
    dependencies["mcp_workers"] = {
        "status": "healthy",
        "available": 2,
        "response_time_ms": 45
    }
    
    # Check database (mock)
    dependencies["database"] = {
        "status": "healthy",
        "connection_pool": {
            "active": 3,
            "idle": 7,
            "max": 10
        },
        "response_time_ms": 12
    }
    
    # Check external APIs (mock)
    dependencies["external_apis"] = {
        "oda_api": {
            "status": "healthy",
            "last_check": datetime.utcnow().isoformat()
        }
    }
    
    # Check FDW database (Requirement 6.6)
    if _fdw_connection_manager is None:
        dependencies["fdw"] = {"status": "disabled"}
    else:
        try:
            fdw_health_result = await _fdw_connection_manager.health_check()
            dependencies["fdw"] = fdw_health_result
        except Exception as e:
            dependencies["fdw"] = {"status": "unhealthy", "error": str(e)}

    # Data Queue backend (Phase 4 of the Data Queues plan). Green when
    # DATA_QUEUE_BACKEND=in_memory (always healthy) or when Redis is
    # reachable.
    import os as _os
    backend = (_os.environ.get("DATA_QUEUE_BACKEND") or "in_memory").lower().strip()
    if backend == "in_memory":
        dependencies["data_queue"] = {"status": "healthy", "backend": "in_memory"}
    elif backend == "redis":
        try:
            from src.services.control_plane.data_queue import make_data_queue_manager
            mgr = make_data_queue_manager("redis")
            # ``snapshot`` on a non-existent run is a cheap probe -- it
            # only triggers the lazy client open + ping.
            _ = await mgr.snapshot("__health_probe__")
            dependencies["data_queue"] = {"status": "healthy", "backend": "redis"}
        except Exception as e:
            dependencies["data_queue"] = {"status": "unhealthy", "backend": "redis", "error": str(e)}
    else:
        dependencies["data_queue"] = {"status": "unknown", "backend": backend}

    # Overall health
    all_healthy = all(
        dep.get("status") in ("healthy", "disabled")
        for dep in dependencies.values()
        if isinstance(dep, dict) and "status" in dep
    )
    
    return {
        "overall_status": "healthy" if all_healthy else "degraded",
        "dependencies": dependencies,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/debug")
async def debug_info() -> Dict[str, Any]:
    """
    Get debug information
    
    Returns detailed system and application state.
    Only available in development mode.
    """
    # In production, this should be protected or disabled
    import platform
    import sys
    
    debug_data = {
        "system": {
            "platform": platform.platform(),
            "python_version": sys.version,
            "processor": platform.processor(),
            "hostname": platform.node()
        },
        "environment": {
            "gateway_port": os.getenv("GATEWAY_PORT", "8000"),
            "min_workers": os.getenv("MIN_WORKERS", "2"),
            "max_workers": os.getenv("MAX_WORKERS", "8"),
            "api_key_configured": bool(os.getenv("API_KEY"))
        },
        "paths": {
            "working_directory": os.getcwd(),
            "python_path": sys.path[:3]  # First 3 paths only
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return debug_data


@router.post("/ping")
async def ping(message: Optional[str] = "pong") -> Dict[str, Any]:
    """
    Simple ping endpoint for testing
    
    Echoes back the provided message or default "pong".
    """
    return {
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/localstack")
async def localstack_health() -> Dict[str, Any]:
    """
    Check LocalStack connectivity and service status
    
    Returns:
        - status: "disabled" if LocalStack mode is off
        - status: "healthy" if LocalStack is running and responsive
        - status: "unhealthy" with troubleshooting if LocalStack is not accessible
    
    This endpoint is useful for:
        - Verifying LocalStack is running before development
        - Debugging connection issues
        - CI/CD pipeline health checks
    """
    # Check if LocalStack mode is enabled
    if not is_localstack_enabled():
        return {
            "status": "disabled",
            "message": "LocalStack mode is not enabled",
            "hint": "Set USE_LOCALSTACK=true to enable LocalStack mode",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Get client manager and test connection
    if not HAS_LOCALSTACK:
        return {
            "status": "error",
            "message": "LocalStack utilities not available",
            "hint": "Check that localstack_config and aws_client_utils modules are installed",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        client_manager = get_default_client_manager()
        if client_manager is None:
            return {
                "status": "error",
                "message": "Could not get AWS client manager",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Test LocalStack connection
        health_result = client_manager.test_localstack_connection()
        
        if not health_result.get("enabled"):
            return {
                "status": "disabled",
                "message": health_result.get("message", "LocalStack not enabled"),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if health_result.get("healthy"):
            return {
                "status": "healthy",
                "endpoint": health_result.get("endpoint"),
                "region": health_result.get("region"),
                "services": health_result.get("services", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Unhealthy - return troubleshooting info
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "endpoint": health_result.get("endpoint"),
                    "error": health_result.get("error"),
                    "troubleshooting": health_result.get("troubleshooting", [
                        "Check if LocalStack is running: docker ps | grep localstack",
                        "Start LocalStack: ./scripts/start-localstack.sh (Linux) or .\\scripts\\start-localstack.ps1 (Windows)",
                        "Check LocalStack logs: docker logs nexus-localstack",
                        "Verify endpoint: curl http://localhost:4566/_localstack/health"
                    ]),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LocalStack health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": str(e),
                "troubleshooting": [
                    "Ensure LocalStack is running",
                    "Check LOCALSTACK_HOST and LOCALSTACK_PORT environment variables",
                    "Run: ./scripts/start-localstack.sh"
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
        )



@router.get("/aws")
async def aws_health() -> Dict[str, Any]:
    """
    Report the active AWS access mode + STS caller identity.

    Used by ops to verify the operator's network-profile projection is in
    effect (e.g. after flipping NexusNetworkConfig.spec.awsAccessMode) and
    that the backend can reach AWS APIs over the expected network path.

    Returns:
        - ``aws_access_mode``: one of ``higher-cost`` / ``moderate`` /
          ``lowest-cost`` / ``public-nodes`` / ``localstack``.
        - ``explicit_endpoints_disabled``: bool — true when boto3 is routing
          to default public regional hostnames.
        - ``sts_identity``: ``{account, arn, userId}`` from STS GetCallerIdentity.
        - ``region``: resolved AWS region.
    """
    try:
        from ..utils import aws_access_config as _ac
        mode = _ac.get_access_mode().value
        disabled = _ac.explicit_endpoints_disabled()
    except Exception as e:
        mode = "unknown"
        disabled = False
        logger.warning(f"Could not resolve aws_access_mode: {e}")

    result: Dict[str, Any] = {
        "aws_access_mode": mode,
        "explicit_endpoints_disabled": disabled,
        "region": os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        "timestamp": datetime.utcnow().isoformat(),
    }

    client_manager = get_default_client_manager() if HAS_LOCALSTACK else None
    if client_manager is None:
        result["sts_identity"] = None
        result["error"] = "AWS client manager unavailable"
        return result

    try:
        identity = client_manager.test_credentials()
        result["sts_identity"] = {
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
            "userId": identity.get("UserId"),
        }
        result["status"] = "healthy"
    except Exception as e:
        # Don't fail the endpoint — surface the error and let ops decide.
        result["status"] = "unhealthy"
        result["sts_identity"] = None
        result["error"] = str(e)[:200]
        logger.warning(f"STS get_caller_identity failed: {e}")

    return result


@router.get("/fdw")
async def fdw_health() -> Dict[str, Any]:
    """
    Check FDW database connectivity and status.

    Returns:
        - status: "disabled" when FDW is not configured
        - status: "healthy" with latency and counts when connected
        - status: "unhealthy" with error details when connection fails

    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    """
    if _fdw_connection_manager is None:
        return {"status": "disabled"}

    try:
        health = await _fdw_connection_manager.health_check()
        result = {
            "status": health.get("status", "unhealthy"),
            "latencyMs": health.get("latency_ms"),
        }

        if health.get("error"):
            result["error"] = health["error"]

        # Include foreign server/table counts if healthy and discovery available
        if health.get("status") == "healthy" and _fdw_discovery_service is not None:
            try:
                servers = await _fdw_discovery_service.list_foreign_servers()
                tables = await _fdw_discovery_service.list_foreign_tables()
                result["foreignServersCount"] = len(servers)
                result["foreignTablesCount"] = len(tables)
            except Exception as disc_err:
                fdw_logger.warning("Failed to get FDW counts for health check", error=str(disc_err))
                result["foreignServersCount"] = None
                result["foreignTablesCount"] = None

        return result

    except Exception as e:
        fdw_logger.error("FDW health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}
