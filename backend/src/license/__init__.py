"""
License Enablement Module

This module provides comprehensive license management for the AI Job Engine MCP Server.
It includes license activation, validation, status checking, feature gating, and audit logging.
"""

from .models.enums import LicenseTier, LicenseStatus, LicenseEventType
from .models.license_model import LicenseRecord, LicenseAuditEntry, FeatureTierMapping

# Lazy imports to avoid circular dependencies
def get_license_integration():
    """Get the global license integration instance."""
    from .integration import get_license_integration as _get
    return _get()

def create_license_integration(**kwargs):
    """Create a new license integration instance."""
    from .integration import create_license_integration as _create
    return _create(**kwargs)

__all__ = [
    # Enums
    "LicenseTier",
    "LicenseStatus", 
    "LicenseEventType",
    # Models
    "LicenseRecord",
    "LicenseAuditEntry",
    "FeatureTierMapping",
    # Integration
    "get_license_integration",
    "create_license_integration",
]
