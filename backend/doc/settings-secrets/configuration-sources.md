# Configuration Sources

The Nexus Telco Backend uses a multi-tier configuration system with automatic environment detection and source prioritization.

---

## Source Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION SOURCE HIERARCHY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Priority 1: SSM Parameter Store (ECS only)                                 │
│  ─────────────────────────────────────────────                              │
│  • Loaded when running on ECS (detected via ECS_CONTAINER_METADATA_URI)     │
│  • Path-based loading: /call-processing/{env}/*                             │
│  • Cached with 5-minute TTL                                                 │
│  • Best for: Non-sensitive configuration that may change                    │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│                                                                             │
│  Priority 2: Secrets Manager (ECS only)                                     │
│  ─────────────────────────────────────                                      │
│  • Loaded when running on ECS                                               │
│  • Supports JSON secrets with multiple keys                                 │
│  • Cached with 5-minute TTL                                                 │
│  • Best for: API keys, credentials, certificates                            │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│                                                                             │
│  Priority 3: Environment Variables                                          │
│  ───────────────────────────────────                                        │
│  • From .env.local (local development)                                      │
│  • From ECS task definition (containerized)                                 │
│  • Always available as fallback                                             │
│  • Best for: Local development, CI/CD overrides                             │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│                                                                             │
│  Priority 4: Default Values (Hardcoded)                                     │
│  ─────────────────────────────────────                                      │
│  • Fallback when no other source provides value                             │
│  • Uses naming convention to build resource names                           │
│  • Example: call-processing-{env}-transformation-system                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Loading Code Pattern

```python
# Example: How a configuration property is resolved
@property
def s3_recordings_bucket(self) -> str:
    """Get S3 bucket for call data and recordings."""
    return (
        # 1. Try SSM Parameter Store first
        self._get_ssm_param('s3/recordings-bucket') or
        # 2. Fall back to environment variable
        os.getenv('S3_RECORDINGS_BUCKET') or
        # 3. Use default naming convention
        self._build_resource_name('call-data')  # → call-processing-{env}-call-data
    )
```

---

## Environment Detection

### Detection Logic

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ENVIRONMENT DETECTION FLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Application Start                                                          │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────┐                                    │
│  │ Check ENVIRONMENT env var           │                                    │
│  │ (set in ECS task definition)        │                                    │
│  └───────────────┬─────────────────────┘                                    │
│                  │                                                          │
│          ┌──────┴──────┐                                                    │
│          │             │                                                    │
│          ▼ Set         ▼ Not Set                                            │
│  ┌───────────────┐    ┌───────────────────────────────┐                     │
│  │ Use value:    │    │ Check ECS_CONTAINER_METADATA_ │                     │
│  │ dev/stage/    │    │ URI env var                   │                     │
│  │ test/prod/    │    └────────────────┬──────────────┘                     │
│  │ local         │                     │                                    │
│  └───────────────┘             ┌───────┴───────┐                            │
│                                │               │                            │
│                                ▼ Present       ▼ Not Present                │
│                        ┌───────────────┐    ┌───────────────────┐           │
│                        │ Running on    │    │ Check USE_LOCAL-  │           │
│                        │ ECS → 'prod'  │    │ STACK env var     │           │
│                        └───────────────┘    └─────────┬─────────┘           │
│                                                       │                     │
│                                               ┌───────┴───────┐             │
│                                               │               │             │
│                                               ▼ = 'true'      ▼ Other       │
│                                       ┌───────────────┐  ┌───────────┐      │
│                                       │ LocalStack    │  │ Default   │      │
│                                       │ → 'local'     │  │ → 'dev'   │      │
│                                       └───────────────┘  └───────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Code Implementation

```python
# src/config/config_provider.py

VALID_ENVIRONMENTS = {"dev", "stage", "test", "prod", "local"}

def detect_environment() -> str:
    """Detect the current runtime environment."""
    
    # 1. Explicit ENVIRONMENT variable (highest priority)
    env = os.getenv('ENVIRONMENT', '').strip().lower()
    if env and env in VALID_ENVIRONMENTS:
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


def is_aws_environment() -> bool:
    """Check if running in AWS environment that should use SSM/Secrets."""
    # Only True when running on ECS
    if os.getenv('ECS_CONTAINER_METADATA_URI') or \
       os.getenv('ECS_CONTAINER_METADATA_URI_V4'):
        return True
    return False
```

---

## Environment Detection Results

| Scenario | `ENVIRONMENT` | `ECS_CONTAINER_METADATA_URI` | `USE_LOCALSTACK` | Result | Config Source |
|----------|---------------|------------------------------|------------------|--------|---------------|
| ECS Production | `prod` | Present | - | `prod` | SSM + Secrets Manager |
| ECS Staging | `stage` | Present | - | `stage` | SSM + Secrets Manager |
| Local with LocalStack | `local` | - | `true` | `local` | `.env.local` |
| Local with AWS | `dev` | - | `false` | `dev` | `.env.local` |
| Default | Not set | - | - | `dev` | `.env.local` |

---

## Key Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `detect_environment()` | Determine current environment | `dev`, `stage`, `test`, `prod`, or `local` |
| `is_aws_environment()` | Check if config should load from SSM/Secrets | `True` only on ECS |
| `get_config()` | Get singleton ConfigProvider instance | `ConfigProvider` |

---

*Related: [Code Flow](code-flow.md) | [Deployment Scenarios](deployment-scenarios/)*
