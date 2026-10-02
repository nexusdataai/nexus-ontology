"""
License Middleware

Middleware for license validation on API requests.
Intercepts requests to protected endpoints and verifies license validity.
"""

from typing import Callable, Optional, List, Dict, Any
from datetime import datetime, timezone
from loguru import logger

from ..models.enums import LicenseStatus, LicenseTier
from ..models.api_models import LicenseValidationResult, LicenseErrorResponse
from ..services.license_service import LicenseService
from ..services.feature_service import FeatureService, get_feature_service
from ..services.cache_manager import LicenseCacheManager, get_cache_manager
from ..consts import PUBLIC_ENDPOINTS, LicenseErrorCode


class LicenseMiddlewareError(Exception):
    """Exception raised for middleware errors."""
    def __init__(self, message: str, error_code: str, status_code: int = 403):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(message)


class LicenseMiddleware:
    """
    Middleware for license validation on API requests.
    
    Intercepts requests to protected endpoints and:
    1. Checks if endpoint is public (bypass validation)
    2. Validates license is active
    3. Checks feature access based on tier
    4. Caches validation results for performance
    """
    
    def __init__(
        self,
        license_service: Optional[LicenseService] = None,
        feature_service: Optional[FeatureService] = None,
        cache_manager: Optional[LicenseCacheManager] = None,
        public_endpoints: Optional[List[str]] = None,
        feature_requirements: Optional[Dict[str, LicenseTier]] = None,
    ):
        """
        Initialize license middleware.
        
        Args:
            license_service: License service instance
            feature_service: Feature service instance
            cache_manager: Cache manager instance
            public_endpoints: List of endpoints that bypass validation
            feature_requirements: Map of endpoint patterns to required tiers
        """
        self._license_service = license_service
        self._feature_service = feature_service or get_feature_service()
        self._cache = cache_manager or get_cache_manager()
        self._public_endpoints = public_endpoints or PUBLIC_ENDPOINTS
        self._feature_requirements = feature_requirements or {}
    
    def set_license_service(self, service: LicenseService) -> None:
        """Set the license service (for lazy initialization)."""
        self._license_service = service
    
    def is_public_endpoint(self, path: str) -> bool:
        """
        Check if endpoint bypasses license validation.
        
        Args:
            path: Request path
            
        Returns:
            True if endpoint is public
        """
        # Normalize path
        path = path.rstrip('/')
        
        for public_path in self._public_endpoints:
            public_path = public_path.rstrip('/')
            
            # Exact match
            if path == public_path:
                return True
            
            # Prefix match (for paths like /api/v1/license/*)
            if path.startswith(public_path + '/'):
                return True
            
            # Wildcard match
            if public_path.endswith('*'):
                prefix = public_path[:-1]
                if path.startswith(prefix):
                    return True
        
        return False
    
    async def validate_request(
        self,
        path: str,
        method: str = "GET",
    ) -> LicenseValidationResult:
        """
        Validate a request against license requirements.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            LicenseValidationResult
            
        Raises:
            LicenseMiddlewareError: If validation fails
        """
        # Check if public endpoint
        if self.is_public_endpoint(path):
            return LicenseValidationResult(
                is_valid=True,
                status=LicenseStatus.ACTIVE,
                message="Public endpoint - no license required",
                can_write=True,
            )
        
        # Ensure license service is available
        if not self._license_service:
            raise LicenseMiddlewareError(
                "License service not initialized",
                LicenseErrorCode.VALIDATION_ERROR,
                status_code=500,
            )
        
        # Validate license
        validation = await self._license_service.validate_license()
        
        if not validation.is_valid:
            raise LicenseMiddlewareError(
                validation.message or "License validation failed",
                validation.error_code or LicenseErrorCode.NOT_ACTIVATED,
                status_code=403,
            )
        
        # Check write permission for non-GET requests during grace period
        if method != "GET" and not validation.can_write:
            raise LicenseMiddlewareError(
                "Write operations not permitted during grace period",
                LicenseErrorCode.EXPIRED,
                status_code=403,
            )
        
        # Check feature requirements for this endpoint
        required_tier = self._get_required_tier(path)
        if required_tier and validation.tier:
            if not self._tier_has_access(validation.tier, required_tier):
                raise LicenseMiddlewareError(
                    f"This feature requires {required_tier.value} tier",
                    LicenseErrorCode.FEATURE_NOT_LICENSED,
                    status_code=403,
                )
        
        return validation
    
    def _get_required_tier(self, path: str) -> Optional[LicenseTier]:
        """Get the required tier for an endpoint."""
        path = path.rstrip('/')
        
        for pattern, tier in self._feature_requirements.items():
            pattern = pattern.rstrip('/')
            
            # Exact match
            if path == pattern:
                return tier
            
            # Prefix match
            if pattern.endswith('*'):
                prefix = pattern[:-1]
                if path.startswith(prefix):
                    return tier
        
        return None
    
    def _tier_has_access(self, current: LicenseTier, required: LicenseTier) -> bool:
        """Check if current tier has access to required tier features."""
        tier_levels = {
            LicenseTier.BASIC: 1,
            LicenseTier.PROFESSIONAL: 2,
            LicenseTier.ENTERPRISE: 3,
        }
        return tier_levels.get(current, 0) >= tier_levels.get(required, 0)
    
    def create_error_response(self, error: LicenseMiddlewareError) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "status": "error",
            "message": error.message,
            "error_code": error.error_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def add_public_endpoint(self, path: str) -> None:
        """Add a public endpoint that bypasses validation."""
        if path not in self._public_endpoints:
            self._public_endpoints.append(path)
    
    def remove_public_endpoint(self, path: str) -> None:
        """Remove a public endpoint."""
        if path in self._public_endpoints:
            self._public_endpoints.remove(path)
    
    def set_feature_requirement(self, path: str, tier: LicenseTier) -> None:
        """Set the required tier for an endpoint."""
        self._feature_requirements[path] = tier
    
    def get_public_endpoints(self) -> List[str]:
        """Get list of public endpoints."""
        return self._public_endpoints.copy()


# Singleton instance
_middleware_instance: Optional[LicenseMiddleware] = None


def get_license_middleware() -> LicenseMiddleware:
    """Get or create the global license middleware instance."""
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = LicenseMiddleware()
    return _middleware_instance


def reset_license_middleware() -> None:
    """Reset the global license middleware (for testing)."""
    global _middleware_instance
    _middleware_instance = None
