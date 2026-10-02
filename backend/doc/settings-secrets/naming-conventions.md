# Naming Conventions

All resources in the Nexus Telco Backend follow consistent naming patterns for easy identification and management across environments.

---

## Resource Naming Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NAMING CONVENTION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Pattern: call-processing-{env}-{resource-name}                             │
│                                                                             │
│  Components:                                                                │
│  ┌──────────────────┬─────────────────────────────────────────────────┐    │
│  │ Component        │ Values                                          │    │
│  ├──────────────────┼─────────────────────────────────────────────────┤    │
│  │ Capability       │ call-processing (fixed)                         │    │
│  │ Environment      │ dev, stage, test, prod, local                   │    │
│  │ Resource Name    │ transformation-system, call-data, license, etc. │    │
│  └──────────────────┴─────────────────────────────────────────────────┘    │
│                                                                             │
│  Examples:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Resource Type    │ Pattern                     │ Example (prod)     │   │
│  ├──────────────────┼─────────────────────────────┼────────────────────┤   │
│  │ DynamoDB Table   │ call-processing-{env}-*     │ call-processing-   │   │
│  │                  │                             │ prod-transformation│   │
│  │                  │                             │ -system            │   │
│  ├──────────────────┼─────────────────────────────┼────────────────────┤   │
│  │ S3 Bucket        │ call-processing-{env}-*     │ call-processing-   │   │
│  │                  │                             │ prod-call-data     │   │
│  ├──────────────────┼─────────────────────────────┼────────────────────┤   │
│  │ SSM Parameter    │ /call-processing/{env}/*    │ /call-processing/  │   │
│  │                  │                             │ prod/server/log-   │   │
│  │                  │                             │ level              │   │
│  ├──────────────────┼─────────────────────────────┼────────────────────┤   │
│  │ Secret           │ call-processing/{env}/*     │ call-processing/   │   │
│  │                  │                             │ prod/api-keys      │   │
│  ├──────────────────┼─────────────────────────────┼────────────────────┤   │
│  │ CloudWatch Log   │ /aws/call-processing/{env}  │ /aws/call-         │   │
│  │                  │                             │ processing/prod    │   │
│  └──────────────────┴─────────────────────────────┴────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## SSM Parameter Path Structure

```
/call-processing/{env}/
├── aws/
│   ├── region              → ap-southeast-1
│   └── role-arn            → arn:aws:iam::...
├── server/
│   ├── environment         → production
│   ├── log-level           → INFO
│   ├── gateway-port        → 8000
│   ├── min-workers         → 2
│   ├── max-workers         → 8
│   └── timeout             → 60.0
├── cognito/
│   ├── region              → ap-southeast-1
│   ├── user-pool-id        → ap-southeast-1_xxx
│   ├── app-client-id       → xxx
│   ├── domain              → xxx.auth.ap-southeast-1.amazoncognito.com
│   └── redirect-uri        → https://app.example.com/callback
├── wxcc/
│   ├── enabled             → true/false
│   ├── bucket              → call-processing-{env}-wxcc-simulator
│   ├── prefix              → wxcc-simulator
│   └── org-id              → sim-org-001
├── s3/
│   ├── recordings-bucket   → call-processing-{env}-call-data
│   ├── journey-logs-bucket → call-processing-{env}-journey-logs
│   └── journey-reports-bucket → call-processing-{env}-journey-reports
├── dynamodb/
│   ├── transformation-table → call-processing-{env}-transformation-system
│   ├── license-table       → call-processing-{env}-license
│   └── wxcc-task-table     → call-processing-{env}-wxcc-task-tracking
├── glue/
│   ├── database            → call-processing-{env}-analytics
│   └── table               → wxcc_calls
└── cloudwatch/
    ├── log-group           → /aws/call-processing/{env}
    └── stream-prefix       → script
```

---

## Examples by Environment

| Resource Type | Pattern | Example (dev) | Example (prod) |
|---------------|---------|---------------|----------------|
| SSM Parameter | `/call-processing/{env}/server/log-level` | `/call-processing/dev/server/log-level` | `/call-processing/prod/server/log-level` |
| Secret | `call-processing/{env}/api-keys` | `call-processing/dev/api-keys` | `call-processing/prod/api-keys` |
| DynamoDB Table | `call-processing-{env}-{name}` | `call-processing-dev-transformation-system` | `call-processing-prod-transformation-system` |
| S3 Bucket | `call-processing-{env}-{name}` | `call-processing-dev-call-data` | `call-processing-prod-call-data` |
| CloudWatch Log Group | `/aws/call-processing/{env}` | `/aws/call-processing/dev` | `/aws/call-processing/prod` |

---

## Code Implementation

The naming convention is implemented in `ConfigProvider`:

```python
# src/config/config_provider.py

CAPABILITY_NAME = "call-processing"

def _build_resource_name(self, resource: str) -> str:
    """
    Build a resource name following the capability-env-name pattern.
    
    Args:
        resource: The resource name suffix (e.g., 'transformation-system')
        
    Returns:
        Full resource name (e.g., 'call-processing-prod-transformation-system')
    """
    return f"{CAPABILITY_NAME}-{self.environment}-{resource}"
```

---

*Related: [SSM Parameters Reference](ssm-parameters.md) | [Secrets Manager Reference](secrets-manager.md)*
