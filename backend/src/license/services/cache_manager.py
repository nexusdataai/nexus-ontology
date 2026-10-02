"""
License Cache Manager

In-memory cache for license validation results with configurable TTL.
Supports cache invalidation on deactivation.
"""

import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from threading import Lock
from loguru import logger

from ..models.license_model import LicenseRecord
from ..models.api_models import LicenseValidationResult
from ..consts import LICENSE_CACHE_TTL_SECONDS, VALIDATION_CACHE_TTL_SECONDS


@dataclass
class CacheEntry:
    """A single cache entry with expiration."""
    value: Any
    expires_at: float  # Unix timestamp
    created_at: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() > self.expires_at


class LicenseCacheManager:
    """
    In-memory cache manager for license data.
    
    Provides caching for:
    - License records (longer TTL)
    - Validation results (shorter TTL)
    
    Thread-safe with lock protection.
    """
    
    def __init__(
        self,
        license_ttl: int = LICENSE_CACHE_TTL_SECONDS,
        validation_ttl: int = VALIDATION_CACHE_TTL_SECONDS,
    ):
        """
        Initialize cache manager.
        
        Args:
            license_ttl: TTL for license records in seconds
            validation_ttl: TTL for validation results in seconds
        """
        self._license_ttl = license_ttl
        self._validation_ttl = validation_ttl
        
        # Separate caches for different data types
        self._license_cache: Dict[str, CacheEntry] = {}
        self._validation_cache: Dict[str, CacheEntry] = {}
        
        # Thread safety
        self._lock = Lock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
    
    def get_license(self, instance_id: str) -> Optional[LicenseRecord]:
        """
        Get cached license record for instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            Cached license record or None
        """
        with self._lock:
            key = f"license:{instance_id}"
            entry = self._license_cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._license_cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set_license(self, instance_id: str, record: LicenseRecord) -> None:
        """
        Cache a license record.
        
        Args:
            instance_id: Instance identifier
            record: License record to cache
        """
        with self._lock:
            key = f"license:{instance_id}"
            expires_at = time.time() + self._license_ttl
            self._license_cache[key] = CacheEntry(value=record, expires_at=expires_at)
            logger.debug(f"Cached license for instance {instance_id}")
    
    def get_validation(self, instance_id: str) -> Optional[LicenseValidationResult]:
        """
        Get cached validation result for instance.
        
        Args:
            instance_id: Instance identifier
            
        Returns:
            Cached validation result or None
        """
        with self._lock:
            key = f"validation:{instance_id}"
            entry = self._validation_cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._validation_cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.value
    
    def set_validation(self, instance_id: str, result: LicenseValidationResult) -> None:
        """
        Cache a validation result.
        
        Args:
            instance_id: Instance identifier
            result: Validation result to cache
        """
        with self._lock:
            key = f"validation:{instance_id}"
            expires_at = time.time() + self._validation_ttl
            self._validation_cache[key] = CacheEntry(value=result, expires_at=expires_at)
            logger.debug(f"Cached validation for instance {instance_id}")
    
    def invalidate_license(self, instance_id: str) -> None:
        """
        Invalidate cached license and validation for instance.
        
        Called on deactivation to ensure fresh data is fetched.
        
        Args:
            instance_id: Instance identifier
        """
        with self._lock:
            license_key = f"license:{instance_id}"
            validation_key = f"validation:{instance_id}"
            
            if license_key in self._license_cache:
                del self._license_cache[license_key]
                logger.debug(f"Invalidated license cache for {instance_id}")
            
            if validation_key in self._validation_cache:
                del self._validation_cache[validation_key]
                logger.debug(f"Invalidated validation cache for {instance_id}")
    
    def invalidate_all(self) -> None:
        """Clear all cached data."""
        with self._lock:
            self._license_cache.clear()
            self._validation_cache.clear()
            logger.info("Cleared all license caches")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        removed = 0
        with self._lock:
            # Clean license cache
            expired_keys = [
                k for k, v in self._license_cache.items() 
                if v.is_expired()
            ]
            for key in expired_keys:
                del self._license_cache[key]
                removed += 1
            
            # Clean validation cache
            expired_keys = [
                k for k, v in self._validation_cache.items() 
                if v.is_expired()
            ]
            for key in expired_keys:
                del self._validation_cache[key]
                removed += 1
        
        if removed > 0:
            logger.debug(f"Cleaned up {removed} expired cache entries")
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "license_entries": len(self._license_cache),
                "validation_entries": len(self._validation_cache),
                "license_ttl_seconds": self._license_ttl,
                "validation_ttl_seconds": self._validation_ttl,
            }
    
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._hits = 0
            self._misses = 0


# Global cache instance
_cache_instance: Optional[LicenseCacheManager] = None


def get_cache_manager() -> LicenseCacheManager:
    """Get or create the global cache manager instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LicenseCacheManager()
    return _cache_instance


def reset_cache_manager() -> None:
    """Reset the global cache manager (for testing)."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.invalidate_all()
    _cache_instance = None
