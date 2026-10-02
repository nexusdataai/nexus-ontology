# cluster_worker.py
import asyncio
import json
import logging
import aioredis
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)

REDIS_URL = "redis://localhost:6379/0"
REQUEST_QUEUE = "mcp:requests"
RESPONSE_PREFIX = "mcp:response:"
MCP_CMD = ["fastmcp", "run", "server.py"]

class MCPWorkerProcess:
    def __init__(self, cmd):
        self.cmd = cmd
        self.proc: asyncio.subprocess.Process | None = None

    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("Missing stdin/stdout")

    async def send_one(self, message: Dict[str, Any]) -> Dict[str, Any]:
        line = json.dumps(message) + "\n"
        self.proc.stdin.write(line.encode("utf-8"))
        await self.proc.stdin.drain()
        resp_line = await self.proc.stdout.readline()
        if not resp_line:
            raise RuntimeError("Empty response from MCP")
        return json.loads(resp_line.decode("utf-8"))


async def main():
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    mcp = MCPWorkerProcess(MCP_CMD)
    await mcp.start()
    logging.info("Cluster worker started, listening on Redis queue...")

    while True:
        # BLPOP - wait for job
        _, raw = await redis.blpop(REQUEST_QUEUE)
        job = json.loads(raw)
        req_id = job["id"]
        tool_name = job["tool_name"]
        arguments = job["arguments"]

        logging.info(f"Processing job {req_id} tool={tool_name}")

        # Build MCP message
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        try:
            result = await mcp.send_one(message)
            await redis.set(RESPONSE_PREFIX + req_id, json.dumps(result), ex=60)
        except Exception as e:
            logging.exception("Error processing job")
            await redis.set(RESPONSE_PREFIX + req_id, json.dumps({"error": str(e)}), ex=60)

if __name__ == "__main__":
    asyncio.run(main())
