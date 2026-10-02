# Configuration Code Flow

How configuration is loaded and accessed in the Nexus Telco Backend codebase.

---

## Initialization Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION INITIALIZATION FLOW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Module Import (src/config/config_provider.py)                           │
│     │                                                                       │
│     ├──► _load_env_local()                                                  │
│     │    │                                                                  │
│     │    ├── Check if running on ECS                                        │
│     │    │   └── If ECS: Skip (config from SSM)                             │
│     │    │                                                                  │
│     │    └── If not ECS: Load .env.local                                    │
│     │        └── Parse key=value, set os.environ                            │
│     │                                                                       │
│  2. First call to get_config()                                              │
│     │                                                                       │
│     ├──► Create ConfigProvider instance                                     │
│     │    │                                                                  │
│     │    ├──► detect_environment()                                          │
│     │    │    └── Returns: dev|stage|test|prod|local                        │
│     │    │                                                                  │
│     │    └──► _load_configuration()                                         │
│     │         │                                                             │
│     │         ├── If is_aws_environment():                                  │
│     │         │   └──► _load_from_aws()                                     │
│     │         │        ├── SSMParameterLoader.load_parameters_by_path()     │
│     │         │        └── SecretsLoader.get_secret() for each secret       │
│     │         │                                                             │
│     │         └── Else:                                                     │
│     │             └──► _load_from_environment()                             │
│     │                  └── Config via properties (env vars + defaults)      │
│     │                                                                       │
│  3. Property Access (e.g., config.s3_recordings_bucket)                     │
│     │                                                                       │
│     └──► Priority resolution:                                               │
│          1. SSM param (if loaded)                                           │
│          2. Environment variable                                            │
│          3. Default value (naming convention)                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Code Files

| File | Purpose |
|------|---------|
| `src/config/config_provider.py` | Main ConfigProvider class, get_config() |
| `src/config/ssm_loader.py` | SSMParameterLoader for AWS Parameter Store |
| `src/config/secrets_loader.py` | SecretsLoader for AWS Secrets Manager |
| `src/config/localstack_config.py` | LocalStack-specific configuration |
| `src/config/__init__.py` | Module exports |

---

## Key Functions

### get_config()

```python
# src/config/config_provider.py

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
```

### detect_environment()

```python
def detect_environment() -> str:
    """Detect the current runtime environment."""
    
    # 1. Explicit ENVIRONMENT variable
    env = os.getenv('ENVIRONMENT', '').strip().lower()
    if env and env in {'dev', 'stage', 'test', 'prod', 'local'}:
        return env
    
    # 2. Check if running on ECS
    if os.getenv('ECS_CONTAINER_METADATA_URI') or \
       os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return 'prod'
    
    # 3. LocalStack mode
    if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
        return 'local'
    
    # 4. Default to dev
    return 'dev'
```

### is_aws_environment()

```python
def is_aws_environment() -> bool:
    """Check if running in AWS environment that should use SSM/Secrets."""
    if os.getenv('ECS_CONTAINER_METADATA_URI') or \
       os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return True
    return False
```

---

## ConfigProvider Class

```python
@dataclass
class ConfigProvider:
    """Central configuration provider for the call-processing capability."""
    
    environment: str = field(default_factory=detect_environment)
    _ssm_params: Dict[str, str] = field(default_factory=dict, repr=False)
    _secrets: Dict[str, Any] = field(default_factory=dict, repr=False)
    _initialized: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        if not self._initialized:
            self._load_configuration()
            self._initialized = True
    
    def _load_configuration(self):
        if is_aws_environment() and self.environment != 'local':
            self._load_from_aws()
        else:
            self._load_from_environment()
```

---

## Property Resolution Pattern

Each configuration property follows the same resolution pattern:

```python
@property
def s3_recordings_bucket(self) -> str:
    """Get S3 bucket for call data and recordings."""
    return (
        # 1. Try SSM Parameter Store first (loaded at init on ECS)
        self._get_ssm_param('s3/recordings-bucket') or
        
        # 2. Fall back to environment variable
        os.getenv('S3_RECORDINGS_BUCKET') or
        
        # 3. Use default naming convention
        self._build_resource_name('call-data')
    )
```

---

## Usage Example

```python
from src.config.config_provider import get_config

# Get singleton config instance
config = get_config()

# Access configuration properties
bucket = config.s3_recordings_bucket      # → call-processing-dev-call-data
table = config.dynamodb_transformation_table  # → call-processing-dev-transformation-system
api_key = config.api_key                  # → (from Secrets Manager or env)
log_level = config.log_level              # → INFO

# Check environment
print(f"Environment: {config.environment}")  # → dev
print(f"Region: {config.aws_region}")        # → ap-southeast-1

# Get complete Cognito config
cognito_config = config.get_cognito_config()
# → {'region': 'ap-southeast-1', 'user_pool_id': '...', 'client_id': '...', ...}
```

---

## Reinitializing Configuration

```python
from src.config.config_provider import reset_config, init_config

# Reset global config (useful for testing)
reset_config()

# Initialize with specific environment
config = init_config(environment='test')
```

---

## .env.local Loading

The `.env.local` file is loaded automatically at module import time (before any configuration access):

```python
def _load_env_local():
    """Load environment variables from .env.local for local development."""
    
    # Skip if running on ECS
    if os.getenv('ECS_CONTAINER_METADATA_URI'):
        return
    
    # Find project root
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env.local"
    
    if env_file.exists():
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

# Called at module import time
_load_env_local()
```

---

*Related: [Configuration Sources](configuration-sources.md) | [Configuration APIs](config-apis.md)*
