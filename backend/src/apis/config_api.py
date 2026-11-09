"""
Configuration API for runtime settings management.

Provides endpoints to get and set application configuration,
including log levels that can be updated via SSM Parameter Store,
as well as SSM parameter and secrets management.

Protected by RBAC permissions:
- manage_system: Required for modifying system configuration
"""

import os
import logging
from datetime import datetime
from typing import Optional, Literal, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================

# Import session middleware for permission checks
try:
    from .session_middleware import (
        require_authentication,
        require_rbac_permission,
        get_session_from_cookie,
        has_permission
    )
    AUTH_MIDDLEWARE_AVAILABLE = True
except ImportError:
    logger.warning("Session middleware not available for config API")
    AUTH_MIDDLEWARE_AVAILABLE = False


def _local_config_admin_allowed() -> bool:
    """In-cluster local K3s: UI uses bypassAuth without a real Cognito session."""
    if os.getenv("USE_LOCALSTACK", "").lower() != "true":
        return False
    return os.getenv("ENABLE_COGNITO", "true").lower() in ("0", "false", "no")


def require_admin():
    """
    Dependency to require admin role or manage_system permission.
    Falls back to allow all if auth middleware is not available.
    """
    if _local_config_admin_allowed():
        async def local_admin_session():
            return {
                "user": {
                    "sub": "local-dev",
                    "email": "dev@local.test",
                    "role": "Admin",
                    "permissions": ["manage_system"],
                    "groups": ["Admin"],
                }
            }

        return local_admin_session

    if AUTH_MIDDLEWARE_AVAILABLE:
        return require_rbac_permission("manage_system")

    # Fallback: allow all (auth should be handled by gateway)
    async def allow_all():
        return True
    return allow_all

# Valid log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LogLevelResponse(BaseModel):
    """Response model for log level endpoints."""
    level: str = Field(..., description="Current log level")
    source: str = Field(..., description="Where the log level was loaded from (ssm, env, default)")
    timestamp: str = Field(..., description="ISO timestamp of the response")


class LogLevelUpdateRequest(BaseModel):
    """Request model for updating log level."""
    level: LogLevel = Field(..., description="New log level to set")
    persist_to_ssm: bool = Field(
        default=True, 
        description="Whether to persist the change to SSM Parameter Store"
    )


class LogLevelUpdateResponse(BaseModel):
    """Response model for log level update."""
    status: str = Field(..., description="Operation status (success/error)")
    previous_level: str = Field(..., description="Previous log level")
    new_level: str = Field(..., description="New log level")
    ssm_updated: bool = Field(..., description="Whether SSM was updated")
    loggers_updated: int = Field(..., description="Number of loggers updated")
    timestamp: str = Field(..., description="ISO timestamp of the update")


def _get_current_log_level_info() -> tuple[str, str]:
    """
    Get current log level and its source.
    
    Returns:
        Tuple of (level, source)
    """
    try:
        from src.config.config_provider import get_config, is_aws_environment
        config = get_config()
        
        # Check if we're on AWS and loaded from SSM
        if is_aws_environment():
            ssm_value = config._get_ssm_param('server/log-level')
            if ssm_value:
                return ssm_value.upper(), "ssm"
        
        # Check environment variable
        env_level = os.getenv('LOG_LEVEL')
        if env_level:
            return env_level.upper(), "env"
        
        # Return default
        return "INFO", "default"
        
    except Exception as e:
        logger.warning(f"Error getting config: {e}")
        return os.getenv('LOG_LEVEL', 'INFO').upper(), "env"


def _update_all_loggers(new_level: str) -> int:
    """
    Update log level for all active loggers.
    
    Args:
        new_level: New log level string (DEBUG, INFO, etc.)
        
    Returns:
        Number of loggers updated
    """
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
            # Update handlers too
            for handler in log.handlers:
                handler.setLevel(level_value)
            count += 1
    
    # Update cloudwatch loggers if available
    try:
        from src.utils.cloudwatch_logger import update_all_logger_levels
        count += update_all_logger_levels(new_level)
    except ImportError:
        pass
    
    return count


