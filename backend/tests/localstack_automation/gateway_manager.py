"""
Gateway Manager

Manages the HTTP Gateway server lifecycle for test automation.
"""

import subprocess
import time
import os
import signal
import sys
from pathlib import Path
from typing import Optional
import requests

from .logging_config import get_logger, TestAutomationLogger
from .models import ServiceHealth


class GatewayManager:
    """Manages the HTTP Gateway server."""
    
    # Default gateway settings
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 8000
    
    # Gateway script/module
    GATEWAY_MODULE = "mcp_http_gateway.py"
    
    # PID file name
    PID_FILE = ".gateway.pid"
    
    # Log files
    LOG_FILE = "gateway.log"
    ERROR_LOG_FILE = "gateway-error.log"
    
    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        project_root: Optional[Path] = None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT
    ):
        """
        Initialize Gateway manager.
        
        Args:
            server_url: Gateway server URL for health checks
            project_root: Project root directory
            host: Host to bind gateway to
            port: Port to bind gateway to
        """
        self.server_url = server_url.rstrip('/')
        self.host = host
        self.port = port
        self.logger = get_logger()
        self._process = None
        
        # Determine project root
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Assume we're in tests/localstack_automation
            self.project_root = Path(__file__).parent.parent.parent
        
        self.pid_file = self.project_root / self.PID_FILE
        self.log_file = self.project_root / self.LOG_FILE
        self.error_log_file = self.project_root / self.ERROR_LOG_FILE
        self.gateway_module = self.project_root / self.GATEWAY_MODULE
    
    def is_running(self) -> bool:
        """
        Check if gateway is responding to health checks.
        
        Returns:
            True if gateway responds to health endpoint, False otherwise
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def is_healthy(self) -> bool:
        """
        Check if gateway health endpoint reports healthy status.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("status") in ("healthy", "ok", "running")
            return False
        except (requests.RequestException, ValueError):
            return False
    
    def get_health(self) -> ServiceHealth:
        """
        Get detailed health status.
        
        Returns:
            ServiceHealth object with status details
        """
        start_time = time.time()
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                health_data = response.json()
                healthy = health_data.get("status") in ("healthy", "ok", "running")
                
                return ServiceHealth(
                    name="Gateway",
                    healthy=healthy,
                    endpoint=self.server_url,
                    response_time_ms=response_time,
                    details=health_data
                )
            else:
                return ServiceHealth(
                    name="Gateway",
                    healthy=False,
                    endpoint=self.server_url,
                    response_time_ms=response_time,
                    error=f"HTTP {response.status_code}"
                )
        except requests.RequestException as e:
            return ServiceHealth(
                name="Gateway",
                healthy=False,
                endpoint=self.server_url,
                error=str(e)
            )
    
    def start(self, timeout: int = 30) -> bool:
        """
        Start the gateway server.
        
        Args:
            timeout: Maximum time to wait for startup in seconds
            
        Returns:
            True if started successfully, False otherwise
        """
        TestAutomationLogger.log_step("Starting Gateway server...")
        
        # Check if already running
        if self.is_running():
            TestAutomationLogger.log_success("Gateway is already running")
            return True
        
        # Verify gateway module exists
        if not self.gateway_module.exists():
            TestAutomationLogger.log_error(f"Gateway module not found: {self.gateway_module}")
            return False
        
        # Start gateway process
        try:
            self.logger.info(f"Starting gateway on {self.host}:{self.port}")
            
            # Open log files
            log_handle = open(self.log_file, 'w')
            error_handle = open(self.error_log_file, 'w')
            
            # Determine how to run the gateway
            # Try uv first, fall back to python
            if self._command_exists("uv"):
                cmd = ["uv", "run", "python", str(self.gateway_module), 
                       "--host", self.host, "--port", str(self.port)]
            else:
                cmd = [sys.executable, str(self.gateway_module),
                       "--host", self.host, "--port", str(self.port)]
            
            # Build environment with LocalStack settings
            env = os.environ.copy()
            env["USE_LOCALSTACK"] = "true"
            env["LOCALSTACK_HOST"] = "localhost"
            
            # Start process
            if sys.platform == "win32":
                # Windows: use CREATE_NEW_PROCESS_GROUP
                self._process = subprocess.Popen(
                    cmd,
                    stdout=log_handle,
                    stderr=error_handle,
                    cwd=str(self.project_root),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                # Unix: use preexec_fn for new process group
                self._process = subprocess.Popen(
                    cmd,
                    stdout=log_handle,
                    stderr=error_handle,
                    cwd=str(self.project_root),
                    env=env,
                    preexec_fn=os.setsid
                )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(self._process.pid))
            
            self.logger.info(f"Gateway process started with PID {self._process.pid}")
            
        except Exception as e:
            TestAutomationLogger.log_error(f"Failed to start gateway: {e}")
            return False
        
        # Wait for health
        return self.wait_for_health(timeout)
    
    def wait_for_health(self, timeout: int = 30) -> bool:
        """
        Wait for gateway health endpoint to respond.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if healthy within timeout, False otherwise
        """
        TestAutomationLogger.log_step(f"Waiting for Gateway to be healthy (timeout: {timeout}s)...")
        
        start_time = time.time()
        check_interval = 1  # seconds
        
        # Initial delay to let process start
        time.sleep(2)
        
        while (time.time() - start_time) < timeout:
            # Check if process is still running
            if self._process and self._process.poll() is not None:
                TestAutomationLogger.log_error(
                    f"Gateway process exited with code {self._process.returncode}"
                )
                return False
            
            if self.is_running():
                elapsed = time.time() - start_time
                TestAutomationLogger.log_success(f"Gateway is healthy (took {elapsed:.1f}s)")
                return True
            
            time.sleep(check_interval)
            self.logger.debug("Waiting for Gateway...")
        
        TestAutomationLogger.log_error(f"Gateway failed to become healthy within {timeout}s")
        return False
    
    def stop(self) -> bool:
        """
        Stop the gateway server gracefully.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        TestAutomationLogger.log_step("Stopping Gateway server...")
        
        pid = self._get_pid()
        
        if pid is None and self._process is None:
            TestAutomationLogger.log_warning("No Gateway process found to stop")
            self._cleanup_files()
            return True
        
        # Use stored process if available
        if self._process:
            pid = self._process.pid
        
        try:
            if sys.platform == "win32":
                # Windows: use taskkill
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                    timeout=10
                )
            else:
                # Unix: send SIGTERM, then SIGKILL if needed
                os.kill(pid, signal.SIGTERM)
                
                # Wait for graceful shutdown
                for _ in range(10):
                    time.sleep(0.5)
                    try:
                        os.kill(pid, 0)  # Check if process exists
                    except OSError:
                        break
                else:
                    # Force kill if still running
                    os.kill(pid, signal.SIGKILL)
            
            TestAutomationLogger.log_success("Gateway stopped")
            
        except (ProcessLookupError, OSError) as e:
            self.logger.debug(f"Process already stopped: {e}")
        except Exception as e:
            TestAutomationLogger.log_error(f"Error stopping Gateway: {e}")
            return False
        finally:
            self._cleanup_files()
            self._process = None
        
        return True
    
    def get_logs(self, lines: int = 100) -> str:
        """
        Get gateway server logs.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            Log output as string
        """
        logs = []
        
        # Read main log file
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    log_lines = f.readlines()
                    logs.append("=== Gateway Log ===")
                    logs.extend(log_lines[-lines:])
            except Exception as e:
                logs.append(f"Error reading log file: {e}")
        
        # Read error log file
        if self.error_log_file.exists():
            try:
                with open(self.error_log_file, 'r') as f:
                    error_lines = f.readlines()
                    if error_lines:
                        logs.append("\n=== Gateway Error Log ===")
                        logs.extend(error_lines[-lines:])
            except Exception as e:
                logs.append(f"Error reading error log file: {e}")
        
        return ''.join(logs) if logs else "No logs available"
    
    def _get_pid(self) -> Optional[int]:
        """Get gateway PID from PID file."""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return None
    
    def _cleanup_files(self):
        """Clean up PID and log files."""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            self.logger.debug(f"Error removing PID file: {e}")
    
    def _command_exists(self, cmd: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["where", cmd],
                    capture_output=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    timeout=5
                )
            return result.returncode == 0
        except Exception:
            return False
