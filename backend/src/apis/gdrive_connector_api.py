"""
Google Drive Connector REST API

FastAPI router for Google Drive integration: OAuth2 flow, configuration,
file listing, connection testing, and diagnostics.
"""

import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

router = APIRouter()


class AuthStartRequest(BaseModel):
    client_id: str = ""
    redirect_uri: str = ""


class AuthCallbackRequest(BaseModel):
    code: str
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""


def _get_connector_service():
    from src.services.gdrive_connector_service import get_gdrive_connector_service
    return get_gdrive_connector_service()


def _get_settings_service():
    from src.services.gdrive_settings_service import get_gdrive_settings_service
    return get_gdrive_settings_service()


@router.get("/status", tags=["Google Drive Connector"])
async def get_status():
    svc = _get_connector_service()
    settings = svc._get_settings()
    connected = False
    token_valid = False
    token_expires = None

    if settings.oauth2_config and settings.oauth2_config.token_expiry:
        token_expires = settings.oauth2_config.token_expiry
        from datetime import datetime, timezone
        try:
            expiry = datetime.fromisoformat(token_expires.replace("Z", "+00:00"))
            token_valid = expiry > datetime.now(timezone.utc)
            connected = token_valid
        except (ValueError, TypeError):
            pass

    return {
        "connected": connected,
        "auth_type": settings.auth_type.value,
        "token_valid": token_valid,
        "token_expires_at": token_expires,
        "folders_configured": len(settings.scan_config.folder_ids),
        "enable_auto_scan": settings.enable_auto_scan,
        "enable_ocr_extraction": settings.enable_ocr_extraction,
    }


@router.get("/settings", tags=["Google Drive Connector"])
async def get_settings():
    svc = _get_settings_service()
    settings = svc.get_settings()
    return {
        "success": True,
        "data": {
            "auth_type": settings.auth_type.value,
            "oauth2_config": {
                "client_id": settings.oauth2_config.client_id if settings.oauth2_config else "",
                "redirect_uri": settings.oauth2_config.redirect_uri if settings.oauth2_config else "",
                "scopes": settings.oauth2_config.scopes if settings.oauth2_config else [],
            } if settings.oauth2_config else None,
            "scan_config": {
                "folder_ids": settings.scan_config.folder_ids,
                "mime_type_filters": settings.scan_config.mime_type_filters,
                "max_files_per_scan": settings.scan_config.max_files_per_scan,
                "include_subfolders": settings.scan_config.include_subfolders,
            },
            "enable_auto_scan": settings.enable_auto_scan,
            "enable_ocr_extraction": settings.enable_ocr_extraction,
            "scan_schedule": settings.scan_schedule,
            "last_updated": settings.last_updated.isoformat() if settings.last_updated else None,
        },
    }


@router.put("/settings", tags=["Google Drive Connector"])
async def update_settings(request: dict):
    svc = _get_settings_service()
    from src.models.gdrive_connector_config import (
        GDriveAuthType, GDriveOAuth2Config, GDriveScanConfig,
    )
    from pydantic import SecretStr

    kwargs = {}
    if 'auth_type' in request:
        kwargs['auth_type'] = GDriveAuthType(request['auth_type'])
    if 'enable_auto_scan' in request:
        kwargs['enable_auto_scan'] = request['enable_auto_scan']
    if 'enable_ocr_extraction' in request:
        kwargs['enable_ocr_extraction'] = request['enable_ocr_extraction']
    if 'scan_schedule' in request:
        kwargs['scan_schedule'] = request['scan_schedule']
    if 'scan_config' in request:
        kwargs['scan_config'] = GDriveScanConfig(**request['scan_config'])
    if 'oauth2_config' in request:
        oc = request['oauth2_config']
        for field in ('client_secret', 'refresh_token', 'access_token'):
            if field in oc and isinstance(oc[field], str):
                oc[field] = SecretStr(oc[field])
        kwargs['oauth2_config'] = GDriveOAuth2Config(**oc)

    settings = svc.update_settings(**kwargs)
    return {"success": True, "message": "Settings saved"}


@router.post("/test", tags=["Google Drive Connector"])
async def test_connection():
    svc = _get_connector_service()
    result = await svc.test_connection()
    return result


@router.post("/auth/start", tags=["Google Drive Connector"])
async def auth_start(request: AuthStartRequest):
    svc = _get_connector_service()
    try:
        url = svc.get_authorization_url(
            client_id=request.client_id,
            redirect_uri=request.redirect_uri,
        )
        return {"success": True, "authorization_url": url}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/callback", tags=["Google Drive Connector"])
async def auth_callback(request: AuthCallbackRequest):
    svc = _get_connector_service()
    try:
        token_data = await svc.exchange_code(
            code=request.code,
            client_id=request.client_id,
            client_secret=request.client_secret,
            redirect_uri=request.redirect_uri,
        )

        settings_svc = _get_settings_service()
        from pydantic import SecretStr
        from src.models.gdrive_connector_config import GDriveOAuth2Config
        current = settings_svc.get_settings()
        oauth_cfg = current.oauth2_config or GDriveOAuth2Config()
        oauth_cfg.refresh_token = SecretStr(token_data.get("refresh_token", ""))
        oauth_cfg.access_token = SecretStr(token_data.get("access_token", ""))

        expires_in = token_data.get("expires_in", 3600)
        from datetime import datetime, timezone, timedelta
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        oauth_cfg.token_expiry = expiry.isoformat()

        if request.client_id:
            oauth_cfg.client_id = request.client_id
        if request.client_secret:
            oauth_cfg.client_secret = SecretStr(request.client_secret)

        settings_svc.update_settings(oauth2_config=oauth_cfg)

        return {
            "success": True,
            "message": "Authorization successful. Tokens saved.",
            "token_expires_at": oauth_cfg.token_expiry,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {e}")


@router.get("/files", tags=["Google Drive Connector"])
async def list_files(
    folder_id: str = Query("", description="Specific folder ID to list"),
    page_token: str = Query("", description="Pagination token"),
    page_size: int = Query(50, ge=1, le=200),
):
    svc = _get_connector_service()
    try:
        files, next_page = await svc.list_files(
            folder_id=folder_id, page_token=page_token, page_size=page_size,
        )
        return {"files": files, "next_page_token": next_page, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File listing failed: {e}")


@router.get("/diagnostics", tags=["Google Drive Connector"])
async def get_diagnostics():
    svc = _get_connector_service()
    return svc.get_diagnostics()
