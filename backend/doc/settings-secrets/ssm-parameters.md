# SSM Parameters Reference

Complete reference for all SSM Parameter Store parameters used by the Nexus Telco Backend.

---

## Complete Parameter List

| Parameter Path | Environment Variable | Default | Description |
|----------------|---------------------|---------|-------------|
| **AWS Core** |
| `/call-processing/{env}/aws/region` | `AWS_REGION` | `ap-southeast-1` | AWS region |
| `/call-processing/{env}/aws/role-arn` | `AWS_ROLE_ARN` | - | IAM role for cross-account |
| **Server** |
| `/call-processing/{env}/server/environment` | `ENVIRONMENT` | `dev` | Environment name |
| `/call-processing/{env}/server/log-level` | `LOG_LEVEL` | `INFO` | Logging level |
| `/call-processing/{env}/server/gateway-port` | `GATEWAY_PORT` | `8000` | HTTP gateway port |
| `/call-processing/{env}/server/min-workers` | `MIN_WORKERS` | `2` | Minimum worker pool |
| `/call-processing/{env}/server/max-workers` | `MAX_WORKERS` | `8` | Maximum worker pool |
| `/call-processing/{env}/server/timeout` | `MCP_REQUEST_TIMEOUT` | `60.0` | Request timeout |
| **Cognito** |
| `/call-processing/{env}/cognito/region` | `COGNITO_REGION` | `ap-southeast-1` | Cognito region |
| `/call-processing/{env}/cognito/user-pool-id` | `COGNITO_USER_POOL_ID` | - | User pool ID |
| `/call-processing/{env}/cognito/app-client-id` | `COGNITO_APP_CLIENT_ID` | - | App client ID |
| `/call-processing/{env}/cognito/domain` | `COGNITO_DOMAIN` | - | Cognito domain |
| `/call-processing/{env}/cognito/redirect-uri` | `COGNITO_REDIRECT_URI` | - | OAuth redirect |
| **WXCC Simulator** |
| `/call-processing/{env}/wxcc/enabled` | `WXCC_SIMULATOR_ENABLED` | `true` | Enable simulator |
| `/call-processing/{env}/wxcc/bucket` | `WXCC_SIMULATOR_BUCKET` | `call-processing-{env}-wxcc-simulator` | Simulator S3 bucket |
| `/call-processing/{env}/wxcc/prefix` | `WXCC_SIMULATOR_PREFIX` | `wxcc-simulator` | S3 prefix |
| `/call-processing/{env}/wxcc/org-id` | `WXCC_SIM_ORG_ID` | `sim-org-001` | Simulated org ID |
| **S3 Buckets** |
| `/call-processing/{env}/s3/recordings-bucket` | `S3_RECORDINGS_BUCKET` | `call-processing-{env}-call-data` | Call data bucket |
| `/call-processing/{env}/s3/journey-logs-bucket` | `S3_JOURNEY_LOGS_BUCKET` | `call-processing-{env}-journey-logs` | Logs bucket |
| `/call-processing/{env}/s3/journey-reports-bucket` | `S3_JOURNEY_REPORTS_BUCKET` | `call-processing-{env}-journey-reports` | Reports bucket |
| **DynamoDB** |
| `/call-processing/{env}/dynamodb/transformation-table` | `DYNAMODB_TABLE` | `call-processing-{env}-transformation-system` | Main table |
| `/call-processing/{env}/dynamodb/license-table` | `LICENSE_TABLE` | `call-processing-{env}-license` | License table |
| `/call-processing/{env}/dynamodb/wxcc-task-table` | `WXCC_TASK_TABLE` | `call-processing-{env}-wxcc-task-tracking` | Task tracking |
| **Glue** |
| `/call-processing/{env}/glue/database` | `GLUE_DATABASE_NAME` | `call-processing-{env}-analytics` | Glue database |
| `/call-processing/{env}/glue/table` | `GLUE_TABLE_NAME` | `wxcc_calls` | Glue table |
| **CloudWatch** |
| `/call-processing/{env}/cloudwatch/log-group` | `CLOUDWATCH_LOG_GROUP` | `/aws/call-processing/{env}` | Log group |
| `/call-processing/{env}/cloudwatch/stream-prefix` | `CLOUDWATCH_LOG_STREAM_PREFIX` | `script` | Stream prefix |

---

## Create SSM Parameters (AWS CLI)

### Production Environment

