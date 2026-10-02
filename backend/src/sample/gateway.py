# advanced_gateway.py
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Depends, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="FastMCP Advanced Gateway")

# Command to run your FastMCP server
# Make sure server.py exists and defines your FastMCP app
MCP_CMD = ["fastmcp", "run", "server.py"]

# ---- CONFIG ----
MIN_WORKERS = 2           # minimum always-running workers
MAX_WORKERS = 8           # hard upper limit
API_KEY = "super-secret"  # replace with env var in real usage
MCP_REQUEST_TIMEOUT = 60.0
# -----------------


# ------------ AUTH (API KEY) ------------

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ------------ MODELS ------------

class MCPEnvelope(BaseModel):
    payload: Dict[str, Any]


class ToolCallRequest(BaseModel):
    arguments: Dict[str, Any]
    id: Optional[str] = None


# ------------ MCP WORKER ------------

class MCPWorker:
    """
    Represents a single MCP subprocess worker.
    Each worker has its own process and lock.
    """
    def __init__(self, worker_id: int, cmd):
        self.worker_id = worker_id
        self.cmd = cmd
        self.proc: Optional[asyncio.subprocess.Process] = None
        self.lock = asyncio.Lock()
        self.busy = False  # for basic auto-scaling decisions

    async def start(self):
        if self.proc is not None:
            return

        logging.info(f"[Worker {self.worker_id}] Starting MCP subprocess...")
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError(f"[Worker {self.worker_id}] Missing stdin/stdout")

    async def stop(self):
        if not self.proc:
            return
        logging.info(f"[Worker {self.worker_id}] Stopping MCP subprocess...")
        self.proc.terminate()
        try:
            await asyncio.wait_for(self.proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            logging.warning(f"[Worker {self.worker_id}] Kill after timeout")
            self.proc.kill()
        self.proc = None

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
            try:
                self.proc.stdin.write(line.encode("utf-8"))
                await self.proc.stdin.drain()

                try:
                    resp_line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    raise HTTPException(status_code=504, detail="MCP worker timed out")
            finally:
                self.busy = False

        if not resp_line:
            raise HTTPException(status_code=502, detail="Empty response from MCP worker")

        try:
            return json.loads(resp_line.decode("utf-8"))
        except Exception:
            logging.exception(f"[Worker {self.worker_id}] Invalid JSON from MCP")
            raise HTTPException(status_code=502, detail="Invalid JSON response from MCP worker")

    async def stream(self, message: Dict[str, Any], websocket: WebSocket, timeout: float):
        """
        Streaming mode: send a single MCP request, then forward
        *multiple* JSON lines from MCP to the WebSocket.

        We keep reading until:
          - MCP closes stdout, OR
          - client disconnects, OR
          - (you add a protocol-based termination condition)
        """
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise HTTPException(status_code=500, detail="Worker not ready")

        line = json.dumps(message) + "\n"

        async with self.lock:
            self.busy = True
            try:
                # Send the request
                self.proc.stdin.write(line.encode("utf-8"))
                await self.proc.stdin.drain()

                # Now stream each subsequent line
                while True:
                    try:
                        resp_line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=timeout)
                    except asyncio.TimeoutError:
                        await websocket.send_json({"error": "MCP worker timed out"})
                        break

                    if not resp_line:
                        # MCP closed stream
                        break

                    try:
                        payload = json.loads(resp_line.decode("utf-8"))
                    except Exception:
                        logging.exception(f"[Worker {self.worker_id}] Invalid streaming JSON")
                        await websocket.send_json({"error": "invalid-json-from-mcp"})
                        continue

                    # Forward each MCP message to WebSocket
                    await websocket.send_json(payload)

                    # Optional: if your MCP streaming protocol
                    # has a "done" flag or specific message, you can break here.
                    # Example:
                    # if payload.get("event") == "stream_end":
                    #     break

            finally:
                self.busy = False


# ------------ WORKER POOL (AUTO-SCALING) ------------

