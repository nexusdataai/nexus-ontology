"""
S3 Helper Utility for reading analysis data from S3
Provides cached S3 reads with automatic retry and error handling

Memory-safety: Includes cache size limits and automatic eviction.
"""

import json
import sys
import boto3
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
from botocore.exceptions import ClientError, BotoCoreError
import tempfile

# Memory safety configuration
MAX_CACHE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB max cache size per reader
MAX_CACHE_OBJECT_SIZE_BYTES = 50 * 1024 * 1024  # 50MB max single object size


class S3DataReader:
    """Helper class to read analysis data from S3 with caching and size limits."""
    
    def __init__(self, bucket: str, key: str, region: str = 'us-east-1', 
                 max_cache_size: int = MAX_CACHE_SIZE_BYTES):
        """
        Initialize S3 data reader.
        
        Args:
            bucket: S3 bucket name (e.g., 'econet-alerts')
            key: S3 object key (e.g., 'classifications/result.json')
            region: AWS region
            max_cache_size: Maximum cache size in bytes
        """
        self.bucket = bucket
        self.key = key
        self.region = region
        self.s3_client = None
        self._cached_data = None
        self._cache_timestamp = None
        self._cached_size = 0
        self._max_cache_size = max_cache_size
    
    def _get_s3_client(self):
        """Get or create S3 client."""
        if self.s3_client is None:
            self.s3_client = boto3.client('s3', region_name=self.region)
        return self.s3_client
    
    async def read_json(self, use_cache: bool = True, cache_ttl_seconds: int = 300) -> Dict[str, Any]:
        """
        Read JSON data from S3 with optional caching and size limits.
        
        Args:
            use_cache: Whether to use cached data if available
            cache_ttl_seconds: Cache time-to-live in seconds (default 5 minutes)
            
        Returns:
            Dictionary containing the JSON data from S3
            
        Raises:
            Exception: If S3 read fails
        """
        import time
        
        # Check cache validity
        if use_cache and self._cached_data is not None and self._cache_timestamp is not None:
            age = time.time() - self._cache_timestamp
            if age < cache_ttl_seconds:
                logger.info(f"Using cached S3 data (age: {age:.1f}s, TTL: {cache_ttl_seconds}s, size: {self._cached_size // 1024}KB)")
                return self._cached_data
            else:
                logger.info(f"Cache expired (age: {age:.1f}s, TTL: {cache_ttl_seconds}s), fetching from S3")
                # Clear expired cache to free memory
                self.clear_cache()
        
        try:
            s3_path = f"s3://{self.bucket}/{self.key}"
            logger.info(f"Reading analysis data from {s3_path}")
            
            s3_client = self._get_s3_client()
            
            # First check object size before downloading
            try:
                head_response = s3_client.head_object(Bucket=self.bucket, Key=self.key)
                content_length = head_response.get('ContentLength', 0)
                
                if content_length > MAX_CACHE_OBJECT_SIZE_BYTES:
                    logger.warning(f"Object too large to cache ({content_length // 1024 // 1024}MB > {MAX_CACHE_OBJECT_SIZE_BYTES // 1024 // 1024}MB limit)")
            except ClientError:
                content_length = 0  # Unknown size, proceed anyway
            
            # Download S3 object
            response = s3_client.get_object(Bucket=self.bucket, Key=self.key)
            data_bytes = response['Body'].read()
            data_size = len(data_bytes)
            
            # Parse JSON
            data = json.loads(data_bytes.decode('utf-8'))
            
            # Only cache if within size limits
            if data_size <= self._max_cache_size and data_size <= MAX_CACHE_OBJECT_SIZE_BYTES:
                self._cached_data = data
                self._cache_timestamp = time.time()
                self._cached_size = data_size
                logger.debug(f"Cached S3 data ({data_size // 1024}KB)")
            else:
                logger.info(f"Object too large to cache ({data_size // 1024 // 1024}MB), returning without caching")
                self.clear_cache()
            
            # Log success
            data_size_mb = data_size / (1024 * 1024)
            logger.info(f"✅ Successfully loaded {data_size_mb:.2f} MB from S3: {s3_path}")
            
            return data
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                logger.error(f"❌ S3 object not found: s3://{self.bucket}/{self.key}")
                raise FileNotFoundError(f"S3 object not found: s3://{self.bucket}/{self.key}")
            elif error_code == 'NoSuchBucket':
                logger.error(f"❌ S3 bucket not found: {self.bucket}")
                raise FileNotFoundError(f"S3 bucket not found: {self.bucket}")
            else:
                logger.error(f"❌ S3 client error: {error_code} - {str(e)}")
                raise Exception(f"S3 read error: {error_code}")
                
        except BotoCoreError as e:
            logger.error(f"❌ Boto core error reading from S3: {str(e)}")
            raise Exception(f"S3 connection error: {str(e)}")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in S3 object: {str(e)}")
            raise Exception(f"Invalid JSON in S3 object: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error reading from S3: {str(e)}")
            raise
    
    def clear_cache(self):
        """Clear the cached data to free memory."""
        self._cached_data = None
        self._cache_timestamp = None
        self._cached_size = 0
        logger.debug("S3 data cache cleared")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the current cache state."""
        import time
        
        if self._cached_data is None:
            return {
                "cached": False,
                "max_cache_size_bytes": self._max_cache_size,
                "max_object_size_bytes": MAX_CACHE_OBJECT_SIZE_BYTES,
            }
        
        age = time.time() - self._cache_timestamp if self._cache_timestamp else 0
        return {
            "cached": True,
            "cache_age_seconds": round(age, 2),
            "cache_timestamp": self._cache_timestamp,
            "cached_size_bytes": self._cached_size,
            "cached_size_kb": self._cached_size // 1024,
            "max_cache_size_bytes": self._max_cache_size,
            "max_object_size_bytes": MAX_CACHE_OBJECT_SIZE_BYTES,
            "data_size_keys": len(self._cached_data.keys()) if isinstance(self._cached_data, dict) else 0,
            "utilization_percent": round(self._cached_size / self._max_cache_size * 100, 1) if self._max_cache_size > 0 else 0
        }


def create_s3_reader(bucket: str, 
                    key: str,
                    region: Optional[str] = None) -> S3DataReader:
    """
    Create an S3 data reader with configuration.
    
    Args:
        bucket: S3 bucket name (required - use ConfigProvider for environment-aware names)
        key: S3 object key (required)
        region: AWS region (optional - defaults to ConfigProvider's aws_region)
        
    Returns:
        Configured S3DataReader instance
        
    Example:
        from src.config.config_provider import get_config
        config = get_config()
        reader = create_s3_reader(
            bucket=config.s3_recordings_bucket,
            key="path/to/file.json"
        )
    """
    # Get region from ConfigProvider if not specified
    if region is None:
        try:
            from ..config.config_provider import get_config
            region = get_config().aws_region
        except ImportError:
            region = 'us-east-1'  # Fallback to default region
    
    return S3DataReader(bucket=bucket, key=key, region=region)


async def read_s3_json(bucket: str, key: str, region: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to read JSON from S3.
    
    Args:
        bucket: S3 bucket name (required - use ConfigProvider for environment-aware names)
        key: S3 object key
        region: AWS region (optional - defaults to ConfigProvider's aws_region)
        
    Returns:
        Dictionary containing the JSON data
        
    Example:
        from src.config.config_provider import get_config
        config = get_config()
        data = await read_s3_json(
            bucket=config.s3_recordings_bucket,
            key="path/to/file.json"
        )
    """
    # Get region from ConfigProvider if not specified
    if region is None:
        try:
            from ..config.config_provider import get_config
            region = get_config().aws_region
        except ImportError:
            region = 'us-east-1'  # Fallback to default region
    
    reader = S3DataReader(bucket=bucket, key=key, region=region)
    return await reader.read_json(use_cache=False)
