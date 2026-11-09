#!/usr/bin/env python3
"""
MCP HTTP Gateway with Worker Pool and Streaming Support
Manages subprocess workers running the MCP server and provides HTTP/WebSocket interfaces
"""

import asyncio
import json
import logging
import re
import sys
import os
from pathlib import Path

# Load .env file before any os.getenv() calls
# Priority: .env.local > .env > system environment variables
try:
    from dotenv import load_dotenv
    # Check for .env.local first (LocalStack development)
    env_local_path = Path(__file__).parent / '.env.local'
    env_path = Path(__file__).parent / '.env'
    
    if env_local_path.exists():
        load_dotenv(env_local_path, override=True)
    elif env_path.exists():
        load_dotenv(env_path, override=True)
    else:
        load_dotenv()  # Try default locations
    if os.getenv('USE_LOCALSTACK', '').lower().strip() == 'true':
        os.environ.pop('AWS_PROFILE', None)
        os.environ.pop('AWS_DEFAULT_PROFILE', None)
except ImportError:
    pass  # dotenv not installed, rely on system environment variables
from typing import Any, Dict, Optional, List
from uuid import uuid4
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
from pydantic import BaseModel
import uvicorn
from loguru import logger

# Import API modules for unified gateway
try:
    from src.apis import journey_api, analytics_api, auth_api, health_api, diagnostics_api, user_management_api, plugin_api, copilot_journey_api, app_data_api, dashboard_api, dashboard_query_api, tests_api, solution_api, view_api
    API_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"API modules not available: {e}")
    API_MODULES_AVAILABLE = False

# Import config API separately (simpler dependencies, independent from main APIs)
try:
    from src.apis import config_api
    CONFIG_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Config API not available: {e}")
    logger.exception(e)
    CONFIG_API_AVAILABLE = False

# Import License API module
try:
    from src.license.apis import license_api
    LICENSE_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"License API module not available: {e}")
    LICENSE_API_AVAILABLE = False

# Import Schedule API module
try:
    from src.apis import schedule_api
    SCHEDULE_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Schedule API not available: {e}")
    SCHEDULE_API_AVAILABLE = False

# Import Control Plane API module
try:
    from src.apis import control_plane_api
    CONTROL_PLANE_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Control Plane API not available: {e}")
    CONTROL_PLANE_API_AVAILABLE = False

# Import FDW API modules
try:
    from src.apis import fdw_api
    FDW_API_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FDW API modules not available: {e}")
    FDW_API_AVAILABLE = False

# Import FDW lifecycle management
try:
    from src.fdw_lifecycle import initialize_fdw, shutdown_fdw
    FDW_LIFECYCLE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FDW lifecycle not available: {e}")
    FDW_LIFECYCLE_AVAILABLE = False

# Import Data Plane lifecycle management
try:
    from src.data_plane_lifecycle import initialize_data_plane, shutdown_data_plane
    DATA_PLANE_LIFECYCLE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Data Plane lifecycle not available: {e}")
    DATA_PLANE_LIFECYCLE_AVAILABLE = False

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=os.getenv("LOG_LEVEL") or os.getenv("SERVER_LOG_LEVEL", "INFO"),
    format="{time:HH:mm:ss} | {level} | GATEWAY | {module}:{function} | {message}",
    colorize=True,
    catch=True
)

# Import and log LocalStack configuration
try:
    from src.config.localstack_config import get_localstack_config, is_localstack_enabled
    HAS_LOCALSTACK_CONFIG = True
    
    if is_localstack_enabled():
        _ls_config = get_localstack_config()
        logger.info(f"LocalStack mode ENABLED - endpoint: {_ls_config.endpoint_url}")
    else:
        logger.info("LocalStack mode DISABLED - using real AWS endpoints")
except ImportError as e:
    HAS_LOCALSTACK_CONFIG = False
    logger.debug(f"LocalStack config module not available: {e}")

# Initialize ConfigProvider early to load SSM/Secrets on AWS or env vars locally
try:
    from src.config.config_provider import get_config, CAPABILITY_NAME
    _app_config = get_config()
    logger.info(f"Config initialized: capability={CAPABILITY_NAME}, env={_app_config.environment}")
    logger.info(f"DynamoDB tables: transformation={_app_config.dynamodb_transformation_table}, license={_app_config.dynamodb_license_table}")
    logger.info(f"S3 buckets: recordings={_app_config.s3_recordings_bucket}")
except ImportError as e:
    logger.warning(f"ConfigProvider not available: {e}")

# FastAPI app - Now a unified gateway for both MCP tools and REST APIs
app = FastAPI(
    title="AI Job Engine Unified Gateway",
    description="Unified HTTP/WebSocket gateway for MCP tools and REST APIs with streaming support",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS allowed origins - localhost and specific IPs for development
CORS_ORIGINS_LOCALHOST = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8000",
    "http://10.0.0.3:8080",
]

# Regex pattern to match all *.totogicore.com subdomains (HTTP and HTTPS)
CORS_ORIGIN_REGEX = r"^https?://([a-zA-Z0-9-]+\.)*totogicore\.com$"

# Combined list for backward compatibility (used in exception handler)
CORS_ORIGINS = CORS_ORIGINS_LOCALHOST + [
    "https://dev.econet.totogicore.com",
    "https://stage.econet.totogicore.com",
    "https://econet.totogicore.com",
    "https://call.totogicore.com",
    "https://call-api.totogicore.com",
    "https://call-dev.totogicore.com",
    "https://call-api-dev.totogicore.com",
]

_cors_pattern = re.compile(CORS_ORIGIN_REGEX)

