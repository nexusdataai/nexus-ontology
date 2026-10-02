# Configuration APIs

Runtime configuration management endpoints for the Nexus Telco Backend.

---

## Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/log-level` | Get current log level |
| PUT | `/api/v1/config/log-level` | Update log level at runtime |
| GET | `/api/v1/config/environment` | Get environment info |

---

## GET /api/v1/config/log-level

Get the current application log level and its source.

### Response

```json
{
  "level": "INFO",
  "source": "ssm",
  "timestamp": "2026-01-27T10:30:00.000Z"
}
```

### Source Values

| Source | Description |
|--------|-------------|
| `ssm` | Loaded from SSM Parameter Store |
| `env` | Loaded from environment variable |
| `default` | Using hardcoded default |

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/config/log-level" \
  -H "Authorization: Bearer <token>"
```

---

## PUT /api/v1/config/log-level

Update the application log level at runtime.

### Request

```json
{
  "level": "DEBUG",
  "persist_to_ssm": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | string | Yes | New log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `persist_to_ssm` | boolean | No | Whether to save to SSM (default: true) |

### Response

```json
{
  "status": "success",
  "previous_level": "INFO",
  "new_level": "DEBUG",
  "ssm_updated": true,
  "loggers_updated": 25,
  "timestamp": "2026-01-27T10:35:00.000Z"
}
```

### Example

```bash
curl -X PUT "http://localhost:8000/api/v1/config/log-level" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG", "persist_to_ssm": true}'
```

### Behavior

1. **Updates all active loggers immediately** - No restart required
2. **Persists to SSM** (if requested) - Survives container restart
3. **Updates environment variable** - For consistency

---

## GET /api/v1/config/environment

Get current environment configuration summary (non-sensitive).

### Response

```json
{
  "environment": "prod",
  "region": "ap-southeast-1",
  "is_aws": true,
  "is_localstack": false,
  "log_level": "INFO",
  "timestamp": "2026-01-27T10:30:00.000Z"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/api/v1/config/environment" \
  -H "Authorization: Bearer <token>"
```

---

## API Implementation

### Code Location

`src/apis/config_api.py`

### Log Level Update Logic

```python
@router.put("/log-level", response_model=LogLevelUpdateResponse)
async def set_log_level(request: LogLevelUpdateRequest):
    """Update the application log level at runtime."""
    
    new_level = request.level.upper()
    
    if new_level not in VALID_LOG_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level: {new_level}"
        )
    
    # Get current level before update
    previous_level, _ = _get_current_log_level_info()
    
    # 1. Update all active loggers
    loggers_updated = _update_all_loggers(new_level)
    
    # 2. Persist to SSM if requested
    ssm_updated = False
    if request.persist_to_ssm:
        ssm_updated = _update_ssm_parameter(new_level)
    
    # 3. Update environment variable for consistency
    os.environ['LOG_LEVEL'] = new_level
    
    return LogLevelUpdateResponse(
        status="success",
        previous_level=previous_level,
        new_level=new_level,
        ssm_updated=ssm_updated,
        loggers_updated=loggers_updated,
        timestamp=datetime.now().isoformat()
    )
```

### Logger Update Logic

```python
def _update_all_loggers(new_level: str) -> int:
    """Update log level for all active loggers."""
    
    count = 0
    level_value = getattr(logging, new_level.upper(), logging.INFO)
    
    # Update root logger
    logging.getLogger().setLevel(level_value)
    count += 1
    
    # Update all named loggers
    for name in logging.Logger.manager.loggerDict:
        log = logging.getLogger(name)
        if isinstance(log, logging.Logger):
            log.setLevel(level_value)
            for handler in log.handlers:
                handler.setLevel(level_value)
            count += 1
    
    return count
```

### SSM Parameter Update

```python
def _update_ssm_parameter(new_level: str) -> bool:
    """Update the log level in SSM Parameter Store."""
    
    if not is_aws_environment():
        return False
    
    config = get_config()
    param_path = f"/{CAPABILITY_NAME}/{config.environment}/server/log-level"
    
    ssm_client = boto3.client('ssm', region_name=config.aws_region)
    
    ssm_client.put_parameter(
        Name=param_path,
        Value=new_level.upper(),
        Type='String',
        Overwrite=True,
        Description='Application log level (updated via API)'
    )
    
    # Invalidate SSM cache
    loader = SSMParameterLoader(region=config.aws_region)
    loader.invalidate_path(f"/{CAPABILITY_NAME}/{config.environment}/")
    
    return True
```

---

## Error Responses

### Invalid Log Level

```json
{
  "detail": "Invalid log level: VERBOSE. Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL"
}
```
Status: `400 Bad Request`

### SSM Update Failed

```json
{
  "status": "success",
  "previous_level": "INFO",
  "new_level": "DEBUG",
  "ssm_updated": false,
  "loggers_updated": 25,
  "timestamp": "2026-01-27T10:35:00.000Z"
}
```

Note: `ssm_updated: false` indicates SSM update failed but loggers were still updated.

---

*Related: [Code Flow](code-flow.md) | [SSM Parameters Reference](ssm-parameters.md)*
