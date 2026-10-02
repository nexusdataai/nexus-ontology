"""
Google Drive Connector Service

Core integration with Google Drive API:
- OAuth2 flow (authorization URL, token exchange, refresh)
- File listing from configured folders
- File download (bytes for extraction pipeline)
- Connection testing and diagnostics
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

gdrive_logger = logger.bind(component="gdrive-connector")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_UPLOAD_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class GoogleDriveConnectorService:

    def __init__(self):
        self._settings = None
        self._api_request_count = 0
        self._sync_history: List[Dict] = []
        self._error_log: List[Dict] = []

    def _get_settings(self):
        if self._settings is None:
            try:
                from src.services.gdrive_settings_service import get_gdrive_settings_service
                svc = get_gdrive_settings_service()
                self._settings = svc.get_settings()
            except Exception as e:
                gdrive_logger.warning(f"Could not load GDrive settings: {e}")
                from src.models.gdrive_connector_config import GoogleDriveConnectorSettings
                self._settings = GoogleDriveConnectorSettings()
        return self._settings

    def _log_error(self, message: str):
        self._error_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
        })
        if len(self._error_log) > 50:
            self._error_log = self._error_log[-50:]

    def get_authorization_url(self, client_id: str = "", redirect_uri: str = "") -> str:
        settings = self._get_settings()
        cid = client_id or (settings.oauth2_config.client_id if settings.oauth2_config else "")
        ruri = redirect_uri or (settings.oauth2_config.redirect_uri if settings.oauth2_config else "")
        scopes = " ".join(settings.oauth2_config.scopes if settings.oauth2_config else GOOGLE_DRIVE_UPLOAD_SCOPES)

        if not cid:
            raise ValueError("OAuth2 client_id not configured")

        params = {
            "client_id": cid,
            "redirect_uri": ruri,
            "response_type": "code",
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
        }
        from urllib.parse import urlencode
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, client_id: str = "",
                            client_secret: str = "", redirect_uri: str = "") -> Dict[str, Any]:
        settings = self._get_settings()
        cid = client_id or (settings.oauth2_config.client_id if settings.oauth2_config else "")
        secret = client_secret or (
            settings.oauth2_config.client_secret.get_secret_value()
            if settings.oauth2_config and settings.oauth2_config.client_secret else ""
        )
        ruri = redirect_uri or (settings.oauth2_config.redirect_uri if settings.oauth2_config else "")

        try:
            import httpx
        except ImportError:
            import urllib.request
            import urllib.parse
            data = urllib.parse.urlencode({
                "code": code, "client_id": cid, "client_secret": secret,
                "redirect_uri": ruri, "grant_type": "authorization_code",
            }).encode()
            req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data,
                                        headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code, "client_id": cid, "client_secret": secret,
                "redirect_uri": ruri, "grant_type": "authorization_code",
            })
            resp.raise_for_status()
            return resp.json()

    async def _get_access_token(self) -> str:
        settings = self._get_settings()

        if settings.auth_type.value == "service_account" and settings.service_account_config:
            return await self._get_service_account_token(settings)

        if not settings.oauth2_config:
            raise ValueError("OAuth2 not configured")

        cfg = settings.oauth2_config
        if cfg.access_token and cfg.token_expiry:
            try:
                expiry = datetime.fromisoformat(cfg.token_expiry.replace("Z", "+00:00"))
                if expiry > datetime.now(timezone.utc):
                    return cfg.access_token.get_secret_value()
            except (ValueError, TypeError):
                pass

        return await self._refresh_oauth_token(settings)

    async def _refresh_oauth_token(self, settings) -> str:
        cfg = settings.oauth2_config
        refresh_token = cfg.refresh_token.get_secret_value() if cfg.refresh_token else ""
        if not refresh_token:
            raise ValueError("No refresh token available. Re-authorize via OAuth2.")

        cid = cfg.client_id
        secret = cfg.client_secret.get_secret_value() if cfg.client_secret else ""

        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(GOOGLE_TOKEN_URL, data={
                    "client_id": cid, "client_secret": secret,
                    "refresh_token": refresh_token, "grant_type": "refresh_token",
                })
                resp.raise_for_status()
                token_data = resp.json()
        except ImportError:
            import urllib.request, urllib.parse
            data = urllib.parse.urlencode({
                "client_id": cid, "client_secret": secret,
                "refresh_token": refresh_token, "grant_type": "refresh_token",
            }).encode()
            req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data,
                                        headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                token_data = json.loads(resp.read())

        access_token = token_data.get("access_token", "")
        expires_in = token_data.get("expires_in", 3600)
        from pydantic import SecretStr
        cfg.access_token = SecretStr(access_token)
        cfg.token_expiry = (
            datetime.now(timezone.utc).__class__.now(timezone.utc)
        ).isoformat()

        try:
            from src.services.gdrive_settings_service import get_gdrive_settings_service
            svc = get_gdrive_settings_service()
            svc.update_token(access_token, expires_in)
        except Exception:
            pass

        return access_token

    async def _get_service_account_token(self, settings) -> str:
        sa_cfg = settings.service_account_config
        sa_json = sa_cfg.service_account_json.get_secret_value() if sa_cfg.service_account_json else ""
        if not sa_json:
            raise ValueError("Service account JSON not configured")

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as AuthRequest
            info = json.loads(sa_json)
            scopes = settings.oauth2_config.scopes if settings.oauth2_config else GOOGLE_DRIVE_UPLOAD_SCOPES
            credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            if sa_cfg.delegated_user:
                credentials = credentials.with_subject(sa_cfg.delegated_user)
            credentials.refresh(AuthRequest())
            return credentials.token
        except ImportError:
            raise ValueError("google-auth library not installed for service account auth")

    async def list_files(self, folder_id: str = "", page_token: str = "",
                         page_size: int = 100) -> Tuple[List[Dict], str]:
        settings = self._get_settings()
        token = await self._get_access_token()
        self._api_request_count += 1

        scan_cfg = settings.scan_config
        folder_ids = [folder_id] if folder_id else scan_cfg.folder_ids
        if not folder_ids:
            folder_ids = ["root"]

        all_files = []
        next_page = ""

        for fid in folder_ids:
            q_parts = [f"'{fid}' in parents", "trashed = false"]
            if scan_cfg.mime_type_filters:
                mime_clauses = " or ".join(f"mimeType = '{m}'" for m in scan_cfg.mime_type_filters)
                q_parts.append(f"({mime_clauses})")
            query = " and ".join(q_parts)

            params = {
                "q": query,
                "pageSize": min(page_size, scan_cfg.max_files_per_scan),
                "fields": "nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)",
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                import httpx
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{GOOGLE_DRIVE_API}/files",
                        params=params,
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
            except ImportError:
                import urllib.request, urllib.parse
                url = f"{GOOGLE_DRIVE_API}/files?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())

            for f in data.get("files", []):
                all_files.append({
                    "file_id": f.get("id", ""),
                    "name": f.get("name", ""),
                    "mime_type": f.get("mimeType", ""),
                    "size_bytes": int(f.get("size", 0)),
                    "created_time": f.get("createdTime"),
                    "modified_time": f.get("modifiedTime"),
                    "parent_folder_id": (f.get("parents") or [None])[0],
                    "web_view_link": f.get("webViewLink"),
                })
            next_page = data.get("nextPageToken", "")

        return all_files, next_page

    async def download_file(self, file_id: str) -> bytes:
        token = await self._get_access_token()
        self._api_request_count += 1

        try:
            import httpx
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.get(
                    f"{GOOGLE_DRIVE_API}/files/{file_id}",
                    params={"alt": "media"},
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                return resp.content
        except ImportError:
            import urllib.request
            url = f"{GOOGLE_DRIVE_API}/files/{file_id}?alt=media"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()

    async def test_connection(self) -> Dict[str, Any]:
        start = time.monotonic()
        try:
            token = await self._get_access_token()

            try:
                import httpx
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        f"{GOOGLE_DRIVE_API}/about",
                        params={"fields": "user,storageQuota"},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    resp.raise_for_status()
                    about = resp.json()
            except ImportError:
                import urllib.request
                url = f"{GOOGLE_DRIVE_API}/about?fields=user,storageQuota"
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    about = json.loads(r.read())

            user = about.get("user", {})
            latency = int((time.monotonic() - start) * 1000)

            files, _ = await self.list_files(page_size=5)

            return {
                "success": True,
                "message": f"Connected as {user.get('displayName', 'unknown')} ({user.get('emailAddress', '')})",
                "files_found": len(files),
                "latency_ms": latency,
                "details": {"user": user},
            }
        except Exception as e:
            latency = int((time.monotonic() - start) * 1000)
            self._log_error(str(e))
            return {
                "success": False,
                "message": f"Connection failed: {e}",
                "files_found": 0,
                "latency_ms": latency,
            }

    def get_diagnostics(self) -> Dict[str, Any]:
        settings = self._get_settings()
        scan_cfg = settings.scan_config

        token_status = "unknown"
        token_expires = None
        if settings.oauth2_config and settings.oauth2_config.token_expiry:
            token_expires = settings.oauth2_config.token_expiry
            try:
                expiry = datetime.fromisoformat(token_expires.replace("Z", "+00:00"))
                token_status = "valid" if expiry > datetime.now(timezone.utc) else "expired"
            except (ValueError, TypeError):
                token_status = "invalid"

        health = "healthy" if token_status == "valid" else ("degraded" if token_status == "expired" else "disconnected")

        last_sync = self._sync_history[-1] if self._sync_history else None

        return {
            "connection_health": health,
            "auth_method": settings.auth_type.value,
            "token_status": token_status,
            "token_expires_at": token_expires,
            "api_quota_daily_limit": 20000,
            "api_quota_used": self._api_request_count,
            "api_quota_remaining": max(0, 20000 - self._api_request_count),
            "folders_configured": len(scan_cfg.folder_ids),
            "total_files_discovered": sum(s.get("files_processed", 0) for s in self._sync_history),
            "files_by_type": {},
            "recent_syncs": self._sync_history[-10:],
            "recent_errors": self._error_log[-20:],
            "last_sync_at": last_sync.get("timestamp") if last_sync else None,
            "last_sync_duration_ms": last_sync.get("duration_ms") if last_sync else None,
            "last_sync_files_processed": last_sync.get("files_processed") if last_sync else None,
        }

    def record_sync(self, files_processed: int, duration_ms: int, errors: int = 0):
        self._sync_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "files_processed": files_processed,
            "duration_ms": duration_ms,
            "errors": errors,
        })
        if len(self._sync_history) > 50:
            self._sync_history = self._sync_history[-50:]


_instance: Optional[GoogleDriveConnectorService] = None


def get_gdrive_connector_service() -> GoogleDriveConnectorService:
    global _instance
    if _instance is None:
        _instance = GoogleDriveConnectorService()
    return _instance
