"""
SSM Parameter and Secrets Management Service

Centralized service for SSM parameter and secrets operations with validation,
categorization, and audit logging. Used by the config API for UI-based
parameter management.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Capability name (overridable via CAPABILITY_NAME env var; default preserves legacy behavior)
CAPABILITY_NAME = os.getenv("CAPABILITY_NAME", "call-processing")


# =============================================================================
# Parameter Categories Schema
# =============================================================================

PARAMETER_CATEGORIES = {
    "server": {
        "label": "Server Configuration",
        "description": "Gateway and server settings",
        "icon": "server",
        "parameters": {
            "log-level": {
                "description": "Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
                "default": "INFO",
                "type": "select",
                "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                "env_var": "LOG_LEVEL"
            },
            "gateway-port": {
                "description": "HTTP gateway port",
                "default": "8000",
                "type": "number",
                "env_var": "GATEWAY_PORT"
            },
            "min-workers": {
                "description": "Minimum worker pool size",
                "default": "2",
                "type": "number",
                "env_var": "MIN_WORKERS"
            },
            "max-workers": {
                "description": "Maximum worker pool size",
                "default": "8",
                "type": "number",
                "env_var": "MAX_WORKERS"
            },
            "timeout": {
                "description": "Request timeout in seconds",
                "default": "60.0",
                "type": "number",
                "env_var": "MCP_REQUEST_TIMEOUT"
            }
        }
    },
    "cognito": {
        "label": "Authentication (Cognito)",
        "description": "AWS Cognito OAuth settings",
        "icon": "shield",
        "parameters": {
            "region": {
                "description": "Cognito region",
                "default": "us-east-1",
                "type": "text",
                "env_var": "COGNITO_REGION"
            },
            "user-pool-id": {
                "description": "Cognito User Pool ID",
                "default": "",
                "type": "text",
                "env_var": "COGNITO_USER_POOL_ID"
            },
            "app-client-id": {
                "description": "Cognito App Client ID",
                "default": "",
                "type": "text",
                "env_var": "COGNITO_APP_CLIENT_ID"
            },
            "domain": {
                "description": "Cognito domain for OAuth",
                "default": "",
                "type": "text",
                "env_var": "COGNITO_DOMAIN"
            },
            "redirect-uri": {
                "description": "OAuth redirect URI (callback URL)",
                "default": "",
                "type": "text",
                "env_var": "COGNITO_REDIRECT_URI"
            }
        }
    },
    "wxcc-query": {
        "label": "WXCC Query",
        "description": "Webex Contact Center query filters for call processing",
        "icon": "search",
        "parameters": {
            "time-value": {
                "description": "How far back to query calls (numeric value)",
                "default": "30",
                "type": "number",
                "env_var": "WXCC_QUERY_TIME_VALUE"
            },
            "time-unit": {
                "description": "Time unit for the query lookback period",
                "default": "minutes",
                "type": "select",
                "options": ["minutes", "hours", "days"],
                "env_var": "WXCC_QUERY_TIME_UNIT"
            },
            "queue-name": {
                "description": "Filter by queue name (exact match, leave empty to skip)",
                "default": "",
                "type": "text",
                "env_var": "WXCC_QUERY_QUEUE_NAME"
            },
            "site-name": {
                "description": "Filter by site name (exact match, leave empty to skip)",
                "default": "",
                "type": "text",
                "env_var": "WXCC_QUERY_SITE_NAME"
            },
            "team-name": {
                "description": "Filter by team name (exact match, leave empty to skip)",
                "default": "",
                "type": "text",
                "env_var": "WXCC_QUERY_TEAM_NAME"
            },
            "agent-name": {
                "description": "Filter by agent name (exact match, leave empty to skip)",
                "default": "",
                "type": "text",
                "env_var": "WXCC_QUERY_AGENT_NAME"
            }
        }
    },
    "wxcc": {
        "label": "WXCC Simulator",
        "description": "Webex Contact Center simulator settings",
        "icon": "phone",
        "parameters": {
            "enabled": {
                "description": "Enable WXCC simulator mode",
                "default": "true",
                "type": "boolean",
                "env_var": "WXCC_SIMULATOR_ENABLED"
            },
            "bucket": {
                "description": "S3 bucket for simulator data",
                "default": "nexus-ai-{env}-wxcc-simulator-{account}",
                "type": "text",
                "env_var": "WXCC_SIMULATOR_BUCKET"
            },
            "prefix": {
                "description": "S3 prefix for simulator data",
                "default": "wxcc-simulator",
                "type": "text",
                "env_var": "WXCC_SIMULATOR_PREFIX"
            },
            "org-id": {
                "description": "Simulated organization ID",
                "default": "sim-org-001",
                "type": "text",
                "env_var": "WXCC_SIM_ORG_ID"
            }
        }
    },
    "data_source_mode": {
        "label": "Data Source Mode",
        "description": "Per-source routing for ReAct tools and the Virtual Data Layer. 'simulator' uses the in-memory simulator; 'real' uses the live FDW connection. Default is 'simulator' on a fresh deploy. Real mode is explicit opt-in. The three external sub-sources (file_uploads, google_drive, social_listening) currently share a single backing simulator, but each carries its own toggle so future per-connector real-mode routing can be enabled independently.",
        "icon": "database",
        "parameters": {
            "sfdc": {
                "description": "Salesforce mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_SFDC"
            },
            "oracle": {
                "description": "Oracle ERP mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_ORACLE"
            },
            "sap": {
                "description": "SAP S/4HANA mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_SAP"
            },
            "file_uploads": {
                "description": "File Uploads (invoices / lab reports / CSV) mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_FILE_UPLOADS"
            },
            "google_drive": {
                "description": "Google Drive (contracts / reports / documents) mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_GOOGLE_DRIVE"
            },
            "social_listening": {
                "description": "Social Listening (market signals / sentiment) mode (simulator | real)",
                "default": "simulator",
                "type": "select",
                "options": ["simulator", "real"],
                "env_var": "DATA_SOURCE_MODE_SOCIAL_LISTENING"
            }
        }
    },
    "sfdc": {
        "label": "SFDC Simulator",
        "description": "Salesforce FDW simulator settings",
        "icon": "database",
        "parameters": {
            "enabled": {
                "description": "[DEPRECATED] Use 'Data Source Mode > sfdc' instead. Legacy boolean kept for backward compat (auto-migrated on first read).",
                "default": "false",
                "type": "boolean",
                "env_var": "SFDC_SIMULATOR_ENABLED"
            },
            "bucket": {
                "description": "S3 bucket for SFDC simulator data dumps",
                "default": "nexus-ai-{env}-sfdc-simulator-{account}",
                "type": "text",
                "env_var": "SFDC_SIMULATOR_BUCKET"
            },
            "prefix": {
                "description": "S3 prefix for SFDC simulator data",
                "default": "sfdc-simulator",
                "type": "text",
                "env_var": "SFDC_SIMULATOR_PREFIX"
            }
        }
    },
    "oracle-erp": {
        "label": "Oracle ERP Simulator",
        "description": "Oracle ERP simulator settings (finance and operations)",
        "icon": "building",
        "parameters": {
            "enabled": {
                "description": "[DEPRECATED] Use 'Data Source Mode > oracle' instead. Legacy boolean kept for backward compat (auto-migrated on first read).",
                "default": "false",
                "type": "boolean",
                "env_var": "ORACLE_ERP_SIMULATOR_ENABLED"
            },
            "bucket": {
                "description": "S3 bucket for Oracle ERP simulator data",
                "default": "nexus-ai-{env}-oracle-erp-simulator-{account}",
                "type": "text",
                "env_var": "ORACLE_ERP_SIMULATOR_BUCKET"
            },
            "prefix": {
                "description": "S3 prefix for Oracle ERP simulator data",
                "default": "oracle-erp-simulator",
                "type": "text",
                "env_var": "ORACLE_ERP_SIMULATOR_PREFIX"
            }
        }
    },
    "sap": {
        "label": "SAP Simulator",
        "description": "SAP S/4HANA simulator settings (supply chain, inventory, production)",
        "icon": "factory",
        "parameters": {
            "enabled": {
                "description": "[DEPRECATED] Use 'Data Source Mode > sap' instead. Legacy boolean kept for backward compat (auto-migrated on first read).",
                "default": "false",
                "type": "boolean",
                "env_var": "SAP_SIMULATOR_ENABLED"
            },
            "bucket": {
                "description": "S3 bucket for SAP simulator data",
                "default": "nexus-ai-{env}-sap-simulator-{account}",
                "type": "text",
                "env_var": "SAP_SIMULATOR_BUCKET"
            },
            "prefix": {
                "description": "S3 prefix for SAP simulator data",
                "default": "sap-simulator",
                "type": "text",
                "env_var": "SAP_SIMULATOR_PREFIX"
            }
        }
    },
    "s3": {
        "label": "S3 Storage",
        "description": "S3 bucket configurations",
        "icon": "database",
        "parameters": {
            "recordings-bucket": {
                "description": "S3 bucket for call recordings and data",
                "default": "call-processing-{env}-call-data-{account}",
                "type": "text",
                "env_var": "S3_RECORDINGS_BUCKET"
            },
            "journey-logs-bucket": {
                "description": "S3 bucket for journey execution logs",
                "default": "call-processing-{env}-journey-logs-{account}",
                "type": "text",
                "env_var": "S3_JOURNEY_LOGS_BUCKET"
            },
            "journey-reports-bucket": {
                "description": "S3 bucket for journey reports",
                "default": "call-processing-{env}-journey-reports-{account}",
                "type": "text",
                "env_var": "S3_JOURNEY_REPORTS_BUCKET"
            }
        }
    },
    "dynamodb": {
        "label": "DynamoDB Tables",
        "description": "DynamoDB table names",
        "icon": "table",
        "parameters": {
            "transformation-table": {
                "description": "Main transformation system table",
                "default": "call-processing-{env}-transformation-system",
                "type": "text",
                "env_var": "DYNAMODB_TABLE"
            },
            "license-table": {
                "description": "License management table",
                "default": "call-processing-{env}-license",
                "type": "text",
                "env_var": "LICENSE_TABLE"
            },
            "foundry-workspace-table": {
                "description": "Foundry workspace single-table (Solutions, Tools, Data Planes, Connectors, Mapping Rules, VDL Entities)",
                "default": "call-processing-{env}-foundry-workspace",
                "type": "text",
                "env_var": "DYNAMODB_FOUNDRY_WORKSPACE_TABLE"
            },
            "control-plane-audit-table": {
                "description": "Control-plane audit trail (agent tool-call audit)",
                "default": "call-processing-{env}-control-plane-audit",
                "type": "text",
                "env_var": "CONTROL_PLANE_AUDIT_TABLE"
            },
            "rbac-table": {
                "description": "RBAC config table",
                "default": "call-processing-{env}-rbac",
                "type": "text",
                "env_var": "RBAC_TABLE"
            }
        }
    },
    "glue": {
        "label": "AWS Glue",
        "description": "Glue database settings",
        "icon": "layers",
        "parameters": {
            "database": {
                "description": "Glue database name",
                "default": "call-processing-{env}-analytics",
                "type": "text",
                "env_var": "GLUE_DATABASE_NAME"
            }
        }
    },
    "cloudwatch": {
        "label": "CloudWatch Logging",
        "description": "CloudWatch log configuration",
        "icon": "activity",
        "parameters": {
            "log-group": {
                "description": "CloudWatch log group",
                "default": "/aws/call-processing/{env}",
                "type": "text",
                "env_var": "CLOUDWATCH_LOG_GROUP"
            },
            "stream-prefix": {
                "description": "Log stream prefix",
                "default": "script",
                "type": "text",
                "env_var": "CLOUDWATCH_LOG_STREAM_PREFIX"
            }
        }
    }
}


# =============================================================================
# Secrets Schema
# =============================================================================

SECRETS_SCHEMA = {
    "api-keys": {
        "label": "API Keys",
        "description": "Gateway authentication keys",
        "keys": ["API_KEY"],
        "managed_by": None  # Managed directly
    },
    "openai": {
        "label": "OpenAI",
        "description": "OpenAI API key for AI analysis",
        "keys": ["OPENAI_API_KEY"],
        "managed_by": None
    },
    "license": {
        "label": "License Keys",
        "description": "License verification keys",
        "keys": ["LICENSE_PUBLIC_KEY", "LICENSE_PRIVATE_KEY"],
        "managed_by": None
    },
    "wxcc": {
        "label": "WXCC Tokens",
        "description": "Webex Contact Center tokens",
        "keys": ["WXCC_SIM_TOKEN"],
        "managed_by": "webex-connector"  # Managed via Webex Connector
    },
    "anthropic": {
        "label": "Anthropic",
        "description": "Claude API keys (optional)",
        "keys": ["CLAUDE_API_KEY", "ANTHROPIC_API_KEY"],
        "managed_by": None
    },
    "github": {
        "label": "GitHub",
        "description": "GitHub personal access token (optional)",
        "keys": ["GITHUB_TOKEN"],
        "managed_by": None
    }
}


@dataclass
class ParameterValue:
    """Represents a parameter with its value and metadata."""
    value: str
    default: str
    description: str
    type: str
    env_var: str
    modified: bool = False
    options: Optional[List[str]] = None


@dataclass
class SecretInfo:
    """Represents secret metadata without the actual value."""
    name: str
    label: str
    description: str
    keys: List[str]
    managed_by: Optional[str]
    last_modified: Optional[str] = None


class SSMService:
    """
    Service for managing SSM parameters and secrets.
    
    Provides CRUD operations for SSM parameters with category-based
    organization and secrets management with value masking.
    """
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize the SSM service.
        
        Args:
            region: AWS region (defaults to config or us-east-1)
        """
        from src.config.config_provider import get_config, detect_environment
        
        self.config = get_config()
        self.environment = detect_environment()
        self.region = region or self.config.aws_region
        
        self._ssm_loader = None
        self._secrets_loader = None
    
    @property
    def ssm_loader(self):
        """Lazy-load SSM loader."""
        if self._ssm_loader is None:
            from src.config.ssm_loader import SSMParameterLoader
            self._ssm_loader = SSMParameterLoader(region=self.region)
        return self._ssm_loader
    
    @property
    def secrets_loader(self):
        """Lazy-load secrets loader."""
        if self._secrets_loader is None:
            from src.config.secrets_loader import SecretsLoader
            self._secrets_loader = SecretsLoader(region=self.region)
        return self._secrets_loader
    
    def _get_parameter_path(self, category: str, name: str) -> str:
        """Build full SSM parameter path."""
        return f"/{CAPABILITY_NAME}/{self.environment}/{category}/{name}"
    
    def _get_secret_name(self, name: str) -> str:
        """Build full secret name."""
        return f"{CAPABILITY_NAME}/{self.environment}/{name}"
    
    def _resolve_default(self, default: str) -> str:
        """Resolve {env} and {account} placeholders in default values."""
        result = default.replace("{env}", self.environment)
        if "{account}" in result:
            result = result.replace("{account}", self._get_account_id())
        return result
    
    def _get_account_id(self) -> str:
        """Get AWS account ID via STS, cached after first call."""
        if not hasattr(self, '_account_id'):
            try:
                import boto3
                sts = boto3.client("sts", region_name=self.region)
                self._account_id = sts.get_caller_identity()["Account"]
            except Exception:
                self._account_id = "{account}"
        return self._account_id
    
    # =========================================================================
    # Parameter Operations
    # =========================================================================
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the parameter schema with categories and metadata.
        
        Returns:
            Schema dictionary with categories and parameter definitions
        """
        return {
            "environment": self.environment,
            "capability": CAPABILITY_NAME,
            "categories": PARAMETER_CATEGORIES,
            "secrets": SECRETS_SCHEMA
        }
    
    def get_all_parameters(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all parameters, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            Dictionary with environment and categories containing parameters
        """
        result = {
            "environment": self.environment,
            "categories": {}
        }
        
        # Filter categories if specified
        categories = {category: PARAMETER_CATEGORIES[category]} if category and category in PARAMETER_CATEGORIES else PARAMETER_CATEGORIES
        
        for cat_name, cat_info in categories.items():
            cat_result = {
                "label": cat_info["label"],
                "description": cat_info["description"],
                "icon": cat_info.get("icon", "settings"),
                "parameters": {}
            }
            
            for param_name, param_info in cat_info["parameters"].items():
                path = self._get_parameter_path(cat_name, param_name)
                default = self._resolve_default(param_info["default"])
                
                # Try to get value from SSM
                value = self.ssm_loader.get_parameter(path)
                
                # Fall back to environment variable if SSM not available
                if value is None:
                    value = os.getenv(param_info["env_var"], default)
                
                cat_result["parameters"][param_name] = {
                    "value": value or default,
                    "default": default,
                    "description": param_info["description"],
                    "type": param_info["type"],
                    "env_var": param_info["env_var"],
                    "modified": value is not None and value != default,
                    "options": param_info.get("options")
                }
            
            result["categories"][cat_name] = cat_result
        
        return result
    
    def get_parameter(self, category: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a single parameter.
        
        Args:
            category: Parameter category
            name: Parameter name
            
        Returns:
            Parameter value and metadata, or None if not found
        """
        if category not in PARAMETER_CATEGORIES:
            return None
        
        if name not in PARAMETER_CATEGORIES[category]["parameters"]:
            return None
        
        param_info = PARAMETER_CATEGORIES[category]["parameters"][name]
        path = self._get_parameter_path(category, name)
        default = self._resolve_default(param_info["default"])
        
        value = self.ssm_loader.get_parameter(path)
        if value is None:
            value = os.getenv(param_info["env_var"], default)
        
        return {
            "value": value or default,
            "default": default,
            "description": param_info["description"],
            "type": param_info["type"],
            "env_var": param_info["env_var"],
            "modified": value is not None and value != default,
            "options": param_info.get("options"),
            "path": path
        }
    
    def set_parameter(
        self,
        category: str,
        name: str,
        value: str,
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set/update a parameter value.
        
        Args:
            category: Parameter category
            name: Parameter name
            value: New value
            user: User making the change (for audit)
            
        Returns:
            Result with previous and new values
        """
        if category not in PARAMETER_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        
        if name not in PARAMETER_CATEGORIES[category]["parameters"]:
            raise ValueError(f"Invalid parameter: {name} in category {category}")
        
        param_info = PARAMETER_CATEGORIES[category]["parameters"][name]
        path = self._get_parameter_path(category, name)
        
        # Get previous value
        previous_value = self.ssm_loader.get_parameter(path)
        if previous_value is None:
            previous_value = os.getenv(param_info["env_var"], param_info["default"])
        
        # Validate value based on type
        self._validate_parameter_value(param_info, value)
        
        # Set the parameter
        success = self.ssm_loader.put_parameter(
            name=path,
            value=value,
            description=f"{param_info['description']} (updated via UI)",
            overwrite=True
        )
        
        if success:
            # Also update environment variable for immediate effect
            os.environ[param_info["env_var"]] = value
            
            # Invalidate cache for this path
            self.ssm_loader.invalidate_path(f"/{CAPABILITY_NAME}/{self.environment}/")
            
            logger.info(f"Parameter {path} updated by {user}: {previous_value} -> {value}")
        
        return {
            "status": "success" if success else "error",
            "path": path,
            "previous_value": previous_value,
            "new_value": value,
            "updated_by": user,
            "timestamp": datetime.now().isoformat()
        }
    
    def _validate_parameter_value(self, param_info: Dict, value: str) -> None:
        """Validate parameter value based on type."""
        param_type = param_info["type"]
        
        if param_type == "select":
            options = param_info.get("options", [])
            if value not in options:
                raise ValueError(f"Value must be one of: {', '.join(options)}")
        
        elif param_type == "number":
            try:
                float(value)
            except ValueError:
                raise ValueError(f"Value must be a number")
        
        elif param_type == "boolean":
            if value.lower() not in ("true", "false"):
                raise ValueError("Value must be 'true' or 'false'")
    
    # =========================================================================
    # Secrets Operations
    # =========================================================================
    
    def get_secrets_list(self) -> List[Dict[str, Any]]:
        """
        Get list of available secrets with metadata (no values).
        
        Returns:
            List of secret metadata
        """
        secrets = []
        
        for secret_name, secret_info in SECRETS_SCHEMA.items():
            full_name = self._get_secret_name(secret_name)
            
            # Try to get metadata
            metadata = self.secrets_loader.describe_secret(full_name)
            
            secrets.append({
                "name": secret_name,
                "label": secret_info["label"],
                "description": secret_info["description"],
                "keys": secret_info["keys"],
                "managed_by": secret_info["managed_by"],
                "exists": metadata is not None,
                "last_modified": metadata.get("last_modified") if metadata else None
            })
        
        return secrets
    
    def get_secret(self, name: str, mask: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a secret with optionally masked values.
        
        Args:
            name: Secret name (without prefix)
            mask: Whether to mask the values
            
        Returns:
            Secret metadata with masked/unmasked values
        """
        if name not in SECRETS_SCHEMA:
            return None
        
        secret_info = SECRETS_SCHEMA[name]
        full_name = self._get_secret_name(name)
        
        # Get secret value
        secret_data = self.secrets_loader.get_secret(full_name, parse_json=True)
        
        if secret_data is None:
            return {
                "name": name,
                "label": secret_info["label"],
                "description": secret_info["description"],
                "keys": secret_info["keys"],
                "managed_by": secret_info["managed_by"],
                "exists": False,
                "values": {key: None for key in secret_info["keys"]}
            }
        
        # Mask or return values
        if mask and isinstance(secret_data, dict):
            masked_values = {}
            for key in secret_info["keys"]:
                value = secret_data.get(key)
                if value:
                    # Show first 4 and last 4 characters
                    if len(value) > 12:
                        masked_values[key] = f"{value[:4]}{'*' * 8}{value[-4:]}"
                    else:
                        masked_values[key] = "*" * len(value)
                else:
                    masked_values[key] = None
            values = masked_values
        else:
            values = secret_data if isinstance(secret_data, dict) else {secret_info["keys"][0]: secret_data}
        
        return {
            "name": name,
            "label": secret_info["label"],
            "description": secret_info["description"],
            "keys": secret_info["keys"],
            "managed_by": secret_info["managed_by"],
            "exists": True,
            "values": values
        }
    
    def set_secret(
        self,
        name: str,
        values: Dict[str, str],
        user: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Set/update a secret.
        
        Args:
            name: Secret name (without prefix)
            values: Dictionary of key-value pairs
            user: User making the change (for audit)
            
        Returns:
            Result status
        """
        if name not in SECRETS_SCHEMA:
            raise ValueError(f"Invalid secret: {name}")
        
        secret_info = SECRETS_SCHEMA[name]
        
        # Check if managed by another component
        if secret_info["managed_by"]:
            raise ValueError(f"Secret '{name}' is managed by {secret_info['managed_by']}. Please use that component to update it.")
        
        full_name = self._get_secret_name(name)
        
        # Get existing secret to merge values
        existing = self.secrets_loader.get_secret(full_name, parse_json=True)
        if isinstance(existing, dict):
            merged = {**existing, **values}
        else:
            merged = values
        
        # Set the secret
        import json
        success = self.secrets_loader.put_secret(full_name, json.dumps(merged))
        
        if success:
            # Invalidate cache
            self.secrets_loader.invalidate_secret(full_name)
            
            logger.info(f"Secret {full_name} updated by {user}")
        
        return {
            "status": "success" if success else "error",
            "name": name,
            "updated_keys": list(values.keys()),
            "updated_by": user,
            "timestamp": datetime.now().isoformat()
        }
    
    # =========================================================================
    # Cache Operations
    # =========================================================================
    
    def invalidate_cache(self) -> Dict[str, Any]:
        """
        Invalidate all SSM and secrets caches.
        
        Returns:
            Result status
        """
        self.ssm_loader.clear_cache()
        self.secrets_loader.clear_cache()
        
        logger.info("SSM and Secrets caches invalidated")
        
        return {
            "status": "success",
            "message": "All caches invalidated",
            "timestamp": datetime.now().isoformat()
        }


# Global service instance
_ssm_service: Optional[SSMService] = None


def get_ssm_service() -> SSMService:
    """Get the global SSM service instance."""
    global _ssm_service
    if _ssm_service is None:
        _ssm_service = SSMService()
    return _ssm_service