```bash
# Set environment
ENV=prod

# AWS Core
aws ssm put-parameter --name "/call-processing/${ENV}/aws/region" \
  --value "ap-southeast-1" --type String --overwrite

# Server Configuration
aws ssm put-parameter --name "/call-processing/${ENV}/server/environment" \
  --value "production" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/server/log-level" \
  --value "INFO" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/server/gateway-port" \
  --value "8000" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/server/min-workers" \
  --value "2" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/server/max-workers" \
  --value "8" --type String --overwrite

# Cognito
aws ssm put-parameter --name "/call-processing/${ENV}/cognito/region" \
  --value "ap-southeast-1" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/cognito/user-pool-id" \
  --value "<user-pool-id>" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/cognito/app-client-id" \
  --value "<app-client-id>" --type String --overwrite

# S3 Buckets
aws ssm put-parameter --name "/call-processing/${ENV}/s3/recordings-bucket" \
  --value "call-processing-${ENV}-call-data" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/s3/journey-logs-bucket" \
  --value "call-processing-${ENV}-journey-logs" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/s3/journey-reports-bucket" \
  --value "call-processing-${ENV}-journey-reports" --type String --overwrite

# DynamoDB Tables
aws ssm put-parameter --name "/call-processing/${ENV}/dynamodb/transformation-table" \
  --value "call-processing-${ENV}-transformation-system" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/dynamodb/license-table" \
  --value "call-processing-${ENV}-license" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/dynamodb/wxcc-task-table" \
  --value "call-processing-${ENV}-wxcc-task-tracking" --type String --overwrite

# Glue
aws ssm put-parameter --name "/call-processing/${ENV}/glue/database" \
  --value "call-processing-${ENV}-analytics" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/glue/table" \
  --value "wxcc_calls" --type String --overwrite

# CloudWatch
aws ssm put-parameter --name "/call-processing/${ENV}/cloudwatch/log-group" \
  --value "/aws/call-processing/${ENV}" --type String --overwrite

# WXCC Simulator
aws ssm put-parameter --name "/call-processing/${ENV}/wxcc/enabled" \
  --value "false" --type String --overwrite
aws ssm put-parameter --name "/call-processing/${ENV}/wxcc/bucket" \
  --value "call-processing-${ENV}-wxcc-simulator" --type String --overwrite
```

---

## Query SSM Parameters

### List All Parameters for an Environment

```bash
aws ssm get-parameters-by-path \
  --path "/call-processing/prod/" \
  --recursive \
  --query "Parameters[].{Name:Name,Value:Value}" \
  --output table
```

### Get Specific Parameter

```bash
aws ssm get-parameter \
  --name "/call-processing/prod/server/log-level" \
  --query "Parameter.Value" \
  --output text
```

### Update Parameter

```bash
aws ssm put-parameter \
  --name "/call-processing/prod/server/log-level" \
  --value "DEBUG" \
  --type String \
  --overwrite
```

---

## SSM Loading Code

```python
# src/config/ssm_loader.py

class SSMParameterLoader:
    """Loads parameters from AWS Systems Manager Parameter Store."""
    
    def load_parameters_by_path(
        self,
        path: str,
        recursive: bool = True,
        decrypt: bool = True
    ) -> Dict[str, str]:
        """
        Load all parameters under a path prefix.
        
        Args:
            path: Path prefix (e.g., /call-processing/prod/)
            recursive: Whether to load recursively
            decrypt: Whether to decrypt SecureString parameters
            
        Returns:
            Dictionary mapping relative parameter names to values
        """
        parameters: Dict[str, str] = {}
        
        paginator = self.client.get_paginator('get_parameters_by_path')
        
        for page in paginator.paginate(
            Path=path,
            Recursive=recursive,
            WithDecryption=decrypt
        ):
            for param in page.get('Parameters', []):
                # Extract relative name (remove path prefix)
                full_name = param['Name']
                relative_name = full_name[len(path):].lstrip('/')
                parameters[relative_name] = param['Value']
        
        return parameters
```

---

## Caching

SSM parameters are cached for 5 minutes (300 seconds) to reduce API calls:

```python
DEFAULT_CACHE_TTL = 300  # 5 minutes

@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
```

To invalidate cache programmatically:

```python
from src.config.ssm_loader import SSMParameterLoader

loader = SSMParameterLoader(region='ap-southeast-1')
loader.invalidate_path('/call-processing/prod/')
```

---

*Related: [Secrets Manager Reference](secrets-manager.md) | [Configuration Sources](configuration-sources.md)*
