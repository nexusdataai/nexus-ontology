"""
SSM Parameter Store Loader

Loads configuration parameters from AWS Systems Manager Parameter Store.
Supports batch loading with caching and error handling.
"""

import os
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

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


class SSMParameterLoader:
    """
    Loads parameters from AWS Systems Manager Parameter Store.
    
    Features:
    - Batch loading with get_parameters_by_path
    - Caching with configurable TTL
    - Graceful error handling
    """
    
    def __init__(
        self,
        region: Optional[str] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL
    ):
        """
        Initialize the SSM Parameter Loader.
        
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
        """Get or create SSM client."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """Create SSM client with appropriate configuration."""
        try:
            import boto3
            
            # Check for LocalStack
            if os.getenv('USE_LOCALSTACK', '').lower() == 'true':
                endpoint_url = os.getenv('AWS_ENDPOINT_URL', 'http://localhost:4566')
                return boto3.client(
                    'ssm',
                    region_name=self.region,
                    endpoint_url=endpoint_url,
                    aws_access_key_id='test',
                    aws_secret_access_key='test'
                )
            
            return boto3.client('ssm', region_name=self.region)
            
        except ImportError:
            logger.error("boto3 not available")
            raise
    
    def get_parameter(self, name: str, decrypt: bool = True) -> Optional[str]:
        """
        Get a single parameter from SSM.
        
        Args:
            name: Full parameter name (e.g., /call-processing/prod/aws/region)
            decrypt: Whether to decrypt SecureString parameters
            
        Returns:
            Parameter value or None if not found
        """
        # Check cache
        cache_key = f"param:{name}"
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired:
                return entry.value
        
        try:
            response = self.client.get_parameter(
                Name=name,
                WithDecryption=decrypt
            )
            value = response['Parameter']['Value']
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                value=value,
                expires_at=time.time() + self.cache_ttl
            )
            
            return value
            
        except self.client.exceptions.ParameterNotFound:
            logger.debug(f"SSM parameter not found: {name}")
            return None
        except Exception as e:
            logger.warning(f"Failed to get SSM parameter {name}: {e}")
            return None
    
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
        # Check cache
        cache_key = f"path:{path}"
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            if not entry.is_expired:
                return entry.value
        
        parameters: Dict[str, str] = {}
        
        try:
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
            
            # Cache the result
            self._cache[cache_key] = CacheEntry(
                value=parameters,
                expires_at=time.time() + self.cache_ttl
            )
            
            logger.info(f"Loaded {len(parameters)} parameters from {path}")
            return parameters
            
        except Exception as e:
            logger.warning(f"Failed to load SSM parameters from {path}: {e}")
            return {}
    
    def get_parameters(
        self,
        names: list,
        decrypt: bool = True
    ) -> Dict[str, str]:
        """
        Get multiple parameters by name.
        
        Args:
            names: List of full parameter names
            decrypt: Whether to decrypt SecureString parameters
            
        Returns:
            Dictionary mapping parameter names to values
        """
        if not names:
            return {}
        
        parameters: Dict[str, str] = {}
        
        # Check cache first
        uncached_names = []
        for name in names:
            cache_key = f"param:{name}"
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if not entry.is_expired:
                    parameters[name] = entry.value
                    continue
            uncached_names.append(name)
        
        if not uncached_names:
            return parameters
        
        try:
            # SSM allows max 10 parameters per request
            batch_size = 10
            for i in range(0, len(uncached_names), batch_size):
                batch = uncached_names[i:i + batch_size]
                
                response = self.client.get_parameters(
                    Names=batch,
                    WithDecryption=decrypt
                )
                
                for param in response.get('Parameters', []):
                    name = param['Name']
                    value = param['Value']
                    parameters[name] = value
                    
                    # Cache individual parameters
                    self._cache[f"param:{name}"] = CacheEntry(
                        value=value,
                        expires_at=time.time() + self.cache_ttl
                    )
            
            return parameters
            
        except Exception as e:
            logger.warning(f"Failed to get SSM parameters: {e}")
            return parameters
    
    def clear_cache(self):
        """Clear the parameter cache."""
        self._cache.clear()
        logger.debug("SSM parameter cache cleared")
    
    def invalidate_path(self, path: str):
        """
        Invalidate all cached entries for a path.
        
        Args:
            path: Path prefix to invalidate
        """
        keys_to_remove = [
            key for key in self._cache
            if key.startswith(f"path:{path}") or 
               (key.startswith("param:") and path in key)
        ]
        for key in keys_to_remove:
            del self._cache[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {path}")
    
    def put_parameter(
        self,
        name: str,
        value: str,
        description: str = "",
        overwrite: bool = True,
        param_type: str = "String"
    ) -> bool:
        """
        Create or update a parameter in SSM.
        
        Args:
            name: Full parameter name (e.g., /call-processing/prod/server/log-level)
            value: Parameter value
            description: Parameter description
            overwrite: Whether to overwrite existing parameter
            param_type: Parameter type (String, StringList, SecureString)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.put_parameter(
                Name=name,
                Value=value,
                Type=param_type,
                Overwrite=overwrite,
                Description=description
            )
            
            # Update cache
            cache_key = f"param:{name}"
            self._cache[cache_key] = CacheEntry(
                value=value,
                expires_at=time.time() + self.cache_ttl
            )
            
            logger.info(f"SSM parameter set: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set SSM parameter {name}: {e}")
            return False
    
    def delete_parameter(self, name: str) -> bool:
        """
        Delete a parameter from SSM.
        
        Args:
            name: Full parameter name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_parameter(Name=name)
            
            # Remove from cache
            cache_key = f"param:{name}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            
            logger.info(f"SSM parameter deleted: {name}")
            return True
            
        except self.client.exceptions.ParameterNotFound:
            logger.debug(f"SSM parameter not found for deletion: {name}")
            return True  # Consider success if already doesn't exist
        except Exception as e:
            logger.error(f"Failed to delete SSM parameter {name}: {e}")
            return False
    
    def describe_parameter(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a parameter without the value.
        
        Args:
            name: Full parameter name
            
        Returns:
            Parameter metadata or None if not found
        """
        try:
            response = self.client.describe_parameters(
                ParameterFilters=[
                    {
                        'Key': 'Name',
                        'Option': 'Equals',
                        'Values': [name]
                    }
                ]
            )
            
            params = response.get('Parameters', [])
            if params:
                param = params[0]
                return {
                    "name": param.get('Name'),
                    "type": param.get('Type'),
                    "description": param.get('Description', ''),
                    "last_modified": param.get('LastModifiedDate').isoformat() if param.get('LastModifiedDate') else None,
                    "version": param.get('Version')
                }
            return None
            
        except Exception as e:
            logger.warning(f"Failed to describe SSM parameter {name}: {e}")
            return None

