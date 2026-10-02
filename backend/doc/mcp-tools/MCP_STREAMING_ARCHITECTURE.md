# MCP Streaming Architecture Documentation

## Overview

This document describes the enhanced MCP (Model Context Protocol) server architecture with full streaming support, worker pool management, and multiple transport protocols.

## Architecture Components

### 1. Core MCP Server (`src/server.py`)

The core server implements the business logic using FastMCP framework with streaming capabilities:

- **Tools with Progress Reporting**: All tools now support `Context` parameter for progress updates
- **Streaming Returns**: List operations can return `AsyncGenerator` for chunked responses
- **Dual Execution Mode**: Supports both stdio (subprocess) and direct Python execution

#### Key Features:
```python
@mcp.tool()
async def journeys_tool(ctx: Context, action: str, ...) -> Union[Dict, AsyncGenerator]:
    # Progress reporting for long operations
    await ctx.report_progress(1, 3, "Loading data...")
    
    # Stream results for list operations
    if action == "list":
        async def stream_journeys():
            for journey in journeys:
                yield journey
        return stream_journeys()
```

### 2. HTTP Gateway (`mcp_http_gateway.py`)

Modern HTTP/WebSocket gateway with worker pool management:

#### Features:
- **Worker Pool**: Auto-scaling subprocess workers (2-8 by default)
- **Health Monitoring**: Automatic worker health checks and recovery
- **Multiple Transports**: HTTP, SSE (Server-Sent Events), and WebSocket
- **Load Balancing**: Intelligent worker selection based on load

#### Endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server information and statistics |
| `/health` | GET | Health check with worker status |
| `/tools` | GET | List available MCP tools |
| `/tools/{name}` | POST | Call tool (synchronous) |
| `/tools/{name}/stream` | POST | Call tool with SSE streaming |
| `/ws/tools/{name}` | WS | WebSocket streaming interface |
| `/stats` | GET | Detailed worker pool statistics |

### 3. Worker Pool Architecture

```
┌─────────────────────────────────────────┐
│         HTTP Gateway Process             │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │        Worker Pool Manager         │ │
│  │                                    │ │
│  │  Min Workers: 2                    │ │
│  │  Max Workers: 8                    │ │
│  │  Auto-scaling: Yes                 │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│     ┌─────────┴─────────┐               │
│     │                   │               │
│  ┌──▼──┐  ┌──▼──┐  ┌──▼──┐             │
│  │ W1  │  │ W2  │  │ W3  │  ...         │
│  └─────┘  └─────┘  └─────┘             │
│     │        │        │                 │
└─────┼────────┼────────┼─────────────────┘
      │        │        │
  ┌───▼──┐ ┌──▼───┐ ┌──▼───┐
  │ MCP  │ │ MCP  │ │ MCP  │ (Subprocesses)
  │Server│ │Server│ │Server│
  └──────┘ └──────┘ └──────┘
```

## Streaming Protocols

### 1. Server-Sent Events (SSE)

For unidirectional streaming from server to client:

```bash
curl -X POST http://localhost:8000/tools/journeys_tool/stream \
  -H "X-API-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"action": "list"}}'
```

Response format:
```
event: progress
data: {"progress": 1, "total": 3, "message": "Loading..."}

event: chunk
data: {"index": 0, "data": {...}}

event: result
data: {"status": "success", "data": [...]}

event: done
data: {"status": "complete"}
```

### 2. WebSocket Streaming

For bidirectional real-time communication:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/tools/journeys_tool?api_key=super-secret');

