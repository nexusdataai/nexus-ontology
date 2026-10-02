"""
Google Drive Connector Settings Service

Persistence layer for Google Drive connector configuration.
- Foundry-workspace DynamoDB table (CONNECTORSETTING#gdrive PK) for non-sensitive
  config (folder IDs, scan schedule, feature flags)
- AWS Secrets Manager for OAuth credentials (via SecretsLoader)
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

try:
    from src.repositories.foundry_workspace_repository import (
        FoundryWorkspaceRepository,
        FoundryWorkspaceRepositoryError,
    )
    FOUNDRY_AVAILABLE = True
except ImportError:
    FOUNDRY_AVAILABLE = False
    FoundryWorkspaceRepository = None  # type: ignore
    FoundryWorkspaceRepositoryError = Exception  # type: ignore

SECRETS_LOADER_AVAILABLE = False
try:
    from src.config.secrets_loader import SecretsLoader
    SECRETS_LOADER_AVAILABLE = True
except ImportError:
    try:
        from config.secrets_loader import SecretsLoader
        SECRETS_LOADER_AVAILABLE = True
    except ImportError:
        SecretsLoader = None

from src.models.gdrive_connector_config import (
    GoogleDriveConnectorSettings,
    GDriveAuthType,
    GDriveOAuth2Config,
    GDriveScanConfig,
)

# Provider key under the CONNECTORSETTING# PK namespace in foundry-workspace.
_GDRIVE_PROVIDER = "gdrive"


class GDriveSettingsService:

    _instance: Optional['GDriveSettingsService'] = None

    def __init__(self):
        self.capability = os.getenv('CAPABILITY_NAME', 'call-processing')
        self.environment = os.getenv('ENVIRONMENT', 'dev')
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.secret_name = f"{self.capability}-{self.environment}-gdrive"
        self._settings_cache: Optional[GoogleDriveConnectorSettings] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 30
        self._foundry_available = False
        self._secrets_available = False
        self._repo: Optional[FoundryWorkspaceRepository] = None
        self._secrets_loader = None

        if FOUNDRY_AVAILABLE:
            try:
                self._repo = FoundryWorkspaceRepository()
                self._foundry_available = True
            except Exception as e:
                logger.warning(f"GDrive settings foundry-workspace not available: {e}")

            if SECRETS_LOADER_AVAILABLE:
                try:
                    self._secrets_loader = SecretsLoader(region=self.region, cache_ttl=0)
                    self._secrets_available = True
                except Exception as e:
                    logger.warning(f"GDrive SecretsLoader not available: {e}")

    @classmethod
    def get_instance(cls) -> 'GDriveSettingsService':
        if cls._instance is None:
            cls._instance = GDriveSettingsService()
        return cls._instance

    def _is_cache_valid(self) -> bool:
        if self._settings_cache is None or self._cache_timestamp is None:
            return False
        age = (datetime.now(timezone.utc) - self._cache_timestamp).total_seconds()
        return age < self._cache_ttl_seconds

    def get_settings(self, force_refresh: bool = False) -> GoogleDriveConnectorSettings:
        if not force_refresh and self._is_cache_valid():
            return self._settings_cache

        config_data: Dict[str, Any] = {}

        if self._foundry_available and self._repo:
            try:
                item = self._repo.get_connector_setting(_GDRIVE_PROVIDER)
                if item:
                    config_data = item.get('config', {}) or {}
            except Exception as e:
                logger.warning(f"GDrive foundry-workspace load failed: {e}")

        creds = self._load_credentials()
        if creds:
            if 'oauth2_config' not in config_data:
                config_data['oauth2_config'] = {}
            config_data['oauth2_config']['client_id'] = creds.get('client_id', '')
            config_data['oauth2_config']['client_secret'] = creds.get('client_secret', '')
            config_data['oauth2_config']['refresh_token'] = creds.get('refresh_token', '')
            if creds.get('service_account_json'):
                if 'service_account_config' not in config_data:
                    config_data['service_account_config'] = {}
                config_data['service_account_config']['service_account_json'] = creds['service_account_json']

        settings = self._parse_settings(config_data)
        self._settings_cache = settings
        self._cache_timestamp = datetime.now(timezone.utc)
        return settings

    def _parse_settings(self, data: dict) -> GoogleDriveConnectorSettings:
        from pydantic import SecretStr

        if 'auth_type' in data and isinstance(data['auth_type'], str):
            data['auth_type'] = GDriveAuthType(data['auth_type'])

        if 'oauth2_config' in data and isinstance(data['oauth2_config'], dict):
            oc = data['oauth2_config']
            for field in ('client_secret', 'refresh_token', 'access_token'):
                if field in oc and isinstance(oc[field], str):
                    oc[field] = SecretStr(oc[field])
            data['oauth2_config'] = GDriveOAuth2Config(**oc)

        if 'service_account_config' in data and isinstance(data['service_account_config'], dict):
            sc = data['service_account_config']
            if 'service_account_json' in sc and isinstance(sc['service_account_json'], str):
                sc['service_account_json'] = SecretStr(sc['service_account_json'])
            from src.models.gdrive_connector_config import GDriveServiceAccountConfig
            data['service_account_config'] = GDriveServiceAccountConfig(**sc)

        if 'scan_config' in data and isinstance(data['scan_config'], dict):
            data['scan_config'] = GDriveScanConfig(**data['scan_config'])

        return GoogleDriveConnectorSettings(**data)

    def _load_credentials(self) -> Optional[Dict[str, str]]:
        if not self._secrets_available or not self._secrets_loader:
            return None
        try:
            secret_data = self._secrets_loader.get_secret(self.secret_name)
            if secret_data:
                return {
                    'client_id': secret_data.get('GDRIVE_CLIENT_ID', ''),
                    'client_secret': secret_data.get('GDRIVE_CLIENT_SECRET', ''),
                    'refresh_token': secret_data.get('GDRIVE_REFRESH_TOKEN', ''),
                    'service_account_json': secret_data.get('GDRIVE_SERVICE_ACCOUNT_JSON', ''),
                }
        except Exception as e:
            logger.warning(f"GDrive secret load failed: {e}")
        return None

    def _save_credentials(self, settings: GoogleDriveConnectorSettings) -> bool:
        if not self._secrets_available or not self._secrets_loader:
            return False
        secret_data: Dict[str, str] = {}
        if settings.oauth2_config:
            oc = settings.oauth2_config
            secret_data['GDRIVE_CLIENT_ID'] = oc.client_id or ''
            secret_data['GDRIVE_CLIENT_SECRET'] = oc.client_secret.get_secret_value() if oc.client_secret else ''
            secret_data['GDRIVE_REFRESH_TOKEN'] = oc.refresh_token.get_secret_value() if oc.refresh_token else ''
        if settings.service_account_config:
            sc = settings.service_account_config
            secret_data['GDRIVE_SERVICE_ACCOUNT_JSON'] = (
                sc.service_account_json.get_secret_value() if sc.service_account_json else ''
            )
        try:
            return self._secrets_loader.put_secret(
                secret_name=self.secret_name,
                secret_string=json.dumps(secret_data),
                description="Google Drive connector credentials",
            )
        except Exception as e:
            logger.error(f"GDrive secret save failed: {e}")
            return False

    def update_settings(self, **kwargs) -> GoogleDriveConnectorSettings:
        current = self.get_settings(force_refresh=True)
        for key, value in kwargs.items():
            if value is not None and hasattr(current, key):
                setattr(current, key, value)
        current.last_updated = datetime.now(timezone.utc)

        self._save_credentials(current)

        if self._foundry_available and self._repo:
            try:
                config_dict = {
                    'auth_type': current.auth_type.value,
                    'enable_auto_scan': current.enable_auto_scan,
                    'enable_ocr_extraction': current.enable_ocr_extraction,
                    'scan_schedule': current.scan_schedule,
                }
                if current.scan_config:
                    config_dict['scan_config'] = {
                        'folder_ids': current.scan_config.folder_ids,
                        'mime_type_filters': current.scan_config.mime_type_filters,
                        'max_files_per_scan': current.scan_config.max_files_per_scan,
                        'include_subfolders': current.scan_config.include_subfolders,
                    }
                self._repo.put_connector_setting(
                    _GDRIVE_PROVIDER,
                    {
                        'config': config_dict,
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as e:
                logger.warning(f"GDrive foundry-workspace save failed: {e}")

        self._settings_cache = current
        self._cache_timestamp = datetime.now(timezone.utc)
        return current

    def update_token(self, access_token: str, expires_in: int):
        from pydantic import SecretStr
        settings = self.get_settings()
        if settings.oauth2_config:
            settings.oauth2_config.access_token = SecretStr(access_token)
            from datetime import timedelta
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            settings.oauth2_config.token_expiry = expiry.isoformat()
            self._settings_cache = settings
            self._cache_timestamp = datetime.now(timezone.utc)


_instance: Optional[GDriveSettingsService] = None


def get_gdrive_settings_service() -> GDriveSettingsService:
    return GDriveSettingsService.get_instance()
