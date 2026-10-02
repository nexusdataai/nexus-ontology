# Secrets Manager Reference

Complete reference for AWS Secrets Manager secrets used by the Nexus Telco Backend.

---

## Secrets Structure

| Secret Name | Keys | Description |
|-------------|------|-------------|
| `call-processing/{env}/api-keys` | `API_KEY` | Gateway authentication key |
| `call-processing/{env}/openai` | `OPENAI_API_KEY` | OpenAI API key for AI analysis |
| `call-processing/{env}/license` | `LICENSE_PUBLIC_KEY`, `LICENSE_PRIVATE_KEY` | License verification keys |
| `call-processing/{env}/wxcc` | `WXCC_SIM_TOKEN` | WXCC simulator token |
| `call-processing/{env}/anthropic` | `CLAUDE_API_KEY`, `ANTHROPIC_API_KEY` | Claude API keys (optional) |
| `call-processing/{env}/github` | `GITHUB_TOKEN` | GitHub token (optional) |

---

## Create Secrets (AWS CLI)

### Production Environment

```bash
# Set environment
ENV=prod

# API Keys secret (JSON format)
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/api-keys" \
  --secret-string '{"API_KEY": "your-secure-api-key"}'

# OpenAI secret
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/openai" \
  --secret-string '{"OPENAI_API_KEY": "sk-proj-xxx"}'

# License keys secret
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/license" \
  --secret-string '{"LICENSE_PUBLIC_KEY": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----", "LICENSE_PRIVATE_KEY": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"}'

# WXCC secret
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/wxcc" \
  --secret-string '{"WXCC_SIM_TOKEN": "test-token-12345"}'

# Anthropic (optional)
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/anthropic" \
  --secret-string '{"CLAUDE_API_KEY": "sk-ant-xxx", "ANTHROPIC_API_KEY": "sk-ant-xxx"}'

# GitHub (optional)
aws secretsmanager create-secret \
  --name "call-processing/${ENV}/github" \
  --secret-string '{"GITHUB_TOKEN": "ghp_xxx"}'
```

---

## Update Secrets

```bash
# Update a secret value
aws secretsmanager put-secret-value \
  --secret-id "call-processing/prod/openai" \
  --secret-string '{"OPENAI_API_KEY": "sk-proj-new-key"}'
```

---

## Query Secrets

```bash
# List secrets
aws secretsmanager list-secrets \
  --filter Key=name,Values=call-processing/prod \
  --query "SecretList[].Name"

# Get secret value
aws secretsmanager get-secret-value \
  --secret-id "call-processing/prod/openai" \
  --query "SecretString" \
  --output text

# Get secret value as JSON
aws secretsmanager get-secret-value \
  --secret-id "call-processing/prod/openai" \
  --query "SecretString" | jq -r '. | fromjson'
```

---

## Secret Loading Code

### Basic Secret Loading

```python
# src/config/secrets_loader.py

class SecretsLoader:
    """Loads secrets from AWS Secrets Manager."""
    
    def get_secret(
        self,
        secret_name: str,
        parse_json: bool = True
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """Get a secret from Secrets Manager."""
        
        response = self.client.get_secret_value(SecretId=secret_name)
        secret_value = response['SecretString']
        
        if parse_json:
            try:
                return json.loads(secret_value)
            except json.JSONDecodeError:
                pass
        
        return secret_value
    
    def get_secret_value(
        self,
        secret_name: str,
        key: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """Get a specific key from a JSON secret."""
        
        secret = self.get_secret(secret_name, parse_json=True)
        
        if isinstance(secret, dict):
            return secret.get(key, default)
        
        return default
```

### OpenAI Key Loading with Fallback

```python
# src/config/config_provider.py

@property
def openai_api_key(self) -> Optional[str]:
    """Get OpenAI API key with multi-source fallback."""
    
    # 1. Check environment variable first
    env_key = os.getenv('OPENAI_API_KEY')
    if env_key:
        return env_key
    
    # 2. Check preloaded cache
    cached_key = self._get_secret('openai', 'OPENAI_API_KEY')
    if cached_key:
        return cached_key
    
    # 3. Try dynamic load from Secrets Manager
    if is_aws_environment():
        secrets_loader = SecretsLoader(region=self.aws_region)
        
        # Try different secret name patterns
        secret_patterns = [
            f"{CAPABILITY_NAME}/{self.environment}/openai",
            f"{CAPABILITY_NAME}-{self.environment}-openai",
        ]
        
        for secret_name in secret_patterns:
            for key in ['OPENAI_API_KEY', 'api_key', 'apiKey']:
                secret_value = secrets_loader.get_secret_value(secret_name, key)
                if secret_value:
                    return secret_value
    
    return None
```

---

## Caching

Secrets are cached for 5 minutes (300 seconds):

```python
DEFAULT_CACHE_TTL = 300

def get_secret(self, secret_name: str, parse_json: bool = True):
    # Check cache first
    cache_key = f"secret:{secret_name}"
    if cache_key in self._cache:
        entry = self._cache[cache_key]
        if not entry.is_expired:
            return entry.value
    
    # Load from Secrets Manager...
    
    # Cache the result
    self._cache[cache_key] = CacheEntry(
        value=secret_value,
        expires_at=time.time() + self.cache_ttl
    )
```

To invalidate cache:

```python
from src.config.secrets_loader import SecretsLoader

loader = SecretsLoader(region='ap-southeast-1')
loader.invalidate_secret('call-processing/prod/openai')

# Or clear all cached secrets
loader.clear_cache()
```

---

## Secret Rotation

For automatic secret rotation, configure Secrets Manager rotation:

```bash
# Enable automatic rotation
aws secretsmanager rotate-secret \
  --secret-id "call-processing/prod/api-keys" \
  --rotation-lambda-arn "arn:aws:lambda:ap-southeast-1:xxx:function:rotation-function" \
  --rotation-rules AutomaticallyAfterDays=30
```

The application's 5-minute cache TTL ensures rotated secrets are picked up within 5 minutes without restart.

---

## Security Best Practices

1. **Never store secrets in SSM Parameter Store** - Use Secrets Manager for all sensitive values
2. **Use JSON format** - Store related secrets together (e.g., `api-keys` contains all API keys)
3. **Least privilege** - IAM roles should only access required secrets
4. **Enable encryption** - Secrets Manager encrypts by default with AWS-managed keys
5. **Enable rotation** - Configure automatic rotation for production secrets
6. **Audit access** - Enable CloudTrail logging for Secrets Manager API calls

---

*Related: [SSM Parameters Reference](ssm-parameters.md) | [IAM Permissions](iam-permissions.md)*
