# server.py
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional

import aiohttp
from fastmcp import FastMCP, Context, tool
from pydantic import BaseModel

mcp = FastMCP("full-featured-mcp-server")


# ============
# Models
# ============

class MathResult(BaseModel):
    a: int
    b: int
    result: int


class StreamChunk(BaseModel):
    index: int
    data: str


# =======================
# 1. Simple Sync Tool
# =======================

@mcp.tool()
def ping() -> str:
    """
    Synchronous tool — fastest possible execution.
    """
    return "pong"


# ===========================
# 2. Async Tool (non-stream)
# ===========================

@mcp.tool()
async def get_time(fmt: Optional[str] = None) -> str:
    """
    Asynchronous tool returning the current server time.
    """
    await asyncio.sleep(0.1)  # simulate async operations

    now = datetime.utcnow()
    if fmt:
        return now.strftime(fmt)
    return now.isoformat() + "Z"


# ==========================================
# 3. "Synchronous Streaming" via ctx.progress
# ==========================================

@mcp.tool()
async def long_task_with_progress(ctx: Context, steps: int = 5) -> dict:
    """
    Streams progress updates via MCP notifications.
    Ideal for your /ws streaming gateway.
    """
    for i in range(steps):
        await ctx.report_progress(
            progress=i + 1,
            total=steps,
            message=f"Step {i+1}/{steps} in progress..."
        )
        await asyncio.sleep(1)

    return {"status": "completed", "steps": steps}


# ==========================================
# 4. True Streaming Tool (async generator)
# ==========================================

@mcp.tool()
async def number_stream(count: int = 10, delay: float = 0.5) -> AsyncGenerator[StreamChunk, None]:
    """
    Returns a stream of objects (chunks) one by one.
    This supports real streaming in your WebSocket mode.
    """
    for i in range(count):
        yield StreamChunk(index=i, data=f"Number {i}")
        await asyncio.sleep(delay)


# ==========================================
# 5. HTTP Streaming Tool (chunked HTTP)
# ==========================================

@mcp.tool()
async def http_stream(url: str) -> AsyncGenerator[StreamChunk, None]:
    """
    Streams chunks from an HTTP endpoint using aiohttp.

    Works amazing with your WebSocket gateway's streaming function.
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            idx = 0
            async for chunk in resp.content.iter_chunked(1024):
                if not chunk:
                    continue
                yield StreamChunk(index=idx, data=chunk.decode(errors="ignore"))
                idx += 1


# ==========================================
# 6. Structured Return Tool (sync)
# ==========================================

@mcp.tool()
def add(a: int, b: int) -> MathResult:
    """Basic synchronous structured-output tool."""
    return MathResult(a=a, b=b, result=a + b)


# ==========================================
# 7. Mixed async + notifications + final value
# ==========================================

@mcp.tool()
async def fetch_url_with_updates(ctx: Context, url: str) -> dict:
    """
    Example of mixed behavior:
      - Sends notifications for progress
      - Streams intermediate info
      - Returns final JSON
    """
    await ctx.info(f"Fetching {url} ...")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            size = resp.content_length or 0
            downloaded = 0

            async for chunk in resp.content.iter_chunked(2048):
                if chunk:
                    downloaded += len(chunk)
                    await ctx.report_progress(
                        progress=downloaded,
                        total=size or None,
                        message=f"Downloaded {downloaded}/{size if size else '?'} bytes"
                    )

    await ctx.info("Download completed")

    return {"url": url, "downloaded": downloaded}


# =========================
# Run (when executed directly)
# =========================

if __name__ == "__main__":
    # This runs the MCP server using stdio.
    # The advanced gateway launches this automatically via subprocess.
    mcp.run()
