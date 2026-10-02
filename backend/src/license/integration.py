"""
License Integration Module

Provides integration helpers for wiring license functionality into the HTTP gateway.
"""

from typing import Optional
from loguru import logger

from .services.license_service import LicenseService
from .services.license_repository import LicenseRepository, AuditRepository
from .services.cache_manager import get_cache_manager
from .services.audit_service import AuditService
from .services.feature_service import get_feature_service
from .middleware.license_middleware import LicenseMiddleware, get_license_middleware
from .apis.license_api import router as license_router, init_services as init_api_services
from .tools.license_tool import init_license_tool, license_tool
from .utils.crypto import LicenseCrypto
from .models.enums import LicenseTier


class LicenseIntegration:
    """
    Integration helper for license functionality.
    
    Provides a single entry point for initializing all license components
    and wiring them into the HTTP gateway.
    """
    
    def __init__(
        self,
        instance_id: Optional[str] = None,
        enable_middleware: bool = True,
        feature_requirements: Optional[dict] = None,
    ):
        """
        Initialize license integration.
        
        Args:
            instance_id: Instance identifier (auto-generated if None)
            enable_middleware: Whether to enable license middleware
            feature_requirements: Map of endpoint patterns to required tiers
        """
        self._instance_id = instance_id
        self._enable_middleware = enable_middleware
        self._feature_requirements = feature_requirements or {}
        
        # Components (initialized lazily)
        self._license_service: Optional[LicenseService] = None
        self._audit_service: Optional[AuditService] = None
        self._middleware: Optional[LicenseMiddleware] = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all license components."""
        if self._initialized:
            return
        
        logger.info("Initializing license integration...")
        
        # Create repositories
        license_repo = LicenseRepository()
        audit_repo = AuditRepository()
        
        # Create services
        cache = get_cache_manager()
        crypto = LicenseCrypto()
        
        self._license_service = LicenseService(
            repository=license_repo,
            audit_repository=audit_repo,
            cache_manager=cache,
            crypto=crypto,
            instance_id=self._instance_id,
        )
        
        self._audit_service = AuditService(repository=audit_repo)
        
        # Initialize API services
        init_api_services(self._license_service, self._audit_service)
        
        # Initialize MCP tool
        init_license_tool(self._license_service, self._audit_service)
        
        # Initialize middleware
        if self._enable_middleware:
            self._middleware = get_license_middleware()
            self._middleware.set_license_service(self._license_service)
            
            # Set feature requirements
            for path, tier in self._feature_requirements.items():
                self._middleware.set_feature_requirement(path, tier)
        
        self._initialized = True
        logger.info("License integration initialized successfully")
    
    @property
    def license_service(self) -> LicenseService:
        """Get the license service."""
        if not self._initialized:
            self.initialize()
        return self._license_service
    
    @property
    def audit_service(self) -> AuditService:
        """Get the audit service."""
        if not self._initialized:
            self.initialize()
        return self._audit_service
    
    @property
    def middleware(self) -> Optional[LicenseMiddleware]:
        """Get the license middleware."""
        if not self._initialized:
            self.initialize()
        return self._middleware
    
    @property
    def api_router(self):
        """Get the license API router."""
        return license_router
    
    @property
    def mcp_tool(self):
        """Get the license MCP tool function."""
        return license_tool
    
    async def validate_request(self, path: str, method: str = "GET") -> bool:
        """
        Validate a request using the middleware.
        
        Args:
            path: Request path
            method: HTTP method
            
        Returns:
            True if request is allowed
            
        Raises:
            LicenseMiddlewareError: If validation fails
        """
        if not self._middleware:
            return True
        
        await self._middleware.validate_request(path, method)
        return True


# Default feature requirements for common endpoints
DEFAULT_FEATURE_REQUIREMENTS = {
    "/api/v1/journeys/*": LicenseTier.BASIC,
    "/api/v1/analytics/*": LicenseTier.PROFESSIONAL,
    "/api/v1/export/*": LicenseTier.PROFESSIONAL,
    "/api/v1/second-brain/*": LicenseTier.PROFESSIONAL,
    "/api/v1/audit/*": LicenseTier.ENTERPRISE,
    "/api/v1/admin/*": LicenseTier.ENTERPRISE,
}


def create_license_integration(
    instance_id: Optional[str] = None,
    enable_middleware: bool = True,
    use_default_requirements: bool = True,
    custom_requirements: Optional[dict] = None,
) -> LicenseIntegration:
    """
    Create and initialize a license integration instance.
    
    Args:
        instance_id: Instance identifier
        enable_middleware: Whether to enable middleware
        use_default_requirements: Whether to use default feature requirements
        custom_requirements: Additional custom requirements
        
    Returns:
        Initialized LicenseIntegration instance
    """
    requirements = {}
    
    if use_default_requirements:
        requirements.update(DEFAULT_FEATURE_REQUIREMENTS)
    
    if custom_requirements:
        requirements.update(custom_requirements)
    
    integration = LicenseIntegration(
        instance_id=instance_id,
        enable_middleware=enable_middleware,
        feature_requirements=requirements,
    )
    
    integration.initialize()
    return integration


# Singleton instance
_integration: Optional[LicenseIntegration] = None


def get_license_integration() -> LicenseIntegration:
    """Get or create the global license integration instance."""
    global _integration
    if _integration is None:
        _integration = create_license_integration()
    return _integration


def reset_license_integration() -> None:
    """Reset the global license integration (for testing)."""
    global _integration
    _integration = None