def _update_ssm_parameter(new_level: str) -> bool:
    """
    Update the log level in SSM Parameter Store.
    
    Args:
        new_level: New log level string
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from src.config.config_provider import get_config, is_aws_environment, CAPABILITY_NAME
        
        if not is_aws_environment():
            logger.info("Not in AWS environment, skipping SSM update")
            return False
        
        import boto3
        config = get_config()
        
        # Build parameter path
        param_path = f"/{CAPABILITY_NAME}/{config.environment}/server/log-level"
        
        # Check for LocalStack
        client_kwargs = {"region_name": config.aws_region}
        if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
            endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
            client_kwargs["endpoint_url"] = endpoint_url
            client_kwargs["aws_access_key_id"] = 'test'
            client_kwargs["aws_secret_access_key"] = 'test'
        
        ssm_client = boto3.client('ssm', **client_kwargs)
        
        ssm_client.put_parameter(
            Name=param_path,
            Value=new_level.upper(),
            Type='String',
            Overwrite=True,
            Description='Application log level (updated via API)'
        )
        
        # Invalidate SSM cache so next read gets fresh value
        try:
            from src.config.ssm_loader import SSMParameterLoader
            loader = SSMParameterLoader(region=config.aws_region)
            loader.invalidate_path(f"/{CAPABILITY_NAME}/{config.environment}/")
        except Exception:
            pass
        
        logger.info(f"Updated SSM parameter {param_path} to {new_level}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update SSM parameter: {e}")
        return False


@router.get("/log-level", response_model=LogLevelResponse)
async def get_log_level():
    """
    Get the current application log level.
    
    Returns the current log level and indicates where it was loaded from
    (SSM Parameter Store, environment variable, or default).
    """
    level, source = _get_current_log_level_info()
    
    return LogLevelResponse(
        level=level,
        source=source,
        timestamp=datetime.now().isoformat()
    )


@router.put("/log-level", response_model=LogLevelUpdateResponse)
async def set_log_level(request: LogLevelUpdateRequest):
    """
    Update the application log level at runtime.
    
    This endpoint:
    1. Updates all active Python loggers immediately
    2. Optionally persists the change to SSM Parameter Store
    
    The change takes effect immediately without requiring a restart.
    """
    new_level = request.level.upper()
    
    if new_level not in VALID_LOG_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid log level: {new_level}. Valid levels: {', '.join(VALID_LOG_LEVELS)}"
        )
    
    # Get current level before update
    previous_level, _ = _get_current_log_level_info()
    
    # Update all active loggers
    loggers_updated = _update_all_loggers(new_level)
    
    # Persist to SSM if requested
    ssm_updated = False
    if request.persist_to_ssm:
        ssm_updated = _update_ssm_parameter(new_level)
    
    # Also update environment variable for consistency
    os.environ['LOG_LEVEL'] = new_level
    
    logger.info(f"Log level changed from {previous_level} to {new_level}")
    
    return LogLevelUpdateResponse(
        status="success",
        previous_level=previous_level,
        new_level=new_level,
        ssm_updated=ssm_updated,
        loggers_updated=loggers_updated,
        timestamp=datetime.now().isoformat()
    )


@router.get("/environment")
async def get_environment_info():
    """
    Get current environment configuration summary.
    
    Returns non-sensitive configuration information about the
    current deployment environment.
    """
    try:
        from src.config.config_provider import get_config, is_aws_environment
        config = get_config()
        
        return {
            "environment": config.environment,
            "region": config.aws_region,
            "is_aws": is_aws_environment(),
            "is_localstack": os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            "log_level": config.log_level,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "environment": os.getenv('ENVIRONMENT', 'unknown'),
            "region": os.getenv('AWS_REGION', 'unknown'),
            "is_aws": False,
            "is_localstack": os.getenv('USE_LOCALSTACK', '').lower() == 'true',
            "log_level": os.getenv('LOG_LEVEL', 'INFO'),
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# SSM Parameter Management Models
# =============================================================================

class ParameterUpdateRequest(BaseModel):
    """Request model for updating a parameter."""
    value: str = Field(..., description="New parameter value")


class ParameterUpdateResponse(BaseModel):
    """Response model for parameter update."""
    status: str = Field(..., description="Operation status")
    path: str = Field(..., description="Full SSM parameter path")
    previous_value: str = Field(..., description="Previous value")
    new_value: str = Field(..., description="New value")
    timestamp: str = Field(..., description="ISO timestamp")


class SecretUpdateRequest(BaseModel):
    """Request model for updating a secret."""
    values: Dict[str, str] = Field(..., description="Secret key-value pairs to update")


class SecretUpdateResponse(BaseModel):
    """Response model for secret update."""
    status: str = Field(..., description="Operation status")
    name: str = Field(..., description="Secret name")
    updated_keys: List[str] = Field(..., description="Keys that were updated")
    timestamp: str = Field(..., description="ISO timestamp")


class CacheInvalidateResponse(BaseModel):
    """Response model for cache invalidation."""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Result message")
    timestamp: str = Field(..., description="ISO timestamp")


# =============================================================================
# SSM Parameter Endpoints
# =============================================================================

@router.get("/schema")
async def get_config_schema(_: bool = Depends(require_admin)):
    """
    Get the configuration schema with all parameter categories and metadata.
    
    Returns the full schema including:
    - Parameter categories with labels and descriptions
    - Parameter definitions with types, defaults, and options
    - Secrets schema with key definitions
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        return service.get_schema()
    except Exception as e:
        logger.error(f"Failed to get config schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters")