class WorkerPool:
    """
    Multi-worker pool, with:
      - min workers prestarted
      - max workers limit
      - auto-scaling: spawn new worker when all are busy
      - round-robin selection among available workers
    """
    def __init__(self, min_workers: int, max_workers: int, cmd):
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.cmd = cmd
        self.workers: list[MCPWorker] = []
        self._rr_index = 0
        self._lock = asyncio.Lock()

    async def start(self):
        # Start minimum workers
        for i in range(self.min_workers):
            worker = MCPWorker(i, self.cmd)
            await worker.start()
            self.workers.append(worker)
        logging.info(f"WorkerPool started with {len(self.workers)} workers.")

    async def stop(self):
        for w in self.workers:
            await w.stop()

    async def _spawn_worker_if_possible(self) -> Optional[MCPWorker]:
        if len(self.workers) >= self.max_workers:
            return None
        worker_id = len(self.workers)
        worker = MCPWorker(worker_id, self.cmd)
        await worker.start()
        self.workers.append(worker)
        logging.info(f"Auto-scaled: spawned worker {worker_id}. Now {len(self.workers)} workers.")
        return worker

    async def get_worker(self) -> MCPWorker:
        """
        Get an available worker.
        Strategy:
          1. Try to find an idle worker.
          2. If all busy and we can grow, spawn a new worker.
          3. Else fallback to round-robin (some request will wait on that worker's lock).
        """
        async with self._lock:
            # Try idle
            for w in self.workers:
                if not w.busy:
                    return w

            # Try auto-scale
            maybe_new = await self._spawn_worker_if_possible()
            if maybe_new:
                return maybe_new

            # Fallback: round-robin
            if not self.workers:
                raise HTTPException(status_code=500, detail="No MCP workers available")
            w = self.workers[self._rr_index]
            self._rr_index = (self._rr_index + 1) % len(self.workers)
            return w


pool = WorkerPool(MIN_WORKERS, MAX_WORKERS, MCP_CMD)


@app.on_event("startup")
async def startup_event():
    await pool.start()


@app.on_event("shutdown")
async def shutdown_event():
    await pool.stop()


# ------------ HTTP ENDPOINTS ------------

@app.post("/mcp", dependencies=[Depends(verify_api_key)])
async def raw_mcp(envelope: MCPEnvelope):
    """
    Low-level endpoint: send full MCP JSON-RPC payload.
    """
    worker = await pool.get_worker()
    resp = await worker.send_one(envelope.payload, timeout=MCP_REQUEST_TIMEOUT)
    return JSONResponse(resp)


@app.post("/tools/{tool_name}", dependencies=[Depends(verify_api_key)])
async def call_tool(tool_name: str, req: ToolCallRequest):
    """
    High-level endpoint: call a tool by name.
    """
    worker = await pool.get_worker()

    message = {
        "jsonrpc": "2.0",
        "id": req.id or str(uuid4()),
        "method": "tools/call",  # Adjust to your MCP method name if needed
        "params": {
            "name": tool_name,
            "arguments": req.arguments,
        },
    }

    resp = await worker.send_one(message, timeout=MCP_REQUEST_TIMEOUT)
    return JSONResponse(resp)


# ------------ WEBSOCKET FOR STREAMING ------------

@app.websocket("/ws/tools/{tool_name}")
async def ws_tool_stream(websocket: WebSocket, tool_name: str):
    """
    WebSocket endpoint for streaming tools.

    Protocol:
      - Client connects: ws://.../ws/tools/{tool_name}?api_key=...
      - Client sends a single JSON message:
          { "arguments": { ... }, "id": "optional-id" }
      - Gateway forwards the request to MCP worker via stream()
      - Each MCP line is forwarded as WebSocket JSON message back to client
    """
    # Simple API key via query param (you can also use subprotocols or headers)
    api_key = websocket.query_params.get("api_key")
    if api_key != API_KEY:
        await websocket.close(code=4401)  # custom unauthorized code
        return

    await websocket.accept()

    try:
        # Receive initial request from client
        init_msg = await websocket.receive_json()
        arguments = init_msg.get("arguments", {})
        req_id = init_msg.get("id") or str(uuid4())

        worker = await pool.get_worker()

        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",  # Or "tools/stream" depending on your MCP server
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        # Start streaming from MCP -> WebSocket
        await worker.stream(message, websocket, timeout=MCP_REQUEST_TIMEOUT)

        # Optionally notify end-of-stream
        await websocket.send_json({"event": "stream_complete"})
    except WebSocketDisconnect:
        logging.info("WebSocket client disconnected.")
    except Exception as e:
        logging.exception("Error in WebSocket streaming")
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
        await websocket.close()


if __name__ == "__main__":
    uvicorn.run("advanced_gateway:app", host="0.0.0.0", port=8080, reload=False)