def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed by CORS policy (localhost or *.totogicore.com)."""
    if not origin:
        return False
    # Check localhost/IP origins
    if origin in CORS_ORIGINS_LOCALHOST:
        return True
    # Check wildcard pattern for totogicore.com
    return bool(_cors_pattern.match(origin))

# Add CORS middleware with regex support for *.totogicore.com
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS_LOCALHOST,  # Exact matches for localhost
    allow_origin_regex=CORS_ORIGIN_REGEX,  # Wildcard for *.totogicore.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Diagnostics response recorder middleware (Phase 1, data-organization spec).
# Must be registered at module scope BEFORE the app starts serving - Starlette
# forbids ``add_middleware`` inside the startup event. Auto-persists any
# ``/api/v1/diagnostics/*`` and ``/api/v1/connector-apis/diagnostic|smoke-test``
# response into the diagnostics DDB table via DiagnosticsHistoryService.
try:
    from src.utils.diagnostics_recorder import register_diagnostics_recorder
    register_diagnostics_recorder(app)
except Exception as _dr_err:
    logger.warning(f"Diagnostics recorder middleware registration failed (non-fatal): {_dr_err}")


# Custom exception handler to ensure CORS headers on error responses
@app.exception_handler(Exception)
async def cors_exception_handler(request: Request, exc: Exception):
    """Ensure CORS headers are included on all error responses."""
    origin = request.headers.get("origin", "")
    
    # Build error response
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
        detail = exc.detail
    else:
        status_code = 500
        detail = "Internal Server Error"
        logger.error(f"Unhandled exception: {exc}")
    
    response = JSONResponse(
        status_code=status_code,
        content={"detail": detail}
    )
    
    # Add CORS headers if origin is allowed (supports *.totogicore.com wildcard)
    if is_allowed_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


# Configuration
MIN_WORKERS = int(os.getenv("MIN_WORKERS", "2"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
MCP_REQUEST_TIMEOUT = float(os.getenv("MCP_REQUEST_TIMEOUT", "60.0"))
API_KEY = os.getenv("API_KEY", "super-secret")  # Use environment variable in production

# Command to run MCP server - detect environment
import shutil
import sys

# Detect Python environment - prefer current interpreter for consistency
if sys.executable:
    # Use the same Python that's running this script
    PYTHON_CMD = sys.executable
elif os.path.exists("/opt/venv/bin/python"):
    # Docker container with venv in /opt/venv
    PYTHON_CMD = "/opt/venv/bin/python"
elif os.name == 'nt' and os.path.exists(".venv/Scripts/python.exe"):
    # Windows local development with .venv
    PYTHON_CMD = os.path.abspath(".venv/Scripts/python.exe")
elif os.path.exists(".venv/bin/python"):
    # Linux/Mac local development with .venv
    PYTHON_CMD = os.path.abspath(".venv/bin/python")
elif shutil.which("python"):
    # System Python
    PYTHON_CMD = "python"
else:
    # Fallback
    PYTHON_CMD = "python3"

# Command to run unified MCP server
MCP_CMD = [PYTHON_CMD, "-m", "src.server", "--stdio"]
logger.info(f"Using Python command: {PYTHON_CMD}")

# ------------ MODELS ------------

class MCPEnvelope(BaseModel):
    """Raw MCP JSON-RPC envelope"""
    payload: Dict[str, Any]

class ToolCallRequest(BaseModel):
    """Tool call request with arguments"""
    arguments: Dict[str, Any]
    id: Optional[str] = None

class StreamResponse(BaseModel):
    """Streaming response chunk"""
    index: int
    data: Any
    event: Optional[str] = None

# ------------ AUTH ------------

async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key for authentication"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ------------ MCP WORKER ------------

class MCPWorker:
    """
    Represents a single MCP subprocess worker.
    Each worker has its own process and lock for thread-safe communication.
    
    Memory-safety: Includes stderr draining to prevent buffer accumulation.
    """
    
    def __init__(self, worker_id: int, cmd: List[str]):
        self.worker_id = worker_id
        self.cmd = cmd
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.lock = asyncio.Lock()
        self.busy = False
        self.request_count = 0
        self.error_count = 0
        self.last_used = datetime.now()
        self._stderr_task: Optional[asyncio.Task] = None
        self._stderr_lines: List[str] = []  # Keep last N lines for debugging
        self._max_stderr_lines = 100  # Maximum stderr lines to keep
    
    def _get_worker_environment(self) -> dict:
        """
        Prepare environment variables for MCP worker subprocess.
        
        Ensures LocalStack-related variables are passed to workers so that
        MCP tools can access LocalStack services when LocalStack mode is enabled.
        """
        worker_env = os.environ.copy()
        
        # LocalStack-related environment variables to pass to workers
        localstack_vars = [
            'USE_LOCALSTACK', 'LOCALSTACK_HOST', 'LOCALSTACK_PORT',
            'AWS_DEFAULT_REGION', 'AWS_REGION', 'AWS_ACCESS_KEY_ID', 
            'AWS_SECRET_ACCESS_KEY', 'AWS_ENDPOINT_URL',
            'AWS_ENDPOINT_URL_DYNAMODB', 'AWS_ENDPOINT_URL_S3',
            'AWS_ENDPOINT_URL_CLOUDWATCH', 'AWS_ENDPOINT_URL_STS'
        ]
        
        # Ensure all LocalStack vars from current environment are included
        for var in localstack_vars:
            if var in os.environ:
                worker_env[var] = os.environ[var]

        # K3s dev: AWS_PROFILE=local is for kubectl, not boto3
        if os.getenv('USE_LOCALSTACK', '').lower().strip() == 'true':
            worker_env.pop('AWS_PROFILE', None)
            worker_env.pop('AWS_DEFAULT_PROFILE', None)
        
        return worker_env
    
    async def _drain_stderr(self):
        """
        Background task to drain stderr and prevent buffer accumulation.
        
        Keeps the last N lines for debugging purposes.
        """
        if not self.proc or not self.proc.stderr:
            return
        
        try:
            while True:
                try:
                    line = await self.proc.stderr.readline()
                    if not line:
                        # EOF - process ended
                        break
                    
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    if decoded_line:
                        # Keep last N lines in circular buffer
                        self._stderr_lines.append(decoded_line)
                        if len(self._stderr_lines) > self._max_stderr_lines:
                            self._stderr_lines.pop(0)
                        
                        # Log errors and warnings
                        if 'error' in decoded_line.lower() or 'exception' in decoded_line.lower():
                            logger.warning(f"[Worker {self.worker_id}] stderr: {decoded_line}")
                        else:
                            logger.debug(f"[Worker {self.worker_id}] stderr: {decoded_line}")
                            
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"[Worker {self.worker_id}] stderr drain error: {e}")
                    break
        except Exception as e:
            logger.debug(f"[Worker {self.worker_id}] stderr drain stopped: {e}")
    
    def get_recent_stderr(self) -> List[str]:
        """Get recent stderr lines for debugging."""
        return self._stderr_lines.copy()
        
    async def start(self):
        """Start the MCP subprocess with LocalStack environment."""
        if self.proc is not None:
            return
            
        logger.info(f"[Worker {self.worker_id}] Starting MCP subprocess...")
        
        # Get environment with LocalStack variables
        worker_env = self._get_worker_environment()
        
        # Log LocalStack status for this worker
        if worker_env.get('USE_LOCALSTACK', '').lower() == 'true':
            ls_host = worker_env.get('LOCALSTACK_HOST', 'localhost')
            ls_port = worker_env.get('LOCALSTACK_PORT', '4566')
            logger.debug(f"[Worker {self.worker_id}] LocalStack mode enabled - endpoint: http://{ls_host}:{ls_port}")
        
        # Use larger buffer limit (10MB) to handle large responses like journey lists
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=Path(__file__).parent,  # Set working directory
            env=worker_env,  # Pass environment with LocalStack variables
            limit=10 * 1024 * 1024,  # 10MB buffer limit for large responses
        )
        
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError(f"[Worker {self.worker_id}] Missing stdin/stdout")
        
        # Start stderr draining task to prevent buffer accumulation
        self._stderr_task = asyncio.create_task(self._drain_stderr())
            
        # Initialize the MCP server
        await self._initialize()
        
    async def _initialize(self):
        """Send initialization request to MCP server"""
        init_message = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "MCP HTTP Gateway",
                    "version": "2.0.0"
                }
            }
        }
        
        response = await self.send_one(init_message, timeout=30.0)
        if "error" in response:
            raise RuntimeError(f"[Worker {self.worker_id}] Failed to initialize: {response['error']}")
        logger.info(f"[Worker {self.worker_id}] Initialized successfully")
        
    async def stop(self):
        """Stop the MCP subprocess and cleanup tasks"""
        if not self.proc:
            return
        
        # Cancel stderr draining task first
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None
            
        logger.info(f"[Worker {self.worker_id}] Stopping MCP subprocess...")
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            logger.warning(f"[Worker {self.worker_id}] Kill after timeout")
            self.proc.kill()
        self.proc = None
        self._stderr_lines.clear()
        
    async def send_one(self, message: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        """
        Send a single MCP request and read one line response.
        Suitable for non-streaming tools.
        """
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise HTTPException(status_code=500, detail="Worker not ready")
            
        line = json.dumps(message) + "\n"
        
        async with self.lock:
            self.busy = True
            self.last_used = datetime.now()
            self.request_count += 1
            
            try:
                self.proc.stdin.write(line.encode("utf-8"))
                await self.proc.stdin.drain()
                
                try:
                    resp_line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    self.error_count += 1
                    raise HTTPException(status_code=504, detail="MCP worker timed out")
            finally:
                self.busy = False
                
        if not resp_line:
            self.error_count += 1
            raise HTTPException(status_code=502, detail="Empty response from MCP worker")
            
        try:
            return json.loads(resp_line.decode("utf-8"))
        except Exception as e:
            self.error_count += 1
            logger.exception(f"[Worker {self.worker_id}] Invalid JSON from MCP")
            raise HTTPException(status_code=502, detail=f"Invalid JSON response: {str(e)}")
            
    async def stream(self, message: Dict[str, Any], websocket: WebSocket, timeout: float):
        """
        Streaming mode: send a single MCP request, then forward
        multiple JSON lines from MCP to the WebSocket.
        """
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise HTTPException(status_code=500, detail="Worker not ready")
            
        line = json.dumps(message) + "\n"
        
        async with self.lock:
            self.busy = True
            self.last_used = datetime.now()
            self.request_count += 1
            
            try:
                # Send the request
                self.proc.stdin.write(line.encode("utf-8"))
                await self.proc.stdin.drain()
                
                # Stream responses
                chunk_count = 0
                while True:
                    try:
                        resp_line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=timeout)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"event": "timeout", "error": "MCP worker timed out"})
                        break
                        
                    if not resp_line:
                        # MCP closed stream
                        break
                        
                    try:
                        payload = json.loads(resp_line.decode("utf-8"))
                    except Exception as e:
                        logger.exception(f"[Worker {self.worker_id}] Invalid streaming JSON")
                        await websocket.send_json({"event": "error", "error": f"Invalid JSON: {str(e)}"})
                        continue
                        
                    # Check for different event types
                    if "result" in payload:
                        # Final result
                        await websocket.send_json({"event": "result", "data": payload["result"]})
                        break
                    elif "progress" in payload:
                        # Progress update
                        await websocket.send_json({"event": "progress", **payload})
                    else:
                        # Stream chunk
                        await websocket.send_json({"event": "chunk", "index": chunk_count, "data": payload})
                        chunk_count += 1
                        
            finally:
                self.busy = False

# ------------ WORKER POOL ------------

class WorkerPool:
    """
    Multi-worker pool with auto-scaling and health monitoring
    """
    
    def __init__(self, min_workers: int, max_workers: int, cmd: List[str]):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.cmd = cmd
        self.workers: List[MCPWorker] = []
        self._rr_index = 0
        self._lock = asyncio.Lock()
        self._health_check_task = None
        
    async def start(self):
        """Start minimum workers and health monitoring"""
        # Start minimum workers
        for i in range(self.min_workers):
            worker = MCPWorker(i, self.cmd)
            await worker.start()
            self.workers.append(worker)
        logger.info(f"WorkerPool started with {len(self.workers)} workers")
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._monitor_health())
        
    async def stop(self):
        """Stop all workers and monitoring"""
        if self._health_check_task:
            self._health_check_task.cancel()
            
        for w in self.workers:
            await w.stop()
            
    async def _monitor_health(self):
        """Periodic health check and worker management"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                async with self._lock:
                    # Remove failed workers
                    healthy_workers = []
                    for w in self.workers:
                        if w.proc and w.proc.returncode is None:
                            healthy_workers.append(w)
                        else:
                            logger.warning(f"[Worker {w.worker_id}] Found dead, removing")
                            
                    self.workers = healthy_workers
                    
                    # Ensure minimum workers
                    while len(self.workers) < self.min_workers:
                        worker_id = max([w.worker_id for w in self.workers], default=-1) + 1
                        worker = MCPWorker(worker_id, self.cmd)
                        await worker.start()
                        self.workers.append(worker)
                        logger.info(f"Health check: spawned replacement worker {worker_id}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                
    async def _spawn_worker_if_possible(self) -> Optional[MCPWorker]:
        """Spawn new worker if under max limit"""
        if len(self.workers) >= self.max_workers:
            return None
            
        worker_id = max([w.worker_id for w in self.workers], default=-1) + 1
        worker = MCPWorker(worker_id, self.cmd)
        await worker.start()
        self.workers.append(worker)
        logger.info(f"Auto-scaled: spawned worker {worker_id}. Now {len(self.workers)} workers")
        return worker
        
    async def get_worker(self) -> MCPWorker:
        """
        Get an available worker using intelligent selection
        """
        async with self._lock:
            # Try to find idle worker
            for w in self.workers:
                if not w.busy and w.proc and w.proc.returncode is None:
                    return w
                    
            # All busy - try to spawn new one
            maybe_new = await self._spawn_worker_if_possible()
            if maybe_new:
                return maybe_new
                
            # Fallback: round-robin among existing
            if not self.workers:
                raise HTTPException(status_code=500, detail="No MCP workers available")
                
            # Find least busy worker
            best_worker = min(self.workers, key=lambda w: (w.busy, w.request_count))
            return best_worker
            
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            "total_workers": len(self.workers),
            "busy_workers": sum(1 for w in self.workers if w.busy),
            "total_requests": sum(w.request_count for w in self.workers),
            "total_errors": sum(w.error_count for w in self.workers),
            "worker_details": [
                {
                    "id": w.worker_id,
                    "busy": w.busy,
                    "requests": w.request_count,
                    "errors": w.error_count,
                    "last_used": w.last_used.isoformat()
                }
                for w in self.workers
            ]
        }

