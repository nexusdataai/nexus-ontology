# cluster_gateway.py
import json
import uuid
import asyncio
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
import uvicorn
import aioredis

API_KEY = "super-secret"
REDIS_URL = "redis://localhost:6379/0"
REQUEST_QUEUE = "mcp:requests"
RESPONSE_PREFIX = "mcp:response:"  # per-request key
RESPONSE_TTL = 60  # seconds

app = FastAPI(title="MCP Cluster Gateway")

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    id: Optional[str] = None

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

@app.post("/cluster/tools", dependencies=[Depends(verify_api_key)])
async def cluster_call(req: ToolCallRequest):
    redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    req_id = req.id or str(uuid.uuid4())
    job = {
        "id": req_id,
        "tool_name": req.tool_name,
        "arguments": req.arguments,
    }

    # push job to queue
    await redis.rpush(REQUEST_QUEUE, json.dumps(job))

    # wait for response on a dedicated key
    resp_key = RESPONSE_PREFIX + req_id
    try:
        # BLPOP-like polling (simple version)
        for _ in range(600):  # up to 60s @ 0.1s
            resp = await redis.get(resp_key)
            if resp:
                await redis.delete(resp_key)
                return json.loads(resp)
            await asyncio.sleep(0.1)
    finally:
        await redis.close()

    raise HTTPException(status_code=504, detail="Timed out waiting for worker response")


if __name__ == "__main__":
    uvicorn.run("cluster_gateway:app", host="0.0.0.0", port=8081, reload=False)