async def get_all_parameters(
    category: Optional[str] = None,
    _: bool = Depends(require_admin)
):
    """
    Get all SSM parameters grouped by category.
    
    Optionally filter by category name.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        return service.get_all_parameters(category)
    except Exception as e:
        logger.error(f"Failed to get parameters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{category}")
async def get_parameters_by_category(
    category: str,
    _: bool = Depends(require_admin)
):
    """
    Get all parameters for a specific category.
    """
    try:
        from src.services.ssm_service import get_ssm_service, PARAMETER_CATEGORIES
        
        if category not in PARAMETER_CATEGORIES:
            raise HTTPException(
                status_code=404,
                detail=f"Category not found: {category}. Valid categories: {', '.join(PARAMETER_CATEGORIES.keys())}"
            )
        
        service = get_ssm_service()
        result = service.get_all_parameters(category)
        
        if category in result.get("categories", {}):
            return result["categories"][category]
        
        raise HTTPException(status_code=404, detail=f"Category not found: {category}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parameters for category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/parameters/{category}/{name}")
async def get_parameter(
    category: str,
    name: str,
    _: bool = Depends(require_admin)
):
    """
    Get a single parameter by category and name.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        result = service.get_parameter(category, name)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Parameter not found: {category}/{name}"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parameter {category}/{name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/parameters/{category}/{name}", response_model=ParameterUpdateResponse)
async def update_parameter(
    category: str,
    name: str,
    request: ParameterUpdateRequest,
    _: bool = Depends(require_admin)
):
    """
    Update a parameter value.
    
    The change is persisted to SSM Parameter Store and takes effect immediately.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        
        # TODO: Get actual user from auth context
        user = "admin"
        
        result = service.set_parameter(category, name, request.value, user)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Failed to update parameter")
        
        return ParameterUpdateResponse(
            status=result["status"],
            path=result["path"],
            previous_value=result["previous_value"],
            new_value=result["new_value"],
            timestamp=result["timestamp"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update parameter {category}/{name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Secrets Management Endpoints
# =============================================================================

@router.get("/secrets")
async def get_secrets_list(_: bool = Depends(require_admin)):
    """
    Get list of available secrets with metadata (no values).
    
    Returns secret names, descriptions, and which keys they contain.
    Secret values are never returned by this endpoint.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        return {"secrets": service.get_secrets_list()}
    except Exception as e:
        logger.error(f"Failed to get secrets list: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/{name}")
