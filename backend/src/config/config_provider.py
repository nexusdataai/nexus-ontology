"""
Configuration Provider for Call Processing Capability

Central configuration management that loads settings from:
- SSM Parameter Store (on ECS/AWS)
- Secrets Manager (for sensitive values)
- .env.local files (for local development)
- Environment variables (fallback)

Resource names follow the pattern: call-processing-{env}-{name}

Configuration Loading Strategy:
================================
1. ECS Platform: Load from SSM Parameter Store and Secrets Manager
2. LocalStack Mode: Load from .env.local + environment variables
3. Local Development: Load from .env.local + environment variables

The runtime environment is auto-detected based on:
- ECS_CONTAINER_METADATA_URI (for ECS)
- USE_LOCALSTACK=true (for LocalStack)
- Otherwise: local development
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)

# Capability name (overridable via CAPABILITY_NAME env var; default preserves legacy behavior)
CAPABILITY_NAME = os.getenv("CAPABILITY_NAME", "call-processing")

# =============================================================================
# Load .env.local for Local Development (before any other config access)
# =============================================================================

def _load_env_local():
    """
    Load environment variables from .env.local for local development.
    
    This is called at module import time to ensure environment variables
    are available before any other configuration is accessed.
    
    Loading priority:
    1. Already-set environment variables (highest priority)
    2. .env.local (single source of truth for local development)
    
    Skipped when running on ECS (environment comes from task definition + SSM).
    """
    # Skip if running on ECS - config comes from SSM
    if os.getenv('ECS_CONTAINER_METADATA_URI') or os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return
    
    # Find project root (go up from src/config/)
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env.local"
    
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
            logger.debug(f"Loaded environment from: {env_file}")
        except Exception as e:
            logger.warning(f"Failed to load {env_file}: {e}")
    else:
        logger.warning(f"No .env.local found at {env_file} - using system environment only")

# Load .env.local at module import time
_load_env_local()

# Valid environments
VALID_ENVIRONMENTS = {"dev", "stage", "test", "prod", "local"}


def detect_environment() -> str:
    """
    Detect the current runtime environment.
    
    Priority:
    1. Explicit ENVIRONMENT variable (set in ECS task definition)
    2. Check if running on ECS (default to prod)
    3. LocalStack mode (use 'local')
    4. Default to 'dev'
    
    Returns:
        Environment string: dev, stage, test, prod, or local
    """
    # 1. Explicit ENVIRONMENT variable
    env = os.getenv('ENVIRONMENT', '').strip().lower()
    if env and env in VALID_ENVIRONMENTS:
        return env
    
    # 2. Check if running on ECS
    if os.getenv('ECS_CONTAINER_METADATA_URI') or os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return 'prod'
    
    # 3. LocalStack mode
    if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
        return 'local'
    
    # 4. Default to dev
    return 'dev'


def is_aws_environment() -> bool:
    """
    Check if running in an AWS environment that should use SSM/Secrets Manager.
    
    Returns True when running on ECS or EKS (IRSA).
    When running locally with AWS credentials, config comes from .env.local.
    
    Returns:
        True if running on ECS or EKS platform
    """
    # ECS platform
    if os.getenv('ECS_CONTAINER_METADATA_URI') or os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return True
    
    # EKS platform (IRSA - IAM Roles for Service Accounts)
    if os.getenv('AWS_WEB_IDENTITY_TOKEN_FILE'):
        return True
    
    # LocalStack mode - use .env.local
    if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
        return False
    
    # Local development with AWS credentials - still use .env.local for config
    return False


@dataclass
class ConfigProvider:
    """
    Central configuration provider for the call-processing capability.
    
    Loads configuration from SSM Parameter Store and Secrets Manager on AWS,
    or from environment variables when running locally/LocalStack.
    """
    
    environment: str = field(default_factory=detect_environment)
    _ssm_params: Dict[str, str] = field(default_factory=dict, repr=False)
    _secrets: Dict[str, Any] = field(default_factory=dict, repr=False)
    _initialized: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """Initialize configuration after dataclass creation."""
        if not self._initialized:
            self._load_configuration()
            self._initialized = True
    
    def _load_configuration(self):
        """Load configuration from appropriate sources."""
        logger.info(f"Loading configuration for environment: {self.environment}")
        
        if is_aws_environment() and self.environment != 'local':
            self._load_from_aws()
        else:
            self._load_from_environment()
    
    def _load_from_aws(self):
        """Load configuration from SSM Parameter Store and Secrets Manager."""
        try:
            import time as _time
            from .ssm_loader import SSMParameterLoader
            from .secrets_loader import SecretsLoader
            
            # Load SSM parameters (with retry for IAM propagation after fresh deployment)
            ssm_loader = SSMParameterLoader(region=self.aws_region)
            ssm_path = os.getenv('SSM_PARAMETER_PREFIX') or f"/{CAPABILITY_NAME}/{self.environment}/"
            if not ssm_path.startswith('/'):
                ssm_path = f"/{ssm_path}"
            if not ssm_path.endswith('/'):
                ssm_path = f"{ssm_path}/"
            self._ssm_params = ssm_loader.load_parameters_by_path(ssm_path)
            
            # Retry if SSM returned 0 params (IAM role may not have propagated yet)
            if not self._ssm_params:
                for attempt in range(3):
                    wait_secs = (attempt + 1) * 5
                    logger.warning(f"SSM returned 0 params, retrying in {wait_secs}s (attempt {attempt + 1}/3)...")
                    _time.sleep(wait_secs)
                    ssm_loader._cache.clear()  # Clear cache to force re-fetch
                    self._ssm_params = ssm_loader.load_parameters_by_path(ssm_path)
                    if self._ssm_params:
                        break
            
            logger.info(f"Loaded {len(self._ssm_params)} SSM parameters from {ssm_path}")
            
            # Load secrets
            secrets_loader = SecretsLoader(region=self.aws_region)
            secrets_prefix = os.getenv('SECRETS_PREFIX') or f"{CAPABILITY_NAME}/{self.environment}/"
            secrets_prefix = secrets_prefix.rstrip('/')
            secret_names = [
                f"{secrets_prefix}/api-keys",
                f"{secrets_prefix}/openai",
                f"{secrets_prefix}/license",
                f"{secrets_prefix}/wxcc",
            ]
            for secret_name in secret_names:
                try:
                    secret_value = secrets_loader.get_secret(secret_name)
                    if secret_value:
                        self._secrets[secret_name] = secret_value
                except Exception as e:
                    logger.warning(f"Could not load secret {secret_name}: {e}")
            
            logger.info(f"Loaded {len(self._secrets)} secrets")
            
        except ImportError as e:
            logger.warning(f"AWS loaders not available, falling back to environment: {e}")
            self._load_from_environment()
        except Exception as e:
            logger.warning(f"Failed to load from AWS, falling back to environment: {e}")
            self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        logger.info("Loading configuration from environment variables")
        # Environment variables are accessed directly via properties
        # This method is a placeholder for any env-based initialization
    
    def _get_ssm_param(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a value from SSM parameters cache."""
        return self._ssm_params.get(key, default)
    
    def _get_secret(self, secret_name: str, key: Optional[str] = None) -> Optional[str]:
        """Get a value from secrets cache."""
        secrets_prefix = os.getenv('SECRETS_PREFIX', f"{CAPABILITY_NAME}/{self.environment}/").rstrip('/')
        secret_path = f"{secrets_prefix}/{secret_name}"
        secret = self._secrets.get(secret_path)
        if secret and key and isinstance(secret, dict):
            return secret.get(key)
        return secret
    
    def _build_resource_name(self, resource: str) -> str:
        """
        Build a resource name following the capability-env-name pattern.
        
        Args:
            resource: The resource name suffix (e.g., 'transformation-system')
            
        Returns:
            Full resource name (e.g., 'ontology-local-foundry-workspace')
        """
        from src.config.resource_naming import dynamodb_table_name
        return dynamodb_table_name(resource, capability=CAPABILITY_NAME, environment=self.environment)
    
    # =========================================================================
    # AWS Core Configuration
    # =========================================================================
    
    @property
    def aws_region(self) -> str:
        """Get AWS region."""
        return (
            self._get_ssm_param('aws/region') or
            os.getenv('AWS_REGION') or
            os.getenv('AWS_DEFAULT_REGION') or
            'us-east-1'
        )

    @property
    def aws_access_mode(self) -> str:
        """Active AWS access mode injected by the kube-operator.

        One of: ``higher-cost`` (default, full PrivateLink), ``moderate``
        (S3/DDB gateway + NAT per AZ), ``lowest-cost`` (S3/DDB gateway +
        single NAT), ``public-nodes`` (nodes with public IPs).

        Drives whether boto3 picks explicit endpoint URLs or default public
        regional hostnames; see :mod:`src.utils.aws_access_config`.
        """
        raw = (os.getenv('AWS_ACCESS_MODE') or '').strip().lower()
        if raw in {'higher-cost', 'moderate', 'lowest-cost', 'public-nodes', 'localstack'}:
            return raw
        return 'higher-cost'

    # =========================================================================
    # DynamoDB Table Names
    # =========================================================================
    
    @property
    def dynamodb_transformation_table(self) -> str:
        """Get DynamoDB transformation system table name."""
        return (
            self._get_ssm_param('dynamodb/transformation-table') or
            os.getenv('DYNAMODB_TABLE') or
            os.getenv('DYNAMODB_TRANSFORMATION_TABLE') or
            self._build_resource_name('transformation-system')
        )
    
    @property
    def dynamodb_license_table(self) -> str:
        """Get DynamoDB license table name."""
        return (
            self._get_ssm_param('dynamodb/license-table') or
            os.getenv('LICENSE_TABLE') or
            os.getenv('DYNAMODB_LICENSE_TABLE') or
            self._build_resource_name('license')
        )
    
    @property
    def dynamodb_foundry_workspace_table(self) -> str:
        """Get DynamoDB foundry workspace table name (Solutions, Views, Dashboards)."""
        return (
            self._get_ssm_param('dynamodb/foundry-workspace-table') or
            os.getenv('FOUNDRY_WORKSPACE_TABLE') or
            os.getenv('DYNAMODB_FOUNDRY_WORKSPACE_TABLE') or
            self._build_resource_name('foundry-workspace')
        )

    @property
    def dynamodb_diagnostics_table(self) -> str:
        """DynamoDB diagnostics history table (AI-OPs, Phase 1).

        Persists diagnostic run records (scope + run_id keyed). Written by
        ``DiagnosticsHistoryService`` and consumed by
        ``GET /api/v1/diagnostics/history``.
        """
        return (
            self._get_ssm_param('dynamodb/diagnostics-table') or
            os.getenv('DIAGNOSTICS_TABLE') or
            os.getenv('DYNAMODB_DIAGNOSTICS_TABLE') or
            self._build_resource_name('diagnostics')
        )

    @property
    def dynamodb_health_table(self) -> str:
        """DynamoDB AI Health Central snapshots table (AI-OPs, Phase 1).

        Persists periodic health snapshots (scope + iso_ts keyed). Written by
        ``AIHealthService`` and consumed by ``GET /api/v1/ai-health/*``.
        """
        return (
            self._get_ssm_param('dynamodb/health-table') or
            os.getenv('HEALTH_TABLE') or
            os.getenv('DYNAMODB_HEALTH_TABLE') or
            self._build_resource_name('health')
        )
    
    # =========================================================================
    # S3 Bucket Names
    # =========================================================================
    
    @property
    def s3_recordings_bucket(self) -> str:
        """Get S3 bucket for call data and recordings."""
        return (
            self._get_ssm_param('s3/recordings-bucket') or
            os.getenv('S3_RECORDINGS_BUCKET') or
            self._build_resource_name('call-data')
        )
    
    @property
    def s3_dashboards_bucket(self) -> str:
        """Get S3 bucket for dashboard persistence."""
        return (
            self._get_ssm_param('s3/dashboards-bucket') or
            os.getenv('DASHBOARD_S3_BUCKET') or
            ''
        )

    @property
    def s3_journey_logs_bucket(self) -> str:
        """Get S3 bucket for journey logs."""
        return (
            self._get_ssm_param('s3/journey-logs-bucket') or
            os.getenv('S3_JOURNEY_LOGS_BUCKET') or
            self._build_resource_name('journey-logs')
        )
    
    @property
    def s3_journey_reports_bucket(self) -> str:
        """Get S3 bucket for journey reports."""
        return (
            self._get_ssm_param('s3/journey-reports-bucket') or
            os.getenv('S3_JOURNEY_REPORTS_BUCKET') or
            self._build_resource_name('journey-reports')
        )
    
    # =========================================================================
    # Glue Configuration
    # =========================================================================
    
    @property
    def glue_database_name(self) -> str:
        """Get Glue database name."""
        from src.config.resource_naming import glue_database_name as _glue_db
        return (
            self._get_ssm_param('glue/database') or
            os.getenv('GLUE_DATABASE_NAME') or
            os.getenv('GLUE_DATABASE') or
            _glue_db(capability=CAPABILITY_NAME, environment=self.environment)
        )
    
    # =========================================================================
    # Server Configuration
    # =========================================================================
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return (
            self._get_ssm_param('server/log-level') or
            os.getenv('LOG_LEVEL') or
            'INFO'
        )
    
    @property
    def gateway_port(self) -> int:
        """Get gateway port."""
        port_str = (
            self._get_ssm_param('server/gateway-port') or
            os.getenv('GATEWAY_PORT') or
            '8000'
        )
        return int(port_str)
    
    @property
    def api_key(self) -> str:
        """Get API key for gateway authentication."""
        return (
            self._get_secret('api-keys', 'API_KEY') or
            os.getenv('API_KEY') or
            'super-secret'
        )
    
    
    # =========================================================================
    # Remote nexus-simulator (in-cluster HTTP)
    # =========================================================================

    @property
    def simulator_enabled(self) -> bool:
        return os.getenv("SIMULATOR_ENABLED", "true").lower() != "false"

    @property
    def simulator_base_url(self) -> str:
        return (os.getenv("SIMULATOR_BASE_URL") or "").rstrip("/")

    @property
    def simulator_ui_url(self) -> str:
        return (os.getenv("SIMULATOR_UI_URL") or "http://localhost:8082").rstrip("/")

    # =========================================================================
    # Cognito Configuration (OAuth 2.0 / OIDC)
    # =========================================================================
    
    @property
    def cognito_region(self) -> str:
        """Get Cognito region."""
        return (
            self._get_ssm_param('cognito/region') or
            os.getenv('COGNITO_REGION') or
            self.aws_region
        )
    
    @property
    def cognito_user_pool_id(self) -> str:
        """Get Cognito User Pool ID."""
        return (
            self._get_ssm_param('cognito/user-pool-id') or
            os.getenv('COGNITO_USER_POOL_ID') or
            ''
        )
    
    @property
    def cognito_app_client_id(self) -> str:
        """Get Cognito App Client ID."""
        return (
            self._get_ssm_param('cognito/client-id') or
            self._get_ssm_param('cognito/app-client-id') or  # Legacy key
            os.getenv('COGNITO_APP_CLIENT_ID') or
            os.getenv('COGNITO_CLIENT_ID') or
            ''
        )
    
    @property
    def cognito_domain(self) -> str:
        """Get Cognito domain for OAuth."""
        return (
            self._get_ssm_param('cognito/domain') or
            os.getenv('COGNITO_DOMAIN') or
            ''
        )
    
    @property
    def cognito_redirect_uri(self) -> str:
        """Get OAuth redirect URI (callback URL)."""
        return (
            self._get_ssm_param('cognito/redirect-uri') or
            os.getenv('COGNITO_REDIRECT_URI') or
            ''
        )
    
    def get_cognito_config(self) -> Dict[str, str]:
        """
        Get complete Cognito configuration as dictionary.
        
        Returns:
            Dict with all Cognito settings
        """
        return {
            "region": self.cognito_region,
            "user_pool_id": self.cognito_user_pool_id,
            "client_id": self.cognito_app_client_id,
            "domain": self.cognito_domain,
            "redirect_uri": self.cognito_redirect_uri
        }
    
    # =========================================================================
    # CloudWatch Configuration
    # =========================================================================
    
    @property
    def cloudwatch_log_group(self) -> str:
        """Get CloudWatch log group."""
        return (
            self._get_ssm_param('cloudwatch/log-group') or
            os.getenv('CLOUDWATCH_LOG_GROUP') or
            f'/aws/{CAPABILITY_NAME}/{self.environment}'
        )
    
    @property
    def cloudwatch_stream_prefix(self) -> str:
        """Get CloudWatch log stream prefix."""
        return (
            self._get_ssm_param('cloudwatch/stream-prefix') or
            os.getenv('CLOUDWATCH_LOG_STREAM_PREFIX') or
            'script'
        )
    
    # =========================================================================
    # OpenAI Configuration
    # =========================================================================
    
    @property
    def openai_api_key(self) -> Optional[str]:
        """
        Get OpenAI API key.
        
        Always fetches fresh from Secrets Manager (no caching) to support
        runtime key rotation without container restart.
        """
        logger.debug("🔑 ConfigProvider.openai_api_key called")
        
        # First check environment variable (set by .env.local or ECS secrets)
        env_key = os.getenv('OPENAI_API_KEY')
        if env_key:
            key_preview = f"{env_key[:10]}...{env_key[-4:]}" if len(env_key) > 14 else "***"
            logger.debug(f"✅ OpenAI key found in environment variable: {key_preview}")
            return env_key
        
        # Always fetch fresh from Secrets Manager (no caching)
        if is_aws_environment() and self.environment != 'local':
            try:
                from .secrets_loader import SecretsLoader
                # Use cache_ttl=0 to always fetch fresh from Secrets Manager
                secrets_loader = SecretsLoader(region=self.aws_region, cache_ttl=0)
                
                secrets_prefix = os.getenv('SECRETS_PREFIX', f"{CAPABILITY_NAME}/{self.environment}/").rstrip('/')
                secret_patterns = [
                    f"{secrets_prefix}/openai",
                    f"{CAPABILITY_NAME}/{self.environment}/openai",
                ]
                
                for secret_name in secret_patterns:
                    logger.debug(f"   Trying secret: {secret_name}")
                    
                    # Try as JSON with common keys
                    for key in ['OPENAI_API_KEY', 'api_key', 'apiKey']:
                        secret_value = secrets_loader.get_secret_value(secret_name, key)
                        if secret_value:
                            key_preview = f"{secret_value[:10]}...{secret_value[-4:]}" if len(secret_value) > 14 else "***"
                            logger.debug(f"✅ Loaded OpenAI API key from Secrets Manager: {secret_name}[{key}] = {key_preview}")
                            return secret_value
                    
                    # Try as raw string
                    secret = secrets_loader.get_secret(secret_name, parse_json=False)
                    if secret and not secret.startswith('{'):
                        key_preview = f"{secret[:10]}...{secret[-4:]}" if len(secret) > 14 else "***"
                        logger.debug(f"✅ Loaded OpenAI API key from Secrets Manager (raw): {secret_name} = {key_preview}")
                        return secret
                
                logger.warning(f"⚠️  OpenAI key not found in any Secrets Manager patterns: {secret_patterns}")
                        
            except Exception as e:
                logger.warning(f"❌ Failed to load OpenAI key from Secrets Manager: {e}")
                import traceback
                logger.debug(f"   Traceback: {traceback.format_exc()}")
        
        logger.warning("⚠️  OpenAI API key not found in any source (env or Secrets Manager)")
        return None


# Global configuration instance (lazy-loaded)
_global_config: Optional[ConfigProvider] = None


def get_config() -> ConfigProvider:
    """
    Get the global ConfigProvider instance.
    
    Returns:
        ConfigProvider instance (creates one if not exists)
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigProvider()
    return _global_config


def reset_config() -> None:
    """
    Reset the global configuration.
    
    Useful for testing or when environment changes.
    """
    global _global_config
    _global_config = None


def init_config(environment: Optional[str] = None) -> ConfigProvider:
    """
    Initialize or reinitialize the global configuration.
    
    Args:
        environment: Optional environment override
        
    Returns:
        ConfigProvider instance
    """
    global _global_config
    if environment:
        os.environ['ENVIRONMENT'] = environment
    _global_config = ConfigProvider()
    return _global_config

