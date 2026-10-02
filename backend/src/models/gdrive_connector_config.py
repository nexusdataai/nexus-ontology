"""
Google Drive Connector Configuration Models

Pydantic models for configuring Google Drive integration.
Supports OAuth2 and Service Account authentication.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, SecretStr
from enum import Enum


class GDriveAuthType(str, Enum):
    OAUTH2 = "oauth2"
    SERVICE_ACCOUNT = "service_account"


class GDriveOAuth2Config(BaseModel):
    client_id: str = Field(default="", description="Google OAuth2 client ID")
    client_secret: SecretStr = Field(default=SecretStr(""), description="Google OAuth2 client secret")
    refresh_token: SecretStr = Field(default=SecretStr(""), description="OAuth2 refresh token")
    access_token: SecretStr = Field(default=SecretStr(""), description="Current access token (auto-managed)")
    token_expiry: Optional[str] = Field(default=None, description="Access token expiry ISO timestamp")
    redirect_uri: str = Field(
        default="http://localhost:3000/gdrive/callback",
        description="OAuth2 redirect URI"
    )
    scopes: List[str] = Field(
        default=["https://www.googleapis.com/auth/drive.readonly"],
        description="OAuth2 scopes"
    )


class GDriveServiceAccountConfig(BaseModel):
    service_account_json: SecretStr = Field(
        default=SecretStr(""),
        description="Service account key JSON (entire file contents)"
    )
    delegated_user: str = Field(default="", description="User email for domain-wide delegation")


class GDriveScanConfig(BaseModel):
    folder_ids: List[str] = Field(default=[], description="Google Drive folder IDs to scan")
    mime_type_filters: List[str] = Field(
        default=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/csv",
        ],
        description="MIME types to include"
    )
    max_files_per_scan: int = Field(default=100, description="Max files to process per scan run")
    include_subfolders: bool = Field(default=True, description="Recurse into subfolders")


class GoogleDriveConnectorSettings(BaseModel):
    auth_type: GDriveAuthType = Field(default=GDriveAuthType.OAUTH2, description="Authentication method")
    oauth2_config: Optional[GDriveOAuth2Config] = Field(default=None)
    service_account_config: Optional[GDriveServiceAccountConfig] = Field(default=None)
    scan_config: GDriveScanConfig = Field(default_factory=GDriveScanConfig)
    enable_auto_scan: bool = Field(default=False, description="Enable automatic periodic scanning")
    enable_ocr_extraction: bool = Field(default=True, description="Run OCR+LLM extraction on downloaded files")
    scan_schedule: str = Field(default="0 */6 * * *", description="Cron schedule for auto-scan")
    last_updated: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None,
            SecretStr: lambda v: "********" if v else None,
        }


class GDriveConnectorStatusResponse(BaseModel):
    connected: bool = False
    auth_type: Optional[str] = None
    token_valid: bool = False
    token_expires_at: Optional[str] = None
    folders_configured: int = 0
    last_scan_at: Optional[str] = None
    total_files_indexed: int = 0
    error: Optional[str] = None


class GDriveFileInfo(BaseModel):
    file_id: str
    name: str
    mime_type: str
    size_bytes: int = 0
    created_time: Optional[str] = None
    modified_time: Optional[str] = None
    parent_folder_id: Optional[str] = None
    web_view_link: Optional[str] = None


class GDriveDiagnostics(BaseModel):
    connection_health: str = "unknown"
    auth_method: Optional[str] = None
    token_status: str = "unknown"
    token_expires_at: Optional[str] = None
    api_quota_daily_limit: int = 20000
    api_quota_used: int = 0
    api_quota_remaining: int = 20000
    folders_configured: int = 0
    total_files_discovered: int = 0
    files_by_type: Dict[str, int] = Field(default_factory=dict)
    recent_syncs: List[Dict] = Field(default_factory=list)
    recent_errors: List[Dict] = Field(default_factory=list)
    last_sync_at: Optional[str] = None
    last_sync_duration_ms: Optional[int] = None
    last_sync_files_processed: Optional[int] = None


class UpdateGDriveSettingsRequest(BaseModel):
    auth_type: Optional[GDriveAuthType] = None
    oauth2_config: Optional[GDriveOAuth2Config] = None
    service_account_config: Optional[GDriveServiceAccountConfig] = None
    scan_config: Optional[GDriveScanConfig] = None
    enable_auto_scan: Optional[bool] = None
    enable_ocr_extraction: Optional[bool] = None
    scan_schedule: Optional[str] = None


class GDriveTestResponse(BaseModel):
    success: bool
    message: str
    files_found: int = 0
    latency_ms: Optional[int] = None
    details: Optional[Dict] = None