# Initialize worker pool
pool = WorkerPool(MIN_WORKERS, MAX_WORKERS, MCP_CMD)

@app.on_event("startup")
async def startup_event():
    """Start worker pool and mount API routes on application startup"""
    await pool.start()
    logger.info(f"Gateway started with {MIN_WORKERS} min workers, {MAX_WORKERS} max workers")
    
    # Debug: Log availability flags
    logger.info(f"API availability: API_MODULES={API_MODULES_AVAILABLE}, CONFIG_API={CONFIG_API_AVAILABLE}, LICENSE_API={LICENSE_API_AVAILABLE}")
    
    # Mount API routers if available
    if API_MODULES_AVAILABLE:
        mount_api_routes()
        logger.info("API routes mounted successfully")
    
    # Mount Configuration API independently (minimal dependencies)
    if CONFIG_API_AVAILABLE:
        mount_config_api()
        logger.info("Configuration API mounted successfully")
    else:
        logger.warning("Configuration API is NOT available - skipping mount")
    
    # Mount User Management API
    try:
        app.include_router(
            user_management_api.router,
            prefix="/api/v1/users",
            tags=["User Management"],
            responses={401: {"description": "Unauthorized"}, 403: {"description": "Admin access required"}}
        )
        logger.info("Mounted User Management APIs at /api/v1/users")
    except Exception as e:
        logger.warning(f"User Management API not mounted: {e}")
    
    # Mount License API independently (doesn't require jose)
    if LICENSE_API_AVAILABLE:
        mount_license_api()
        logger.info("License API mounted successfully")
    
    # Mount Google Drive Connector API
    try:
        from src.apis import gdrive_connector_api
        app.include_router(
            gdrive_connector_api.router,
            prefix="/api/v1/connectors/gdrive",
            tags=["Google Drive Connector"],
        )
        logger.info("Mounted Google Drive Connector APIs at /api/v1/connectors/gdrive")
    except Exception as e:
        logger.warning(f"Failed to mount Google Drive Connector API: {e}")
    
    # Mount RBAC API independently
    try:
        mount_rbac_api()
        logger.info("RBAC API mounted successfully")
    except Exception as e:
        logger.warning(f"Failed to mount RBAC API: {e}")

    # Mount Schedule API and start batch scheduler
    if SCHEDULE_API_AVAILABLE:
        mount_schedule_api()
        logger.info("Schedule API mounted successfully")
    try:
        from src.services.scheduler_service import SchedulerService
        scheduler = SchedulerService.get_instance()
        await scheduler.start()
        logger.info("Batch scheduler started")
    except Exception as e:
        logger.warning(f"Failed to start batch scheduler: {e}")

    # NOTE: legacy tools_api (hardcoded sample list) intentionally NOT mounted.
    # The Tool Builder router (tools_builder_api) owns /api/v1/tools and is
    # mounted further below once the ToolStoreService + DynamicToolLoader
    # are constructed via control_plane_api._ensure_init.

    # Mount Audit API
    try:
        from src.apis.audit_api import router as audit_router
        app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])
        logger.info("Audit API mounted at /api/v1/audit")
    except Exception as e:
        logger.warning(f"Failed to mount Audit API: {e}")

    # Mount AI Control Plane API
    if CONTROL_PLANE_API_AVAILABLE:
        try:
            app.include_router(
                control_plane_api.router,
                prefix="/api/v1/control-plane",
                tags=["AI Control Plane"],
            )
            logger.info("Mounted AI Control Plane APIs at /api/v1/control-plane")
        except Exception as e:
            logger.warning(f"Failed to mount Control Plane API: {e}")

    # Ontology VDL API (spec 041) — promoted from /control-plane/virtual/query
    try:
        from src.apis import ontology_vdl_api as _ontology_vdl_api
        app.include_router(_ontology_vdl_api.router)
        logger.info("Mounted Ontology VDL API at /api/v1/vdl")
    except Exception as e:
        logger.warning(f"Failed to mount Ontology VDL API: {e}")

    # Initialize Data Source Mode service (single source of truth for
    # simulator-vs-real routing). Constructed BEFORE FDW init so the
    # FDW API and tools can take a reference to the singleton.
    _data_source_mode_service = None
    try:
        from src.config.ssm_loader import SSMParameterLoader
        from src.services.data_source_mode_service import DataSourceModeService
        from src.apis import data_source_mode_api
        _ssm_loader_for_modes = SSMParameterLoader()
        _data_source_mode_service = DataSourceModeService(ssm_loader=_ssm_loader_for_modes)
        await _data_source_mode_service.initialize()
        data_source_mode_api.configure(_data_source_mode_service)
        app.include_router(data_source_mode_api.router)
        logger.info(
            f"Data Source Mode service initialized; modes={_data_source_mode_service.all_modes()}"
        )
    except Exception as e:
        logger.warning(f"Data Source Mode service init failed (non-fatal): {e}")

    # AI-OPs diagnostics history API (Phase 1). Middleware is registered
    # at module scope above (Starlette forbids middleware registration
    # after startup); only the read-back router is mounted here.
    try:
        from src.apis import diagnostics_history_api as _dh_api
        app.include_router(_dh_api.router)
        logger.info("Diagnostics history router mounted")
    except Exception as e:
        logger.warning(f"Diagnostics history mount failed (non-fatal): {e}")

    # AI Health Central API + background snapshotter (Phase 1).
    try:
        from src.apis import ai_health_api as _ah_api
        app.include_router(_ah_api.router)
        from src.services.ai_health_service import get_ai_health_service
        await get_ai_health_service().start()
        logger.info("AI Health router + snapshotter started")
    except Exception as e:
        logger.warning(f"AI Health init failed (non-fatal): {e}")

    # Virtual Data API Registry (Phase 2, data-organization spec).
    try:
        from src.apis import vdl_api as _vdl_api
        app.include_router(_vdl_api.router)
        from src.services.data_plane import vdl_api_executor as _vdl_exec
        from src.services.data_plane.vdl_api_registry_service import (
            get_vdl_api_registry,
        )
        from src.services.data_plane.vdl_api_seed_loader import load_seed_specs
        _vdl_exec.configure(app)
        _seed = load_seed_specs()
        if _seed:
            await get_vdl_api_registry().bootstrap_if_empty(_seed)
        logger.info(f"VDL API router mounted + {len(_seed)} seed specs loaded")
    except Exception as e:
        logger.warning(f"VDL API init failed (non-fatal): {e}")

    # Data Source Definition API (Phase 2, data-organization spec).
    try:
        from src.apis import data_source_api as _ds_api
        app.include_router(_ds_api.router)
        logger.info("Data Sources router mounted")
    except Exception as e:
        logger.warning(f"Data Sources router mount failed (non-fatal): {e}")

    # Onto-data bootstrap (Phase 3, data-organization spec).
    # Idempotent: seeds policies/workflows/integrations from disk only if
    # the DDB category is empty. Ensures DDB is the sole runtime source.
    try:
        from src.services.onto_data_service import OntoDataService as _OntoDataService
        _bootstrap_counts = _OntoDataService().bootstrap_if_empty()
        if any(_bootstrap_counts.values()):
            logger.info(f"Onto-data bootstrap seeded: {_bootstrap_counts}")
        else:
            logger.info("Onto-data bootstrap: DDB already populated, skipping seed")
    except Exception as e:
        logger.warning(f"Onto-data bootstrap failed (non-fatal): {e}")

    # Knowledge Pipeline registry (Phase 3.4, data-organization spec).
    try:
        from src.apis import knowledge_pipeline_api as _kp_api
        app.include_router(_kp_api.router)
        from src.services.control_plane.knowledge_pipeline_service import (
            get_knowledge_pipeline_service,
        )
        await get_knowledge_pipeline_service().bootstrap_defaults()
        logger.info("Knowledge Pipelines router mounted + defaults bootstrapped")
    except Exception as e:
        logger.warning(f"Knowledge Pipelines init failed (non-fatal): {e}")

    # Initialize FDW integration (if configured)
    if FDW_LIFECYCLE_AVAILABLE:
        try:
            fdw_enabled = await initialize_fdw()
            if fdw_enabled:
                logger.info("FDW integration initialized successfully")
            else:
                logger.info("FDW integration not configured - skipping")
        except Exception as e:
            logger.warning(f"FDW initialization failed: {e}")

    # Hand the resolver to the FDW API so default `?source=` routing
    # honours the per-source mode without breaking explicit overrides.
    if _data_source_mode_service is not None:
        try:
            from src.apis import fdw_api as _fdw_api_mod
            _fdw_api_mod.configure(
                connection_manager=_fdw_api_mod._connection_manager,
                discovery_service=_fdw_api_mod._discovery_service,
                query_service=_fdw_api_mod._query_service,
                mode_service=_data_source_mode_service,
            )
        except Exception as e:
            logger.warning(f"fdw_api mode wiring failed (non-fatal): {e}")

    # Initialize Data Plane service
    if DATA_PLANE_LIFECYCLE_AVAILABLE:
        try:
            await initialize_data_plane()
            logger.info("Data Plane service initialized successfully")
        except Exception as e:
            logger.warning(f"Data Plane initialization failed: {e}")

    # Initialize Mapping Rule service
    try:
        from src.services.mapping_rule_service import MappingRuleService
        from src.apis import mapping_rule_api
        _mapping_rule_service = MappingRuleService()
        await _mapping_rule_service.initialize()
        mapping_rule_api.configure(_mapping_rule_service)
        logger.info("Mapping Rule service initialized successfully")

        from src.services.virtual_query_service import VirtualQueryService
        from src.apis.control_plane_api import configure_virtual_query
        _vq_fdw_query = None
        _vq_fdw_discovery = None
        _vq_simulators = {}
        try:
            from src.apis.fdw_api import _query_service as _vq_fdw_query, _discovery_service as _vq_fdw_discovery, _simulators as _vq_simulators
        except Exception:
            pass

        _athena_service = None
        try:
            from src.services.athena_query_service import AthenaQueryService
            _athena_service = AthenaQueryService()
            logger.info("AthenaQueryService initialized for VDL")
        except Exception as ae:
            logger.warning(f"AthenaQueryService init failed (non-fatal): {ae}")

        _virtual_query_service = VirtualQueryService(
            _mapping_rule_service,
            _vq_fdw_query,
            _vq_fdw_discovery,
            simulators=_vq_simulators,
            athena_service=_athena_service,
            mode_service=_data_source_mode_service,
        )
        configure_virtual_query(_virtual_query_service)
        logger.info(
            f"Virtual Query service initialized successfully "
            f"(mode_service={'set' if _data_source_mode_service else 'none'})"
        )

        app_data_api.configure(_virtual_query_service)

        dashboard_query_api.configure(_virtual_query_service)

        from src.services.dashboard_service import DashboardService
        _dashboard_service = DashboardService()
        dashboard_api.configure(_dashboard_service)

        try:
            from src.services.solution_service import SolutionService
            from src.services.view_service import ViewService
            _solution_service = SolutionService()
            _view_service = ViewService()
            solution_api.configure(_solution_service)
            view_api.configure(_view_service)
            logger.info("Foundry workspace services initialized (Solutions, Views)")
        except Exception as fe:
            logger.warning(f"Foundry workspace services init failed (non-fatal): {fe}")

        try:
            from src.services.plugins.plugin_service import PluginService
            _plugin_service = PluginService(virtual_query_service=_virtual_query_service)
            plugin_api.configure(_plugin_service)
            logger.info("Plugin service initialized")
        except Exception as pe:
            logger.warning(f"Plugin service init failed (non-fatal): {pe}")

        # AI Automation Framework - structured Use Case index that drives the
        # Copilot's planning step (replaces today's "0 knowledge sources").
        # The control_plane RAG service is lazy-init via _ensure_init() so we
        # must trigger it explicitly here before reading _rag_service.
        _automation_indexer = None
        try:
            from src.services.control_plane.automation_indexer import AutomationIndexer
            from src.services.control_plane import connector_apis as _connector_apis
            from src.apis import control_plane_api as _cp_api
            try:
                await _cp_api._ensure_init()
            except Exception as init_err:
                logger.warning(f"control_plane _ensure_init failed: {init_err}")
            _cp_rag2 = getattr(_cp_api, "_rag_service", None)
            _cp_agent2 = getattr(_cp_api, "_agent_executor", None)
            _emb = getattr(_cp_rag2, "_embeddings", None) if _cp_rag2 else None
            _vec = getattr(_cp_rag2, "_vector", None) if _cp_rag2 else None

            # Solutions catalog: always mount list/CRUD (DDB-backed). NLP /search
            # needs the indexer wired below when pgvector is available.
            try:
                from src.services.solutions_yaml_service import (
                    get_solutions_yaml_service,
                )
                from src.apis import solutions_yaml_api as _sol_api
                await get_solutions_yaml_service().bootstrap_from_files()
                app.include_router(_sol_api.router)
                logger.info("Solutions catalog API mounted (DDB list/CRUD)")
            except Exception as sie:
                logger.warning(f"Solutions catalog mount failed (non-fatal): {sie}")

            if _emb is not None and _vec is not None:
                _tools_for_idx = _cp_agent2._tools if _cp_agent2 else None
                _automation_indexer = AutomationIndexer(
                    embedding_service=_emb, vector_store=_vec,
                    tool_registry=_tools_for_idx,
                    connector_apis_module=_connector_apis,
                )
                from src.apis import automation_api as _auto_api_mod
                from src.apis import automation_diagnostics_api as _auto_diag_mod
                _auto_api_mod.configure(_automation_indexer)
                _auto_diag_mod.configure(_automation_indexer)
                app.include_router(_auto_api_mod.router)
                app.include_router(_auto_diag_mod.router)
                # Run the indexer once (idempotent). Failures are non-fatal so
                # the Copilot still falls back to today's behaviour.
                try:
                    _idx_stats = await _automation_indexer.index_all()
                    logger.info(
                        f"Automation indexer: use_cases={_idx_stats.get('indexed_use_cases')} "
                        f"steps={_idx_stats.get('indexed_steps')} bindings={_idx_stats.get('indexed_tool_bindings')} "
                        f"missing_tools={len(_idx_stats.get('missing_tools') or [])} "
                        f"missing_apis={len(_idx_stats.get('missing_connector_apis') or [])}"
                    )
                except Exception as ide:
                    logger.warning(f"Automation indexer run failed (non-fatal): {ide}")

                # Wire NLP search indexer when pgvector is available.
                try:
                    from src.services.solutions_indexer import SolutionsIndexer
                    from src.apis import solutions_yaml_api as _sol_api
                    _solutions_indexer = SolutionsIndexer(
                        embedding_service=_emb,
                        vector_store=_vec,
                    )
                    await _solutions_indexer.index_all()
                    _sol_api.configure(_solutions_indexer)
                    logger.info("Solutions catalog NLP search indexer wired")
                except Exception as sie:
                    logger.warning(f"Solutions catalog indexer failed (non-fatal): {sie}")
            else:
                logger.warning(
                    "Automation indexer init: no embedding/vector service - skipped "
                    f"(rag={'set' if _cp_rag2 else 'none'} emb={'set' if _emb else 'none'} "
                    f"vec={'set' if _vec else 'none'})"
                )
        except Exception as aie:
            logger.warning(f"Automation indexer outer failure: {aie}", exc_info=True)

        try:
            from src.services.control_plane.copilot_engine import CopilotEngine
            from src.services.control_plane.copilot_session_store import CopilotSessionStore
            from src.services.control_plane.automation_kg import AutomationKnowledgeGraph
            from src.services.journey_store_service import JourneyStoreService
            from src.apis import control_plane_api as _cp_api2
            _cp_rag = getattr(_cp_api2, "_rag_service", None)
            _cp_agent = getattr(_cp_api2, "_agent_executor", None)
            _cp_tools = _cp_agent._tools if _cp_agent else None
            _vector_store = getattr(_cp_api2, "_vector_store", None) or (
                _cp_rag._vector if _cp_rag and hasattr(_cp_rag, "_vector") else None
            )
            _graph_store = getattr(_cp_api2, "_graph_store", None) or (
                _cp_rag._graph if _cp_rag and hasattr(_cp_rag, "_graph") else None
            )
            _session_store = CopilotSessionStore()
            await _session_store.initialize()
            try:
                _journey_store = JourneyStoreService()
            except Exception as je:
                logger.warning(f"Journey store init failed (non-fatal): {je}")
                _journey_store = None

            # JourneyExecutorBridge: lets Copilot-engine saved-journey
            # runs land in the existing transformation-system DDB so
            # /api/v1/journeys/{id}/jobs/{job_id}/logs + aggregate-report
            # surface them identically to regular Journeys. Best-effort:
            # if AWS creds / DDB are unreachable, the bridge becomes a
            # no-op (Copilot still works, the studio just shows empty
            # job history for that run).
            _journey_executor_bridge = None
            try:
                from src.utils.job_executor import TransformationJobExecutor
                from src.services.logs_and_reports_service import LogsAndReportsService
                from src.services.control_plane.journey_executor_bridge import (
                    JourneyExecutorBridge,
                )
                _txjob_executor = TransformationJobExecutor()
                try:
                    _logs_reports_svc = LogsAndReportsService()
                except Exception as _lse:
                    logger.warning(f"LogsAndReportsService init failed (non-fatal): {_lse}")
                    _logs_reports_svc = None
                _journey_executor_bridge = JourneyExecutorBridge(
                    executor=_txjob_executor,
                    logs_service=_logs_reports_svc,
                )
                if _journey_store is not None:
                    _journey_store.configure_executor_bridge(_journey_executor_bridge)
                globals()["_journey_executor_bridge"] = _journey_executor_bridge
                logger.info(
                    "JourneyExecutorBridge wired (Copilot Saved -> /api/v1/journeys logs)",
                )

                # Phase-3 (journey-specific reports): single generic
                # JourneyReportBuilder shared by every solution. Reads
                # report-schema YAML files under enterprise-knowledge/
                # report-schemas/{solution_id}.yaml and aggregates
                # Data.kpis across completed JobExecution rows.
                try:
                    from src.services.journey_report_catalog import (
                        ReportSchemaCatalog, set_catalog as _set_report_catalog,
                    )
                    from src.services.journey_report_builder import (
                        JourneyReportBuilder, set_report_builder,
                    )
                    _report_catalog = ReportSchemaCatalog()
                    _report_catalog.reload()
                    _set_report_catalog(_report_catalog)
                    set_report_builder(JourneyReportBuilder(
                        catalog=_report_catalog,
                        executor=_txjob_executor,
                    ))
                    logger.info(
                        "JourneyReportBuilder wired ({} schemas)".format(
                            len(_report_catalog.known_solutions()),
                        ),
                    )
                except Exception as _re:
                    logger.warning(
                        f"JourneyReportBuilder wire failed (non-fatal): {_re}",
                    )
            except Exception as _be:
                logger.warning(
                    f"JourneyExecutorBridge wire failed (non-fatal): {_be}",
                )
            try:
                from src.services.control_plane import connector_apis as _cp_apis_mod
            except Exception:
                _cp_apis_mod = None
            _automation_kg = AutomationKnowledgeGraph(
                vector_store=_vector_store,
                graph_store=_graph_store,
                automation_indexer=_automation_indexer,
                tool_registry=_cp_tools,
                connector_apis_module=_cp_apis_mod,
            )
            from src.services.ai_engine_client import AiEngineClient
            _ai_engine_client = AiEngineClient()
            globals()["_ai_engine_client"] = _ai_engine_client
            if _ai_engine_client.configured:
                logger.info("AI Engine client configured: {}", _ai_engine_client.url)
            else:
                logger.info("AI Engine client disabled — Copilot uses in-process execution")
            _copilot = CopilotEngine(
                rag_service=_cp_rag,
                tool_registry=_cp_tools,
                virtual_query_service=_virtual_query_service,
                automation_indexer=_automation_indexer,
                session_store=_session_store,
                automation_kg=_automation_kg,
                journey_executor_bridge=_journey_executor_bridge,
                ai_engine_client=_ai_engine_client,
            )
            copilot_journey_api.configure(_copilot, journey_store=_journey_store)
            try:
                from src.apis import automation_diagnostics_api as _auto_diag_mod2
                _auto_diag_mod2.configure(
                    _automation_indexer,
                    automation_kg=_automation_kg,
                    journey_store=_journey_store,
                    copilot_engine=_copilot,
                    vector_store=_vector_store,
                    session_store=_session_store,
                )
            except Exception as ade:
                logger.warning(f"Automation diagnostics rewire failed (non-fatal): {ade}")
            try:
                from src.apis import react_tools_diagnostics_api as _rtd_api
                _rtd_api.configure(
                    _cp_tools,
                    connector_apis=_connector_apis,
                    automation_indexer=_automation_indexer,
                )
                app.include_router(_rtd_api.router)
                logger.info("ReAct Tools diagnostics router mounted")
            except Exception as rte:
                logger.warning(f"ReAct Tools diagnostics wire failed (non-fatal): {rte}")
            try:
                from src.apis import connector_api_workbench_api as _wb_api
                _wb_api.configure(app=app, tool_registry=_cp_tools)
                app.include_router(_wb_api.router)
                logger.info("Connector API Workbench router mounted")
            except Exception as we:
                logger.warning(f"Connector API Workbench wire failed (non-fatal): {we}")
            try:
                from src.apis import ontology_connectors_api as _ontology_conn_api
                app.include_router(_ontology_conn_api.router)
                logger.info("Mounted Ontology Connectors API at /api/v1/connectors")
            except Exception as oce:
                logger.warning(f"Ontology Connectors API mount failed (non-fatal): {oce}")
            try:
                from src.services.control_plane.yaml_journey_runner import YamlJourneyRunner
                from src.apis import yaml_journey_api as _yj_api
                _yaml_journey_runner = YamlJourneyRunner(
                    tool_registry=_cp_tools,
                    session_store=_session_store,
                    connector_apis=_connector_apis,
                )
                _yj_api.configure(_yaml_journey_runner)
                app.include_router(_yj_api.router)
                globals()["_yaml_journey_runner"] = _yaml_journey_runner
                logger.info("YAML Journey runner mounted")
                # Re-configure the copilot-journey router so the
                # /journey-builder/* endpoints can dispatch through the
                # YAML runner + call JourneyDoc.validate_strict against
                # the live ToolRegistry + connector_apis catalogue.
                try:
                    copilot_journey_api.configure(
                        _copilot,
                        journey_store=_journey_store,
                        yaml_journey_runner=_yaml_journey_runner,
                        tool_registry=_cp_tools,
                        connector_apis=_connector_apis,
                    )
                except Exception as cje:
                    logger.warning(f"copilot_journey_api re-configure failed (non-fatal): {cje}")
            except Exception as yje:
                logger.warning(f"YAML Journey runner wire failed (non-fatal): {yje}")
            # Phase 1 -- registry buckets API (read-only listing + per-bucket detail).
            # Mounted here (not in mount_api_routes) because _cp_tools is
            # only populated during startup_event after the Copilot agent
            # is instantiated -- mount_api_routes runs earlier and saw NameError.
            try:
                from src.apis import buckets_api as _buckets_api_mod
                _buckets_api_mod.configure(tool_registry=_cp_tools)
                app.include_router(_buckets_api_mod.router)
                logger.info("Mounted Buckets APIs at /api/v1/control-plane/buckets")
            except Exception as e:
                logger.warning(f"Buckets API mount failed (non-fatal): {e}")
            # Phase 6 (Data Queues) -- diagnostics endpoints + queue manager wiring.
            # Same reason as buckets: _yaml_journey_runner only exists now.
            try:
                from src.apis import data_queues_api as _data_queues_mod
                queue_mgr = getattr(_yaml_journey_runner, "_data_queue", None)
                if queue_mgr is None:
                    from src.services.control_plane.data_queue import make_data_queue_manager
                    queue_mgr = make_data_queue_manager()
                _data_queues_mod.configure(queue_manager=queue_mgr)
                app.include_router(_data_queues_mod.router)
                logger.info("Mounted Data Queues APIs at /api/v1/control-plane/runs/{id}/queues")
            except Exception as e:
                logger.warning(f"Data Queues API mount failed (non-fatal): {e}")
            try:
                from src.apis import control_plane_api as _cp_api3
                from src.apis import tools_builder_api as _tb_api
                from src.services.control_plane.tool_registry_sync import ToolRegistrySync
                _cp_store = getattr(_cp_api3, "_tool_store", None)
                _cp_loader = getattr(_cp_api3, "_dynamic_tool_loader", None)
                _tb_api.configure(
                    store=_cp_store,
                    loader=_cp_loader,
                    registry=_cp_tools,
                )
                app.include_router(_tb_api.router)
                logger.info("Tool Builder router mounted")
                if _cp_store is not None and _cp_loader is not None and _cp_tools is not None:
                    _registry_sync = ToolRegistrySync(
                        registry=_cp_tools,
                        store=_cp_store,
                        loader=_cp_loader,
                        poll_interval_s=int(os.environ.get("TOOL_REGISTRY_POLL_S", "60")),
                    )
                    _registry_sync.start()
                    globals()["_tool_registry_sync"] = _registry_sync
            except Exception as tbe:
                logger.warning(f"Tool Builder wire failed (non-fatal): {tbe}")
            # Phase 3.3 (data-organization spec) - project the fully-populated
            # in-memory ToolRegistry into DDB TOOLREG# rows and mount the
            # DDB-backed read API. Idempotent; failures are non-fatal.
            try:
                from src.apis import tools_registry_api as _tr_api
                from src.services.control_plane.tools_registry_service import (
                    get_tools_registry_service,
                )
                if _cp_tools is not None:
                    _tr_api.configure(_cp_tools)
                    app.include_router(_tr_api.router)
                    await get_tools_registry_service().sync_from_in_memory(_cp_tools)
                    logger.info("Tools Registry (TOOLREG#) synced + router mounted")
            except Exception as tre:
                logger.warning(f"Tools Registry sync/mount failed (non-fatal): {tre}")

            logger.info(
                f"Copilot engine initialized "
                f"(rag={'set' if _cp_rag else 'none'} tools={len(_cp_tools.list_tools()) if _cp_tools else 0} "
                f"automation_indexer={'set' if _automation_indexer else 'none'} "
                f"session_store={'redis' if _session_store._use_redis else ('pg' if _session_store._use_pg else 'memory')} "
                f"journey_store={'set' if _journey_store else 'none'})"
            )
        except Exception as ce:
            logger.warning(f"Copilot engine init failed (non-fatal): {ce}")

        # Dashboard Diagnostics - service that runs panel queries through the
        # live VDL stack and grades the result against a fixed checklist.
        try:
            from src.services.dashboard_diagnostics_service import DashboardDiagnosticsService
            from src.services.mimir_client import get_default_mimir_client
            from src.apis import dashboard_diagnostics_api as _dd_api
            _dashboard_diag_service = DashboardDiagnosticsService(
                dashboard_service=_dashboard_service,
                mapping_rule_service=_mapping_rule_service,
                virtual_query_service=_virtual_query_service,
                simulators=_vq_simulators,
                mimir_client=get_default_mimir_client(),
                athena_service=_athena_service,
            )
            _dd_api.configure(_dashboard_diag_service)
            app.include_router(_dd_api.router)
            logger.info("Dashboard diagnostics service initialized")
        except Exception as dde:
            logger.warning(f"Dashboard diagnostics init failed (non-fatal): {dde}")

        # Virtual Data Diagnostics - probes every mapped virtual entity
        # through the same VDL path the Data Plane preview uses and
        # surfaces layer-by-layer failures (no rule, inactive rule,
        # unknown source schema, simulator not loaded, missing field
        # maps, query error, zero rows, etc.).
        try:
            from src.services.virtual_data_diagnostics_service import VirtualDataDiagnosticsService
            from src.apis import virtual_data_diagnostics_api as _vd_api
            from src.services.mimir_client import get_default_mimir_client as _vd_mimir
            _vd_diag_service = VirtualDataDiagnosticsService(
                mapping_rule_service=_mapping_rule_service,
                virtual_query_service=_virtual_query_service,
                fdw_discovery=_vq_fdw_discovery,
                simulators=_vq_simulators,
                athena_service=_athena_service,
                mimir_client=_vd_mimir(),
            )
            _vd_api.configure(_vd_diag_service)
            app.include_router(_vd_api.router)
            logger.info("Virtual data diagnostics service initialized")
        except Exception as vde:
            logger.warning(f"Virtual data diagnostics init failed (non-fatal): {vde}")

        # Solution Four Views - one-shot seeding of mapping rules, 32 views,
        # and demo data so dashboards show populated panels on first load.
        # SOLUTION_STORAGE_MODE controls routing (simulator | production).
        # SOLUTION_FORCE_SEED=true forces a re-seed of mapping rules and data.
        #
        # `ensure_solution_entities` is kept inline (fast, ~1s; creates the
        # mapping rules dashboards need to query). `ensure_solution_views`
        # and `seed_demo_data` are offloaded to a background task because
        # they walk every dashboard / write thousands of rows into the
        # simulator and have been observed to push startup past the
        # kubelet liveness window in earlier deploys, leading to the pod
        # being killed mid-seed and dashboards staying empty.
        try:
            import os as _os
            import asyncio as _asyncio
            from src.services.solution_entity_catalogue import ensure_solution_entities
            from src.services.solution_view_seed import ensure_solution_views
            from src.services.solution_demo_seed import seed_demo_data

            force_seed = _os.environ.get("SOLUTION_FORCE_SEED", "").lower() == "true"

            ent_summary = await ensure_solution_entities(
                mapping_service=_mapping_rule_service,
                force_recreate=force_seed,
            )
            logger.info(
                f"Solution entity catalogue ensured inline: "
                f"created={ent_summary.get('created')} skipped={ent_summary.get('skipped')} "
                f"errors={ent_summary.get('errors')}"
            )

            if _os.environ.get("CANONICAL_MAPPING_SEED", "true").lower() != "false":
                from src.services.canonical_mapping_seeder import ensure_canonical_mapping_rules

                canon_summary = await ensure_canonical_mapping_rules(
                    mapping_service=_mapping_rule_service,
                    simulators=_vq_simulators,
                    force_recreate=force_seed,
                )
                logger.info(
                    "Canonical VDL mapping rules ensured: "
                    f"created={canon_summary.get('created')} skipped={canon_summary.get('skipped')} "
                    f"no_source={canon_summary.get('no_source_table')} errors={canon_summary.get('errors')}"
                )

            async def _seed_views_and_data_bg():
                try:
                    view_summary = await ensure_solution_views(
                        dashboard_service=_dashboard_service,
                        view_service=_view_service,
                        solution_service=_solution_service,
                    )
                    data_summary = await seed_demo_data(force=force_seed)
                    logger.info(
                        f"Solution Four Views background seed complete: "
                        f"views status={view_summary.get('status')} apps={len(view_summary.get('apps', {}))}, "
                        f"demo data status={data_summary.get('status')} "
                        f"seeded_apps={len(data_summary.get('apps', {})) - len(data_summary.get('skipped', []))}"
                    )
                except Exception as bg_e:
                    logger.warning(
                        f"Solution Four Views background seed failed (non-fatal): {bg_e}",
                        exc_info=True,
                    )

            _asyncio.create_task(_seed_views_and_data_bg())
            logger.info("Solution Four Views view+data seed scheduled in background")
        except Exception as fve:
            logger.warning(f"Solution Four Views seed scheduling failed (non-fatal): {fve}", exc_info=True)
    except Exception as e:
        logger.warning(f"Mapping Rule initialization failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of worker pool and scheduler"""
    # Stop batch scheduler
    try:
        from src.services.scheduler_service import SchedulerService
        scheduler = SchedulerService.get_instance()
        await scheduler.stop()
    except Exception as e:
        logger.warning(f"Scheduler shutdown error: {e}")

    # Shutdown FDW integration
    if FDW_LIFECYCLE_AVAILABLE:
        try:
            await shutdown_fdw()
        except Exception as e:
            logger.warning(f"FDW shutdown error: {e}")

    # Shutdown Data Plane service
    if DATA_PLANE_LIFECYCLE_AVAILABLE:
        try:
            await shutdown_data_plane()
        except Exception as e:
            logger.warning(f"Data Plane shutdown error: {e}")

    await pool.stop()
    logger.info("Gateway shutdown complete")

# ------------ HTTP ENDPOINTS ------------

@app.get("/")
async def root():
    """Root endpoint with server information including LocalStack status."""
    # Build LocalStack status info
    localstack_info = {"enabled": False}
    if HAS_LOCALSTACK_CONFIG and is_localstack_enabled():
        config = get_localstack_config()
        localstack_info = {
            "enabled": True,
            "endpoint": config.endpoint_url,
            "region": config.region
        }
    
    return {
        "service": "AI Job Engine Unified Gateway",
        "version": "3.0.0",
        "protocol": ["mcp", "rest"],
        "transport": ["http", "websocket", "sse"],
        "streaming": True,
        "apis_enabled": API_MODULES_AVAILABLE,
        "localstack": localstack_info,
        "workers": pool.get_stats(),
        "endpoints": {
            "mcp_tools": "/tools/*",
            "rest_apis": "/api/v1/*" if API_MODULES_AVAILABLE else None,
            "websocket": "/ws/tools/*",
            "localstack_health": "/health/localstack",
            "documentation": "/docs"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health():
    """Health check with worker pool status"""
    stats = pool.get_stats()
    return {
        "status": "healthy" if stats["total_workers"] > 0 else "unhealthy",
        "workers": stats,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ready")
@app.get("/readiness")
async def readiness():
    """
    Readiness probe - indicates if the service is ready to accept traffic.
    
    Returns 200 if:
    - Worker pool has at least one worker available
    - Workers are initialized and responding
    
    Used by Kubernetes/container orchestrators for readiness probes.
    """
    stats = pool.get_stats()
    total_workers = stats.get("total_workers", 0)
    busy_workers = stats.get("busy_workers", 0)
    available_workers = total_workers - busy_workers
    
    if total_workers > 0:
        return {
            "ready": True,
            "status": "ready",
            "total_workers": total_workers,
            "available_workers": available_workers,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "status": "not_ready",
                "reason": "No workers available",
                "total_workers": 0,
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/live")
@app.get("/liveness")
async def liveness():
    """
    Liveness probe - indicates if the service is alive and should not be restarted.
    
    Returns 200 if the application process is running and responsive.
    This is a lightweight check that doesn't verify all dependencies.
    
    Used by Kubernetes/container orchestrators for liveness probes.
    """
    return {
        "alive": True,
        "status": "alive",
        "service": "AI Job Engine Gateway",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus text format including:
    - Worker pool statistics
    - Request counts
    - Error rates
    - System health indicators
    """
    stats = pool.get_stats()
    
    # Build Prometheus format metrics
    lines = [
        "# HELP mcp_gateway_workers_total Total number of MCP workers",
        "# TYPE mcp_gateway_workers_total gauge",
        f"mcp_gateway_workers_total {stats.get('total_workers', 0)}",
        "",
        "# HELP mcp_gateway_workers_busy Number of busy MCP workers",
        "# TYPE mcp_gateway_workers_busy gauge",
        f"mcp_gateway_workers_busy {stats.get('busy_workers', 0)}",
        "",
        "# HELP mcp_gateway_requests_total Total requests processed by all workers",
        "# TYPE mcp_gateway_requests_total counter",
        f"mcp_gateway_requests_total {stats.get('total_requests', 0)}",
        "",
        "# HELP mcp_gateway_errors_total Total errors across all workers",
        "# TYPE mcp_gateway_errors_total counter",
        f"mcp_gateway_errors_total {stats.get('total_errors', 0)}",
        "",
        "# HELP mcp_gateway_up Whether the gateway is up (1) or down (0)",
        "# TYPE mcp_gateway_up gauge",
        f"mcp_gateway_up {1 if stats.get('total_workers', 0) > 0 else 0}",
        "",
    ]
    
    # Add per-worker metrics
    for worker in stats.get('worker_details', []):
        worker_id = worker.get('id', 0)
        lines.extend([
            f"# HELP mcp_worker_requests Worker request count",
            f"# TYPE mcp_worker_requests counter",
            f'mcp_worker_requests{{worker_id="{worker_id}"}} {worker.get("requests", 0)}',
            f'mcp_worker_errors{{worker_id="{worker_id}"}} {worker.get("errors", 0)}',
            f'mcp_worker_busy{{worker_id="{worker_id}"}} {1 if worker.get("busy") else 0}',
        ])
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/plain; charset=utf-8"
    )


@app.get("/health/localstack")
async def localstack_health():
    """
    Check LocalStack connectivity and service status.
    
    Returns detailed information about LocalStack availability including:
    - Whether LocalStack mode is enabled
    - Connection status to LocalStack endpoint
    - Individual service status (DynamoDB, S3, CloudWatch)
    - Troubleshooting guidance if unhealthy
    """
    # Check if LocalStack config is available
    if not HAS_LOCALSTACK_CONFIG:
        return {
            "status": "unavailable",
            "message": "LocalStack configuration module not available",
            "timestamp": datetime.now().isoformat()
        }
    
    # Check if LocalStack mode is enabled
    if not is_localstack_enabled():
        return {
            "status": "disabled",
            "message": "LocalStack mode is not enabled",
            "hint": "Set USE_LOCALSTACK=true in .env.local to enable LocalStack mode",
            "timestamp": datetime.now().isoformat()
        }
    
    config = get_localstack_config()
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{config.endpoint_url}/_localstack/health")
            
            if response.status_code == 200:
                health_data = response.json()
                services = health_data.get("services", {})
                return {
                    "status": "healthy",
                    "endpoint": config.endpoint_url,
                    "region": config.region,
                    "services": {
                        "dynamodb": services.get("dynamodb", "unknown"),
                        "s3": services.get("s3", "unknown"),
                        "cloudwatch": services.get("cloudwatch", "unknown"),
                        "sts": services.get("sts", "unknown")
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "endpoint": config.endpoint_url,
                    "error": f"Health check returned HTTP {response.status_code}",
                    "troubleshooting": [
                        "Check if LocalStack container is running: docker ps | grep localstack",
                        "View LocalStack logs: docker logs nexus-localstack",
                        "Restart LocalStack: ./scripts/start-localstack.sh (Linux) or .\\scripts\\start-localstack.ps1 (Windows)"
                    ],
                    "timestamp": datetime.now().isoformat()
                }
    except httpx.ConnectError as e:
        return {
            "status": "unreachable",
            "endpoint": config.endpoint_url,
            "error": f"Connection refused: {str(e)}",
            "troubleshooting": [
                "Ensure LocalStack is running: docker ps | grep localstack",
                f"Verify endpoint URL: curl {config.endpoint_url}/_localstack/health",
                "Check LOCALSTACK_HOST and LOCALSTACK_PORT in .env.local",
                "Start LocalStack: ./scripts/start-localstack.sh (Linux) or .\\scripts\\start-localstack.ps1 (Windows)"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "endpoint": config.endpoint_url,
            "error": "Connection timed out after 5 seconds",
            "troubleshooting": [
                "LocalStack may be starting up - wait a few seconds and retry",
                "Check LocalStack container health: docker inspect nexus-localstack",
                "View LocalStack logs: docker logs nexus-localstack"
            ],
            "timestamp": datetime.now().isoformat()
        }
    except ImportError:
        # httpx not installed, try with requests
        try:
            import requests
            response = requests.get(f"{config.endpoint_url}/_localstack/health", timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                services = health_data.get("services", {})
                return {
                    "status": "healthy",
                    "endpoint": config.endpoint_url,
                    "region": config.region,
                    "services": {
                        "dynamodb": services.get("dynamodb", "unknown"),
                        "s3": services.get("s3", "unknown"),
                        "cloudwatch": services.get("cloudwatch", "unknown"),
                        "sts": services.get("sts", "unknown")
                    },
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "status": "unhealthy",
                    "endpoint": config.endpoint_url,
                    "error": f"Health check returned HTTP {response.status_code}",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "endpoint": config.endpoint_url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "status": "error",
            "endpoint": config.endpoint_url,
            "error": str(e),
            "troubleshooting": [
                "Check LocalStack container status: docker ps",
                "View LocalStack logs: docker logs nexus-localstack"
            ],
            "timestamp": datetime.now().isoformat()
        }


@app.post("/admin/refresh-aws-credentials", dependencies=[Depends(verify_api_key)])
async def refresh_aws_credentials():
    """
    Refresh AWS credentials without restarting the gateway.
    
    This is useful when base credentials have been refreshed externally (e.g., via aws-login.sh)
    and you want the gateway to pick up the new credentials.
    
    Requires API key authentication.
    """
    try:
        from src.utils.aws_client_utils import refresh_default_credentials
        
        logger.info("Received request to refresh AWS credentials")
        success = refresh_default_credentials()
        
        if success:
            return {
                "status": "success",
                "message": "AWS credentials refreshed successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "Failed to refresh AWS credentials - check logs for details",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error refreshing AWS credentials: {str(e)}")
        return {
            "status": "error",
            "message": f"Failed to refresh AWS credentials: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@app.post("/mcp", dependencies=[Depends(verify_api_key)])
async def raw_mcp(envelope: MCPEnvelope):
    """
    Low-level endpoint: send raw MCP JSON-RPC payload
    """
    worker = await pool.get_worker()
    resp = await worker.send_one(envelope.payload, timeout=MCP_REQUEST_TIMEOUT)
    return JSONResponse(resp)

@app.get("/tools", dependencies=[Depends(verify_api_key)])
async def list_tools():
    """List available MCP tools"""
    worker = await pool.get_worker()
    
    message = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "tools/list",
        "params": {}
    }
    
    resp = await worker.send_one(message, timeout=30.0)
    
    if "error" in resp:
        raise HTTPException(status_code=500, detail=resp["error"])
        
    return resp.get("result", {})

@app.post("/tools/{tool_name}", dependencies=[Depends(verify_api_key)])
async def call_tool(tool_name: str, req: ToolCallRequest):
    """
    High-level endpoint: call a tool by name
    """
    worker = await pool.get_worker()
    
    message = {
        "jsonrpc": "2.0",
        "id": req.id or str(uuid4()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": req.arguments,
        },
    }
    
    resp = await worker.send_one(message, timeout=MCP_REQUEST_TIMEOUT)
    
    if "error" in resp:
        raise HTTPException(status_code=400, detail=resp["error"])
        
    return resp.get("result", {})

# ------------ SSE STREAMING ------------

@app.post("/tools/{tool_name}/stream", dependencies=[Depends(verify_api_key)])
async def stream_tool(tool_name: str, req: ToolCallRequest):
    """
    Server-Sent Events endpoint for streaming tool responses
    """
    async def event_generator():
        worker = await pool.get_worker()
        
        message = {
            "jsonrpc": "2.0",
            "id": req.id or str(uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": req.arguments,
                "stream": True  # Request streaming mode
            },
        }
        
        # Send request
        line = json.dumps(message) + "\n"
        
        async with worker.lock:
            worker.busy = True
            worker.last_used = datetime.now()
            worker.request_count += 1
            
            try:
                worker.proc.stdin.write(line.encode("utf-8"))
                await worker.proc.stdin.drain()
                
                # Stream responses as SSE
                while True:
                    try:
                        resp_line = await asyncio.wait_for(
                            worker.proc.stdout.readline(), 
                            timeout=MCP_REQUEST_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        yield f"event: error\ndata: {json.dumps({'error': 'timeout'})}\n\n"
                        break
                        
                    if not resp_line:
                        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
                        break
                        
                    try:
                        payload = json.loads(resp_line.decode("utf-8"))
                        
                        if "result" in payload:
                            yield f"event: result\ndata: {json.dumps(payload['result'])}\n\n"
                            break
                        elif "progress" in payload:
                            yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                        else:
                            yield f"event: chunk\ndata: {json.dumps(payload)}\n\n"
                            
                    except Exception as e:
                        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                        
            finally:
                worker.busy = False
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# ------------ WEBSOCKET STREAMING ------------

@app.websocket("/ws/tools/{tool_name}")
async def ws_tool_stream(websocket: WebSocket, tool_name: str):
    """
    WebSocket endpoint for bidirectional streaming with tools
    """
    # Authenticate via query param
    api_key = websocket.query_params.get("api_key")
    if api_key != API_KEY:
        await websocket.close(code=4401, reason="Unauthorized")
        return
        
    await websocket.accept()
    
    try:
        # Receive tool arguments
        init_msg = await websocket.receive_json()
        arguments = init_msg.get("arguments", {})
        req_id = init_msg.get("id") or str(uuid4())
        
        # Send acknowledgment
        await websocket.send_json({
            "event": "started",
            "id": req_id,
            "tool": tool_name
        })
        
        worker = await pool.get_worker()
        
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }
        
        # Stream from MCP to WebSocket
        await worker.stream(message, websocket, timeout=MCP_REQUEST_TIMEOUT)
        
        # Send completion
        await websocket.send_json({
            "event": "complete",
            "id": req_id
        })
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from {tool_name}")
    except Exception as e:
        logger.exception(f"WebSocket error for {tool_name}")
        try:
            await websocket.send_json({
                "event": "error",
                "error": str(e)
            })
        except:
            pass
        await websocket.close()

@app.get("/stats", dependencies=[Depends(verify_api_key)])
async def get_stats():
    """Get detailed worker pool statistics"""
    return pool.get_stats()

# ------------ API ROUTE MOUNTING ------------

def mount_api_routes():
    """
    Mount REST API routes for direct HTTP endpoints
    These bypass the MCP worker pool for low-latency operations
    """
    try:
        # Journey Management APIs
        app.include_router(
            journey_api.router,
            prefix="/api/v1/journeys",
            tags=["Journey Management"],
            responses={401: {"description": "Unauthorized"}}
        )
        logger.info("Mounted Journey Management APIs at /api/v1/journeys")
        
        # Analytics APIs
        app.include_router(
            analytics_api.router,
            prefix="/api/v1/analytics",
            tags=["Analytics"],
            responses={401: {"description": "Unauthorized"}}
        )
        logger.info("Mounted Analytics APIs at /api/v1/analytics")
        
        # Authentication APIs
        # Try Cognito auth first, fall back to mock auth if it fails
        try:
            from src.apis import cognito_auth_api
            app.include_router(
                cognito_auth_api.router,
                tags=["Authentication"],
                responses={401: {"description": "Unauthorized"}}
            )
            logger.info("✅ Mounted Cognito Authentication APIs at /api/v1/auth")
        except Exception as e:
            logger.warning(f"⚠️ Cognito auth unavailable, using mock auth: {e}")
            app.include_router(
                auth_api.router,
                prefix="/api/v1/auth",
                tags=["Authentication"],
                responses={401: {"description": "Unauthorized"}}
            )
            logger.info("Mounted Mock Authentication APIs at /api/v1/auth")
        
        # Health Check APIs
        app.include_router(
            health_api.router,
            prefix="/api/v1/health",
            tags=["Health"],
            responses={503: {"description": "Service Unavailable"}}
        )
        logger.info("Mounted Health Check APIs at /api/v1/health")

        app.include_router(plugin_api.router)
        logger.info("Mounted Plugin Registry APIs at /api/v1/plugins")

        app.include_router(copilot_journey_api.router, prefix="/api/v1/control-plane")
        logger.info("Mounted Copilot Journey APIs at /api/v1/control-plane/copilot-journey")

        # NOTE: the buckets + data-queues routers were originally mounted
        # here, but their deps (_cp_tools, _yaml_journey_runner) only get
        # initialised later inside startup_event() -- so at the time
        # mount_api_routes() runs they raise NameError and the routes
        # silently fail to register. The actual mount now lives in
        # startup_event() directly after the YAML journey runner is
        # wired up; see the matching block there.

        app.include_router(app_data_api.router)
        logger.info("Mounted App Data APIs at /api/v1/apps")

        app.include_router(dashboard_api.router)
        logger.info("Mounted Dashboard CRUD APIs at /api/v1/dashboards")

        app.include_router(dashboard_query_api.router)
        logger.info("Mounted Dashboard Query APIs at /api/v1/dashboard")

        app.include_router(solution_api.router)
        logger.info("Mounted Solution APIs at /api/v1/solutions")

        app.include_router(view_api.router)
        logger.info("Mounted View APIs at /api/v1/views")
        
        # Call Processing Diagnostics APIs
        app.include_router(
            diagnostics_api.router,
            prefix="/api/v1/diagnostics",
            tags=["Call Processing Diagnostics"],
            responses={401: {"description": "Unauthorized"}, 500: {"description": "Diagnostic Error"}}
        )
        logger.info("Mounted Call Processing Diagnostics APIs at /api/v1/diagnostics")
        
        # Test Suite Management APIs
        app.include_router(
            tests_api.router,
            prefix="/api/v1/tests",
            tags=["Test Suite Management"],
            responses={401: {"description": "Unauthorized"}, 502: {"description": "GitHub API Error"}}
        )
        logger.info("Mounted Test Suite Management APIs at /api/v1/tests")
        
        # FDW Discovery/Query APIs
        if FDW_API_AVAILABLE:
            app.include_router(
                fdw_api.router,
                tags=["FDW"],
                responses={503: {"description": "FDW Not Configured"}}
            )
            logger.info("Mounted FDW APIs at /api/fdw")

        # Data Plane APIs
        try:
            from src.apis import data_plane_api
            app.include_router(
                data_plane_api.router,
                tags=["Data Planes"],
            )
            logger.info("Mounted Data Plane APIs at /api/data-planes")
        except Exception as e:
            logger.warning(f"Failed to mount Data Plane APIs: {e}")

        try:
            from src.apis import mapping_rule_api
            app.include_router(
                mapping_rule_api.router,
                tags=["Mapping Rules"],
            )
            logger.info("Mounted Mapping Rule APIs at /api/v1/mapping-rules")
        except Exception as e:
            logger.warning(f"Failed to mount Mapping Rule APIs: {e}")
        
    except Exception as e:
        logger.error(f"Failed to mount API routes: {e}")
        raise


def mount_config_api():
    """
    Mount Configuration API routes independently.
    Provides runtime configuration management (log levels, environment info).
    """
    try:
        # Configuration APIs (log level, environment info)
        app.include_router(
            config_api.router,
            prefix="/api/v1/config",
            tags=["Configuration"],
            responses={401: {"description": "Unauthorized"}}
        )
        logger.info("Mounted Configuration APIs at /api/v1/config")
        
    except Exception as e:
        logger.error(f"Failed to mount Configuration APIs: {e}")


def mount_rbac_api():
    """
    Mount RBAC (Role-Based Access Control) API routes independently.
    Provides endpoints for managing roles, permissions, and their mappings.
    """
    try:
        from src.apis import rbac_api
        app.include_router(
            rbac_api.router,
            tags=["RBAC Management"],
            responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}}
        )
        logger.info("Mounted RBAC Management APIs at /api/v1/rbac")
        
    except Exception as e:
        logger.error(f"Failed to mount RBAC APIs: {e}")
        raise


# ------------ DB DOCTOR API ENDPOINTS ------------

class DiagnoseRequest(BaseModel):
    """Request model for database diagnosis"""
    bucket: Optional[str] = None
    database_name: Optional[str] = None
    table_name: Optional[str] = None


class RepairRequest(BaseModel):
    """Request model for database repair"""
    operations: List[str]
    missing_partitions: Optional[List[Dict[str, Any]]] = None


class QueryRequest(BaseModel):
    """Request model for call database query (SELECT only)"""
    query: str


@app.post("/api/v1/db-doctor/diagnose", dependencies=[Depends(verify_api_key)])
async def diagnose_database(request: DiagnoseRequest = None):
    """
    Run diagnostics on the Glue Call Database.
    Scans S3 and compares with Glue catalog to identify issues.
    """
    try:
        from src.services.db_doctor_service import DbDoctorService
        
        kwargs = {}
        if request:
            if request.bucket:
                kwargs['bucket'] = request.bucket
            if request.database_name:
                kwargs['database_name'] = request.database_name
            if request.table_name:
                kwargs['table_name'] = request.table_name
        
        doctor = DbDoctorService(**kwargs)
        report = doctor.diagnose()
        
        return JSONResponse(content=report.to_dict())
        
    except ImportError as e:
        logger.error(f"DB Doctor service not available: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DB Doctor service not available", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Diagnosis failed", "message": str(e)}
        )


@app.post("/api/v1/db-doctor/repair", dependencies=[Depends(verify_api_key)])
async def repair_database(request: RepairRequest):
    """
    Execute repair operations on the database.
    Can add missing partitions, remove orphaned partitions, or rebuild the entire table.
    """
    try:
        from src.services.db_doctor_service import DbDoctorService, PartitionInfo
        
        doctor = DbDoctorService()
        
        if "rebuild_table" in request.operations:
            result = doctor.rebuild_table()
        elif "remove_orphaned_partitions" in request.operations:
            if not request.missing_partitions:  # Reusing field for orphaned partitions
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Orphaned partitions required for remove_orphaned_partitions operation"}
                )
            
            # Convert dict to PartitionInfo objects
            partitions = [
                PartitionInfo(
                    year=p['year'],
                    month=p['month'],
                    day=p['day'],
                    hour=p['hour'],
                    s3_location=p['s3_location'],
                    in_catalog=p.get('in_catalog', False),
                    file_count=p.get('file_count', 0)
                )
                for p in request.missing_partitions
            ]
            
            result = doctor.remove_orphaned_partitions(partitions)
        elif "add_partitions" in request.operations:
            if not request.missing_partitions:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Missing partitions required for add_partitions operation"}
                )
            
            # Convert dict to PartitionInfo objects
            partitions = [
                PartitionInfo(
                    year=p['year'],
                    month=p['month'],
                    day=p['day'],
                    hour=p['hour'],
                    s3_location=p['s3_location'],
                    in_catalog=p.get('in_catalog', False),
                    file_count=p.get('file_count', 0)
                )
                for p in request.missing_partitions
            ]
            
            result = doctor.repair_partitions(partitions)
        else:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid operation", "valid_operations": ["add_partitions", "remove_orphaned_partitions", "rebuild_table"]}
            )
        
        return JSONResponse(content=result.to_dict())
        
    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"DB Doctor service not available: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DB Doctor service not available", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Repair failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Repair failed", "message": str(e)}
        )


@app.post("/api/v1/db-doctor/query", dependencies=[Depends(verify_api_key)])
async def execute_call_database_query(request: QueryRequest):
    """
    Execute a SELECT query against the Glue call table via Athena.
    Only SELECT is allowed; query must reference the configured database and table.
    Results are capped at 1000 rows.
    """
    try:
        from src.services.db_doctor_service import DbDoctorService
        doctor = DbDoctorService()
        result = doctor.execute_query(request.query)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"DB Doctor service not available: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DB Doctor service not available", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Query failed", "message": str(e)}
        )


@app.get("/api/v1/db-doctor/status", dependencies=[Depends(verify_api_key)])
async def get_db_doctor_status():
    """
    Get current DB Doctor operation status.
    """
    try:
        from src.services.db_doctor_service import DbDoctorService
        
        doctor = DbDoctorService()
        status = doctor.get_status()
        
        return JSONResponse(content=status)
        
    except ImportError as e:
        logger.error(f"DB Doctor service not available: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "DB Doctor service not available", "message": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to get status", "message": str(e)}
        )


def mount_license_api():
    """
    Mount License API routes independently.
    This is separate from mount_api_routes() because the license API
    doesn't require the jose module that other APIs depend on.
    """
    try:
        from src.license.services.license_service import LicenseService
        from src.license.services.audit_service import AuditService
        
        # Initialize services (uses default dev keypair from keys.py)
        license_service = LicenseService()
        audit_service = AuditService()
        license_api.init_services(license_service, audit_service)
        
        # Mount router
        app.include_router(
            license_api.router,
            tags=["License Management"],
            responses={401: {"description": "Unauthorized"}}
        )
        logger.info("Mounted License Management APIs at /api/v1/license")
        
    except Exception as e:
        logger.error(f"Failed to mount License APIs: {e}")


def mount_schedule_api():
    """
    Mount Batch Schedule API routes.
    Provides CRUD endpoints for managing periodic job schedules.
    """
    try:
        app.include_router(
            schedule_api.router,
            prefix="/api/v1/schedules",
            tags=["Batch Schedules"],
        )
        logger.info("Mounted Batch Schedule APIs at /api/v1/schedules")
    except Exception as e:
        logger.error(f"Failed to mount Schedule APIs: {e}")


# ------------ ROUTING MIDDLEWARE ------------

@app.middleware("http")
async def route_classifier(request: Request, call_next):
    """
    Classify routes as MCP (worker) or API (direct) for monitoring
    """
    path = request.url.path
    
    # Add routing metadata to request state
    if path.startswith("/tools/") or path.startswith("/ws/"):
        request.state.route_type = "mcp_worker"
    elif path.startswith("/api/"):
        request.state.route_type = "rest_api"
    elif path.startswith("/v1/sim/") or path.startswith("/v1/tasks") or path.startswith("/v1/captures"):
        request.state.route_type = "wxcc_simulator"
    elif path in ["/docs", "/redoc", "/openapi.json"]:
        request.state.route_type = "documentation"
    else:
        request.state.route_type = "system"
    
    # Add timing
    start_time = datetime.now()
    
    # Process request
    response = await call_next(request)
    
    # Log routing information
    duration = (datetime.now() - start_time).total_seconds()
    logger.debug(
        f"[{request.state.route_type}] {request.method} {path} - "
        f"Status: {response.status_code}, Duration: {duration:.3f}s"
    )
    
    # Add custom headers
    response.headers["X-Route-Type"] = request.state.route_type
    response.headers["X-Response-Time"] = f"{duration:.3f}"
    
    return response


# ------------ HYBRID ENDPOINTS ------------

@app.get("/api/status")
async def unified_status() -> Dict[str, Any]:
    """
    Unified status endpoint showing both MCP and API status
    """
    status = {
        "timestamp": datetime.now().isoformat(),
        "gateway": "operational",
        "mcp_workers": pool.get_stats(),
        "api_status": "enabled" if API_MODULES_AVAILABLE else "disabled"
    }
    
    if API_MODULES_AVAILABLE:
        # Add API-specific status
        status["api_endpoints"] = {
            "journeys": "operational",
            "analytics": "operational",
            "auth": "operational",
            "health": "operational",
        }
    
    return status


@app.post("/api/v1/hybrid/journey-analysis")
async def hybrid_journey_analysis(
    journey_id: str,
    use_worker: bool = False
) -> Dict[str, Any]:
    """
    Example hybrid endpoint that can use either direct call or worker
    
    - use_worker=False: Direct service call (fast, low latency)
    - use_worker=True: Delegate to MCP worker (isolated, scalable)
    """
    if use_worker:
        # Use MCP worker for heavy processing
        worker = await pool.get_worker()
        message = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "tools/call",
            "params": {
                "name": "journeys_tool",
                "arguments": {
                    "action": "get_comprehensive",
                    "journey_id": journey_id
                }
            }
        }
        resp = await worker.send_one(message, timeout=MCP_REQUEST_TIMEOUT)
        return resp.get("result", {})
    else:
        # Direct service call for quick response
        if not API_MODULES_AVAILABLE:
            raise HTTPException(status_code=501, detail="Direct API not available")
            
        from src.services.journey_service import JourneyService
        from src.models.journey_model import JourneyActionRequest
        
        service = JourneyService()
        request = JourneyActionRequest(
            action="read",
            journey_id=journey_id
        )
        result = await service.execute_action(request)
        return result.model_dump(exclude_none=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Job Engine MCP HTTP Gateway")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()
    
    uvicorn.run(
        "mcp_http_gateway:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        access_log=True,
    )