async def get_secret(
    name: str,
    _: bool = Depends(require_admin)
):
    """
    Get a secret's metadata and masked values.
    
    Values are masked (e.g., "sk-p****1234") for security.
    Use this endpoint to verify a secret exists and see its structure.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        result = service.get_secret(name, mask=True)
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"Secret not found: {name}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get secret {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/secrets/{name}", response_model=SecretUpdateResponse)
async def update_secret(
    name: str,
    request: SecretUpdateRequest,
    _: bool = Depends(require_admin)
):
    """
    Update a secret's values.
    
    Provide key-value pairs to update. Existing keys not included
    in the request are preserved.
    
    Note: Some secrets are managed by other components (e.g., Webex Connector)
    and cannot be updated directly through this endpoint.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        
        # TODO: Get actual user from auth context
        user = "admin"
        
        result = service.set_secret(name, request.values, user)
        
        if result["status"] != "success":
            raise HTTPException(status_code=500, detail="Failed to update secret")
        
        return SecretUpdateResponse(
            status=result["status"],
            name=result["name"],
            updated_keys=result["updated_keys"],
            timestamp=result["timestamp"]
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update secret {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Cache Management Endpoints
# =============================================================================

@router.post("/cache/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(_: bool = Depends(require_admin)):
    """
    Invalidate all SSM and Secrets Manager caches.
    
    Use this to force a refresh of all cached configuration values.
    Cached values will be reloaded on next access.
    """
    try:
        from src.services.ssm_service import get_ssm_service
        service = get_ssm_service()
        result = service.invalidate_cache()
        
        return CacheInvalidateResponse(
            status=result["status"],
            message=result["message"],
            timestamp=result["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WXCC Mode Endpoint - Returns current effective mode (reads fresh from SSM)
# =============================================================================

class WxccModeResponse(BaseModel):
    """Response model for WXCC mode."""
    simulator_enabled: bool = Field(..., description="Whether WXCC simulator is enabled")
    mode: str = Field(..., description="Current mode: 'simulator' or 'real'")
    source: str = Field(..., description="Where the setting was read from")
    timestamp: str = Field(..., description="ISO timestamp")


@router.get("/wxcc-mode", response_model=WxccModeResponse)
async def get_wxcc_mode():
    """
    Get the current WXCC mode (simulator or real).
    
    This endpoint reads the setting directly from SSM Parameter Store
    to ensure it returns the most current value (not cached).
    """
    try:
        import boto3
        from src.config.config_provider import get_config, is_aws_environment, CAPABILITY_NAME
        
        config = get_config()
        source = "default"
        simulator_enabled = True  # Default to true (simulator mode)
        
        if is_aws_environment():
            try:
                # Build parameter path
                param_path = f"/{CAPABILITY_NAME}/{config.environment}/wxcc/enabled"
                
                # Read directly from SSM (not cached)
                client_kwargs = {"region_name": config.aws_region}
                if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
                    endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
                    client_kwargs["endpoint_url"] = endpoint_url
                    client_kwargs["aws_access_key_id"] = 'test'
                    client_kwargs["aws_secret_access_key"] = 'test'
                
                ssm_client = boto3.client('ssm', **client_kwargs)
                
                response = ssm_client.get_parameter(Name=param_path)
                value = response['Parameter']['Value'].lower()
                simulator_enabled = value == 'true'
                source = "ssm"
                logger.info(f"WXCC mode from SSM: {param_path} = {value}")
                
            except ssm_client.exceptions.ParameterNotFound:
                # Parameter doesn't exist, use default
                source = "default"
                logger.info(f"WXCC mode SSM param not found, using default: simulator_enabled={simulator_enabled}")
            except Exception as e:
                # SSM read failed, fall back to environment
                logger.warning(f"Failed to read SSM param, falling back to env: {e}")
                env_value = os.getenv('WXCC_SIMULATOR_ENABLED', 'true').lower()
                simulator_enabled = env_value == 'true'
                source = "env"
        else:
            # Not on AWS, use environment variable
            env_value = os.getenv('WXCC_SIMULATOR_ENABLED', 'true').lower()
            simulator_enabled = env_value == 'true'
            source = "env"
        
        return WxccModeResponse(
            simulator_enabled=simulator_enabled,
            mode="simulator" if simulator_enabled else "real",
            source=source,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error(f"Failed to get WXCC mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SFDC Simulator Mode Endpoint
# =============================================================================

class SfdcModeResponse(BaseModel):
    """Response model for SFDC simulator mode."""
    simulator_enabled: bool = Field(..., description="Whether SFDC simulator is enabled")
    mode: str = Field(..., description="Current mode: 'simulator' or 'real'")
    source: str = Field(..., description="Where the setting was read from")
    timestamp: str = Field(..., description="ISO timestamp")


@router.get("/sfdc-mode", response_model=SfdcModeResponse)
async def get_sfdc_mode():
    """Get the current SFDC mode (simulator or real)."""
    try:
        import boto3
        from src.config.config_provider import get_config, is_aws_environment, CAPABILITY_NAME

        config = get_config()
        simulator_enabled = False
        source = "default"

        if is_aws_environment():
            try:
                param_path = f"/{CAPABILITY_NAME}/{config.environment}/sfdc/enabled"
                client_kwargs = {"region_name": config.aws_region}
                ssm_client = boto3.client('ssm', **client_kwargs)
                response = ssm_client.get_parameter(Name=param_path)
                value = response['Parameter']['Value'].lower()
                simulator_enabled = value == 'true'
                source = "ssm"
            except ssm_client.exceptions.ParameterNotFound:
                source = "default"
            except Exception:
                env_value = os.getenv('SFDC_SIMULATOR_ENABLED', 'false').lower()
                simulator_enabled = env_value == 'true'
                source = "env"
        else:
            env_value = os.getenv('SFDC_SIMULATOR_ENABLED', 'false').lower()
            simulator_enabled = env_value == 'true'
            source = "env"

        return SfdcModeResponse(
            simulator_enabled=simulator_enabled,
            mode="simulator" if simulator_enabled else "real",
            source=source,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        logger.error(f"Failed to get SFDC mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SfdcModeUpdateRequest(BaseModel):
    enabled: bool = Field(..., description="Enable or disable SFDC simulator")


@router.put("/sfdc-mode", response_model=SfdcModeResponse)
async def set_sfdc_mode(request: SfdcModeUpdateRequest):
    """Toggle SFDC simulator mode on/off via SSM Parameter Store."""
    try:
        import boto3
        from src.config.config_provider import get_config, is_aws_environment, CAPABILITY_NAME

        config = get_config()
        value = "true" if request.enabled else "false"
        source = "env"

        if is_aws_environment():
            try:
                param_path = f"/{CAPABILITY_NAME}/{config.environment}/sfdc/enabled"
                client_kwargs = {"region_name": config.aws_region}
                ssm_client = boto3.client('ssm', **client_kwargs)
                ssm_client.put_parameter(
                    Name=param_path, Value=value, Type='String', Overwrite=True
                )
                source = "ssm"
                logger.info(f"SFDC mode set via SSM: {param_path} = {value}")
            except Exception as e:
                logger.warning(f"Failed to write SSM param, falling back to env: {e}")
                os.environ['SFDC_SIMULATOR_ENABLED'] = value
                source = "env"
        else:
            os.environ['SFDC_SIMULATOR_ENABLED'] = value
            source = "env"

        return SfdcModeResponse(
            simulator_enabled=request.enabled,
            mode="simulator" if request.enabled else "real",
            source=source,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
    except Exception as e:
        logger.error(f"Failed to set SFDC mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulator")
async def get_simulator_urls():
    """Public URLs for the standalone nexus-simulator service."""
    from src.services.simulator_fdw_client import (
        simulator_base_url,
        simulator_remote_enabled,
        simulator_ui_url,
    )
    return {
        "enabled": simulator_remote_enabled(),
        "baseUrl": simulator_base_url(),
        "uiUrl": simulator_ui_url() or "http://localhost:8082",
    }

