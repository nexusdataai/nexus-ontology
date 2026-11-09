"""
Secrets Manager Loader

Loads sensitive configuration from AWS Secrets Manager.
Supports JSON secret parsing and caching.
"""

import os
import json
import logging
import time
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default cache TTL in seconds (5 minutes)
DEFAULT_CACHE_TTL = 300


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    value: Any
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at


class SecretsLoader:
    """
    Loads secrets from AWS Secrets Manager.
    
    Features:
    - Automatic JSON parsing
    - Caching with configurable TTL
    - Graceful error handling
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL
    ):
        """
        Initialize the Secrets Loader.
        
        Args:
            region: AWS region (defaults to AWS_REGION env var)
            cache_ttl: Cache TTL in seconds
        """
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._client = None
    
    @property
    def client(self):
        """Get or create Secrets Manager client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """Create Secrets Manager client with appropriate configuration."""
        try:
            import boto3
            from src.utils.aws_access_config import merge_kwargs

            if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
                from src.config.localstack_config import get_localstack_config

                cfg = get_localstack_config()
                endpoint_url = (
                    cfg.get_service_endpoint('secretsmanager')
                    or os.getenv('AWS_ENDPOINT_URL_SECRETSMANAGER')
                    or cfg.endpoint_url
                )
                kwargs = merge_kwargs(
                    'secretsmanager',
                    self.region,
                    {
                        'aws_access_key_id': cfg.access_key,
                        'aws_secret_access_key': cfg.secret_key,
                        'endpoint_url': endpoint_url,
                    },
                )
                return boto3.client('secretsmanager', **kwargs)

            kwargs = merge_kwargs('secretsmanager', self.region, {})
            return boto3.client('secretsmanager', **kwargs)

        except ImportError:
            logger.error("boto3 not available")
            raise
    
    def get_secret(
        self,
        secret_name: str,
        parse_json: bool = True
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Get a secret from Secrets Manager.
        
        Args:
            secret_name: Secret name or ARN
            parse_json: Whether to parse the secret as JSON
            
        Returns:
            Secret value (string or dict if JSON) or None if not found
        """
        # Check cache
        cache_key = f"secret:{secret_name}"
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired:
                return entry.value
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Get secret string or binary
            if 'SecretString' in response:
                secret_value = response['SecretString']
            else:
                # Binary secret
                import base64
                secret_value = base64.b64decode(response['SecretBinary']).decode('utf-8')
            
            # Try to parse as JSON if requested
            if parse_json:
                try:
                    secret_value = json.loads(secret_value)
                except json.JSONDecodeError:
                    # Not JSON, return as string
                    pass
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                value=secret_value,
                expires_at=time.time() + self.cache_ttl
            )
            
            logger.debug(f"Loaded secret: {secret_name}")
            return secret_value
            
        except self.client.exceptions.ResourceNotFoundException:
            logger.debug(f"Secret not found: {secret_name}")
            return None
        except self.client.exceptions.AccessDeniedException:
            logger.warning(f"Access denied to secret: {secret_name}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get secret {secret_name}: {e}")
            return None
    
    def get_secret_value(
        self,
        secret_name: str,
        key: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get a specific key from a JSON secret.
        
        Args:
            secret_name: Secret name or ARN
            key: Key within the JSON secret
            default: Default value if key not found
            
        Returns:
            Value for the key or default
        """
        secret = self.get_secret(secret_name, parse_json=True)
        
        if secret is None:
            return default
        
        if isinstance(secret, dict):
            return secret.get(key, default)
        
        # Secret is not a dict, can't get key
        return default
    
    def get_secrets_batch(
        self,
        secret_names: list,
        parse_json: bool = True
    ) -> Dict[str, Any]:
        """
        Get multiple secrets.
        
        Note: Secrets Manager doesn't have a batch API, so this
        calls get_secret for each name.
        
        Args:
            secret_names: List of secret names
            parse_json: Whether to parse secrets as JSON
            
        Returns:
            Dictionary mapping secret names to values
        """
        secrets: Dict[str, Any] = {}
        
        for name in secret_names:
            value = self.get_secret(name, parse_json=parse_json)
            if value is not None:
                secrets[name] = value
        
        return secrets
    
    def clear_cache(self):
        """Clear the secrets cache."""
        self._cache.clear()
        logger.debug("Secrets cache cleared")
    
    def invalidate_secret(self, secret_name: str):
        """
        Invalidate a cached secret.
        
        Args:
            secret_name: Secret name to invalidate
        """
        cache_key = f"secret:{secret_name}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Invalidated cached secret: {secret_name}")
    
    def put_secret(
        self,
        secret_name: str,
        secret_string: str,
        description: str = ""
    ) -> bool:
        """
        Create or update a secret in Secrets Manager.
        
        Args:
            secret_name: Secret name
            secret_string: Secret value (typically JSON string)
            description: Optional description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to update existing secret
            try:
                self.client.put_secret_value(
                    SecretId=secret_name,
                    SecretString=secret_string
                )
                logger.info(f"Secret updated: {secret_name}")
            except self.client.exceptions.ResourceNotFoundException:
                # Create new secret if it doesn't exist
                self.client.create_secret(
                    Name=secret_name,
                    SecretString=secret_string,
                    Description=description or f"Managed secret: {secret_name}"
                )
                logger.info(f"Secret created: {secret_name}")
            
            # Invalidate cache
            self.invalidate_secret(secret_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to put secret {secret_name}: {e}")
            return False
    
    def list_secrets(self, prefix: Optional[str] = None) -> list:
        """
        List secrets, optionally filtered by prefix.
        
        Args:
            prefix: Optional prefix to filter secrets
            
        Returns:
            List of secret metadata dictionaries
        """
        secrets = []
        
        try:
            paginator = self.client.get_paginator('list_secrets')
            
            filters = []
            if prefix:
                filters.append({
                    'Key': 'name',
                    'Values': [prefix]
                })
            
            paginate_kwargs = {}
            if filters:
                paginate_kwargs['Filters'] = filters
            
            for page in paginator.paginate(**paginate_kwargs):
                for secret in page.get('SecretList', []):
                    # Filter by prefix manually if needed (AWS filter is partial match)
                    if prefix and not secret['Name'].startswith(prefix):
                        continue
                    
                    secrets.append({
                        "name": secret['Name'],
                        "description": secret.get('Description', ''),
                        "last_modified": secret.get('LastChangedDate').isoformat() if secret.get('LastChangedDate') else None,
                        "created": secret.get('CreatedDate').isoformat() if secret.get('CreatedDate') else None,
                        "arn": secret.get('ARN')
                    })
            
            return secrets
            
        except Exception as e:
            logger.warning(f"Failed to list secrets: {e}")
            return []
    
    def describe_secret(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a secret without the value.
        
        Args:
            secret_name: Secret name or ARN
            
        Returns:
            Secret metadata or None if not found
        """
        try:
            response = self.client.describe_secret(SecretId=secret_name)
            
            return {
                "name": response.get('Name'),
                "description": response.get('Description', ''),
                "arn": response.get('ARN'),
                "last_modified": response.get('LastChangedDate').isoformat() if response.get('LastChangedDate') else None,
                "created": response.get('CreatedDate').isoformat() if response.get('CreatedDate') else None,
                "rotation_enabled": response.get('RotationEnabled', False),
                "tags": response.get('Tags', [])
            }
            
        except self.client.exceptions.ResourceNotFoundException:
            return None
        except Exception as e:
            logger.warning(f"Failed to describe secret {secret_name}: {e}")
            return None
    
    def delete_secret(
        self,
        secret_name: str,
        force: bool = False,
        recovery_days: int = 30
    ) -> bool:
        """
        Delete a secret from Secrets Manager.
        
        Args:
            secret_name: Secret name
            force: If True, delete immediately without recovery window
            recovery_days: Days to retain secret for recovery (7-30)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if force:
                self.client.delete_secret(
                    SecretId=secret_name,
                    ForceDeleteWithoutRecovery=True
                )
            else:
                self.client.delete_secret(
                    SecretId=secret_name,
                    RecoveryWindowInDays=recovery_days
                )
            
            # Invalidate cache
            self.invalidate_secret(secret_name)
            
            logger.info(f"Secret deleted: {secret_name}")
            return True
            
        except self.client.exceptions.ResourceNotFoundException:
            logger.debug(f"Secret not found for deletion: {secret_name}")
            return True  # Consider success if already doesn't exist
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_name}: {e}")
            return False

