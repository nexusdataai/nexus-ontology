# Unified Gateway Architecture Guide

## Overview

The Unified Gateway (`mcp_http_gateway.py`) is a single entry point that serves both:
1. **MCP Tools** - Via subprocess worker pool (isolated, scalable)
2. **REST APIs** - Via direct function calls (low-latency, efficient)

This hybrid architecture allows you to choose the best execution model for each operation.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                   Unified Gateway                       │
│                 (mcp_http_gateway.py)                   │
├────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Request Router                      │  │
│  │  - Classifies requests by path                   │  │
│  │  - Routes to appropriate handler                 │  │
│  └──────────────────┬──────────────────────────────┘  │
│                     │                                  │
│     ┌───────────────┴───────────────┐                 │
│     │                               │                 │
│  ┌──▼─────────────┐   ┌────────────▼──────────┐     │
│  │  MCP Routes    │   │   REST API Routes      │     │
│  │  /tools/*      │   │   /api/v1/*            │     │
│  │  /ws/tools/*   │   │   - Journey Management │     │
│  └────────┬───────┘   │   - Analytics         │     │
│           │           │   - Authentication     │     │
│           │           │   - Health Checks      │     │
│           │           └────────────┬───────────┘     │
│           │                        │                  │
│  ┌────────▼───────┐   ┌───────────▼───────────┐     │
│  │  Worker Pool   │   │   Direct Import        │     │
│  │  (Subprocess)  │   │   (Same Process)       │     │
│  └────────┬───────┘   └───────────┬───────────┘     │
│           │                        │                  │
└───────────┼────────────────────────┼──────────────────┘
            │                        │
    ┌───────▼───────┐       ┌───────▼───────┐
    │  MCP Server   │       │  API Services  │
    │ (src/server)  │       │  (src/apis)    │
    └───────────────┘       └───────────────┘
```

## Endpoint Structure

### MCP Tool Endpoints (Worker Pool)
- `POST /tools/{tool_name}` - Execute MCP tool
- `POST /tools/{tool_name}/stream` - Stream tool execution (SSE)
- `WS /ws/tools/{tool_name}` - WebSocket streaming
- `GET /tools` - List available tools
- `GET /stats` - Worker pool statistics

### REST API Endpoints (Direct Call)
- `/api/v1/journeys/*` - Journey management
- `/api/v1/analytics/*` - Analytics and metrics
- `/api/v1/auth/*` - Authentication
- `/api/v1/health/*` - Health checks

### Hybrid Endpoints
- `/api/v1/hybrid/*` - Can use either worker or direct call

## When to Use Each Type

### Use MCP Workers (Subprocess) For:
| Scenario | Reason |
|----------|--------|
| Heavy computation | Process isolation prevents blocking |
| Long-running tasks | Non-blocking execution |
| Memory-intensive operations | Separate memory space |
| Untrusted code execution | Security isolation |
| ML model inference | Resource isolation |
| File processing | Prevents memory leaks |
| Batch operations | Parallel processing |

### Use Direct REST APIs For:
| Scenario | Reason |
|----------|--------|
| Simple CRUD operations | Lower latency (~10ms vs ~100ms) |
| Database queries | Connection pool efficiency |
| Cache lookups | Minimal overhead |
| Authentication checks | Fast response needed |
| Health checks | Quick status checks |
| Real-time data | Minimal latency |
| High-frequency calls | Avoid subprocess overhead |

## API Implementation Examples

### 1. Simple REST API (Direct Call)
```python
# src/apis/journey_api.py
@router.get("/{journey_id}/status")
async def get_journey_status(journey_id: str):
    """Quick status check - direct database query"""
    service = JourneyService()
    result = await service.get_status(journey_id)
    return {"status": result.status, "progress": result.progress}
```

### 2. Heavy Processing (Use Worker)
```python
# For heavy operations, delegate to MCP worker internally
@router.post("/{journey_id}/analyze")
async def analyze_journey(journey_id: str):
    """Complex analysis - delegate to worker"""
    # This internally uses the worker pool
    worker = await pool.get_worker()
    message = {
        "method": "tools/call",
        "params": {"name": "analyze_tool", "arguments": {...}}
    }
    return await worker.send_one(message, timeout=60)
```

### 3. Hybrid Approach
```python
@app.post("/api/v1/hybrid/process")
async def hybrid_process(items: List[str], use_worker: bool = None):
    """Smart routing based on workload"""
    if use_worker is None:
        # Auto-decide based on size
        use_worker = len(items) > 10
    
    if use_worker:
        # Large batch - use worker
        return await process_with_worker(items)
    else:
        # Small batch - direct processing
        return await process_directly(items)
```

## Configuration

### Environment Variables
```bash
# Worker Pool Configuration
MIN_WORKERS=2              # Minimum subprocess workers
MAX_WORKERS=8              # Maximum subprocess workers
MCP_REQUEST_TIMEOUT=60.0   # Worker request timeout

# API Configuration
API_RATE_LIMIT=100         # Requests per minute
API_CACHE_TTL=300          # Cache TTL in seconds
ENABLE_API_CACHE=true      # Enable response caching

# Authentication
API_KEY=super-secret       # API key for authentication
JWT_SECRET=change-this     # JWT signing secret

# Logging
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
```

## Starting the Gateway

### Basic Start
```bash
python mcp_http_gateway.py
```

### With Custom Configuration
```bash
export MIN_WORKERS=4
export MAX_WORKERS=16
export LOG_LEVEL=DEBUG
python mcp_http_gateway.py --port 8000
```

### Using Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "mcp_http_gateway.py"]
```

## Testing

### Test All Components
```bash
# Test unified gateway (MCP + APIs)
python test_unified_gateway.py

# Test MCP integration only
python test_mcp_integration.py
```

### Example API Calls

#### REST API (Direct)
```bash
# Quick journey status (direct call, ~10ms)
curl -X GET http://localhost:8000/api/v1/journeys/JRN-001/status \
  -H "X-API-Key: super-secret"

# Login (direct call)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

#### MCP Tool (Worker)
```bash
# Complex journey analysis (worker process, isolated)
curl -X POST http://localhost:8000/tools/journeys_tool \
  -H "X-API-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"action": "analyze", "journey_id": "JRN-001"}}'
```

#### Streaming (SSE)
```bash
# Stream metrics (Server-Sent Events)
curl -X POST http://localhost:8000/api/v1/analytics/stream \
  -H "X-API-Key: super-secret" \
  -H "Content-Type: application/json" \
  -d '{"stream_type": "metrics"}'
```

## Performance Comparison

| Operation Type | Direct API | MCP Worker | Recommendation |
|---------------|------------|------------|----------------|
| Simple GET | ~10ms | ~100ms | Use Direct API |
| Database Query | ~20ms | ~120ms | Use Direct API |
| Complex Analysis | ~500ms | ~550ms | Use Worker (isolation) |
| Batch Processing | O(n) | O(n/workers) | Use Worker (parallel) |
| Memory Heavy | Risk OOM | Isolated | Use Worker |
| Real-time Stream | Low latency | Higher latency | Use Direct API |

## Security Considerations

### Authentication Options
1. **API Key** - Simple, stateless
2. **JWT Token** - Stateful, user-specific
3. **OAuth 2.0** - Third-party integration

### Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/resource")
@limiter.limit("10/minute")
async def limited_resource():
    return {"data": "limited"}
```

### Input Validation
All inputs validated through Pydantic models:
```python
class JourneyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    priority: str = Field(..., pattern="^(low|medium|high)$")
```

## Monitoring

### Built-in Metrics
- Worker pool statistics: `/stats`
- Health checks: `/api/v1/health/`
- Unified status: `/api/status`

### Custom Headers
Every response includes:
- `X-Route-Type`: mcp_worker | rest_api | system
- `X-Response-Time`: Response time in seconds

### Logging
```python
# All requests logged with routing information
[mcp_worker] POST /tools/analyze - Status: 200, Duration: 1.234s
[rest_api] GET /api/v1/journeys - Status: 200, Duration: 0.015s
```

## Best Practices

1. **Use Direct APIs for UI** - Lower latency for better UX
2. **Use Workers for Background Jobs** - Process isolation
3. **Implement Caching** - Reduce database load
4. **Monitor Worker Health** - Auto-recovery enabled
5. **Use Streaming for Large Data** - Reduce memory usage
6. **Implement Circuit Breakers** - Fail gracefully
7. **Version Your APIs** - Use `/api/v1/`, `/api/v2/`
8. **Document Everything** - OpenAPI at `/docs`

## Troubleshooting

### Gateway Not Starting
```bash
# Check if port is in use
lsof -i :8000

# Check Python version (3.8+ required)
python --version

# Check dependencies
pip list | grep fastapi
```

### Workers Not Processing
```bash
# Check worker status
curl http://localhost:8000/stats

# Check MCP server directly
python src/server.py --stdio

# Check logs
tail -f logs/gateway.log
```

### API Errors
```bash
# Check API documentation
open http://localhost:8000/docs

# Test health endpoint
curl http://localhost:8000/api/v1/health/

# Check authentication
curl -I http://localhost:8000/api/v1/journeys \
  -H "X-API-Key: your-key"
```

## Future Enhancements

- [ ] GraphQL endpoint support
- [ ] gRPC for binary streaming
- [ ] Redis queue for job management
- [ ] Prometheus metrics export
- [ ] Distributed tracing (OpenTelemetry)
- [ ] WebSocket pub/sub for real-time events
- [ ] API versioning middleware
- [ ] Response compression
- [ ] Request/response caching layer
- [ ] Database connection pooling optimization