ws.onopen = () => {
    ws.send(JSON.stringify({
        arguments: { action: "list" },
        id: "req-123"
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch(data.event) {
        case 'started':
            console.log('Operation started');
            break;
        case 'progress':
            console.log(`Progress: ${data.progress}/${data.total}`);
            break;
        case 'chunk':
            console.log('Received chunk:', data.data);
            break;
        case 'complete':
            console.log('Operation complete');
            break;
    }
};
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_WORKERS` | 2 | Minimum number of worker processes |
| `MAX_WORKERS` | 8 | Maximum number of worker processes |
| `MCP_REQUEST_TIMEOUT` | 60.0 | Request timeout in seconds |
| `API_KEY` | super-secret | API authentication key |
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Starting the Gateway

```bash
# Basic startup
./start_gateway.sh

# With custom configuration
export MIN_WORKERS=4
export MAX_WORKERS=16
export LOG_LEVEL=DEBUG
./start_gateway.sh

# Direct Python execution
python mcp_http_gateway.py --host 0.0.0.0 --port 8000

# Development mode with auto-reload
python mcp_http_gateway.py --reload
```

## Integration Testing

Run the comprehensive test suite:

```bash
# Start the gateway first
./start_gateway.sh

# In another terminal, run tests
python test_mcp_integration.py
```

Tests cover:
- STDIO mode communication
- HTTP endpoints
- SSE streaming
- WebSocket streaming
- Worker pool scaling
- Error handling

## Migration from Old Architecture

### Before (Direct Import)
```python
# Replaced by mcp_http_gateway.py
from src.services.journey_service import JourneyService
service = JourneyService()
result = await service.execute_action(request)
```

### After (Subprocess Workers)
```python
# New mcp_http_gateway.py
worker = await pool.get_worker()
message = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": tool_name, "arguments": args}
}
resp = await worker.send_one(message, timeout=60.0)
```

## Benefits

1. **Scalability**: Auto-scaling worker pool handles varying loads
2. **Isolation**: Each worker runs in separate process for stability
3. **Streaming**: Real-time progress updates and chunked responses
4. **Resilience**: Worker crashes don't affect the gateway
5. **Protocol Compliance**: Proper MCP JSON-RPC implementation
6. **Performance**: Parallel processing with multiple workers
7. **Monitoring**: Built-in health checks and statistics

## API Examples

### List Journeys with Streaming

```python
import aiohttp
import json

async def stream_journeys():
    async with aiohttp.ClientSession() as session:
        headers = {"X-API-Key": "super-secret"}
        url = "http://localhost:8000/tools/journeys_tool/stream"
        payload = {"arguments": {"action": "list"}}
        
        async with session.post(url, headers=headers, json=payload) as response:
            async for line in response.content:
                if line.startswith(b'event:'):
                    event = line[6:].decode().strip()
                elif line.startswith(b'data:'):
                    data = json.loads(line[5:].decode())
                    print(f"Event: {event}, Data: {data}")
```

### WebSocket Real-time Updates

```python
import websockets
import json

async def websocket_journey_updates():
    uri = "ws://localhost:8000/ws/tools/journeys_tool?api_key=super-secret"
    
    async with websockets.connect(uri) as websocket:
        # Send request
        await websocket.send(json.dumps({
            "arguments": {"action": "create", "name": "New Journey"},
            "id": "create-001"
        }))
        
        # Receive updates
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data.get("event") == "progress":
                print(f"Progress: {data['message']}")
            elif data.get("event") == "complete":
                print("Journey created successfully!")
                break
```

## Troubleshooting

### Worker Pool Issues

Check worker statistics:
```bash
curl -H "X-API-Key: super-secret" http://localhost:8000/stats
```

### Connection Errors

1. Verify gateway is running: `curl http://localhost:8000/health`
2. Check worker processes: `ps aux | grep "src/server.py"`
3. Review logs for errors
4. Restart gateway if needed

### Performance Tuning

- Increase `MAX_WORKERS` for high concurrency
- Adjust `MCP_REQUEST_TIMEOUT` for long-running operations
- Use WebSocket for real-time requirements
- Use SSE for one-way streaming
- Use standard HTTP for simple requests

## Security Considerations

1. **API Key**: Always use strong API keys in production
2. **CORS**: Configure allowed origins properly
3. **Rate Limiting**: Consider adding rate limiting for public endpoints
4. **TLS**: Use HTTPS/WSS in production environments
5. **Input Validation**: All inputs are validated through Pydantic models

## Future Enhancements

- [ ] Redis-based job queue for better scaling
- [ ] Metrics collection (Prometheus)
- [ ] Circuit breaker pattern for resilience
- [ ] GraphQL interface option
- [ ] gRPC support for binary streaming
- [ ] Horizontal scaling with multiple gateway instances
