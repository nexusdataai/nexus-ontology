"""
License Constants

Central location for all license-related configuration constants.
"""

from typing import List, Dict
from .models.enums import LicenseTier

# Grace period configuration
DEFAULT_GRACE_PERIOD_DAYS = 7

# Cache configuration
LICENSE_CACHE_TTL_SECONDS = 300  # 5 minutes
VALIDATION_CACHE_TTL_SECONDS = 60  # 1 minute

# Expiration warning threshold
EXPIRATION_WARNING_DAYS = 30

# Renewal window
RENEWAL_WINDOW_DAYS = 90  # Can renew up to 90 days before expiration

# Audit log retention
AUDIT_LOG_RETENTION_YEARS = 2

# Public endpoints that bypass license validation
PUBLIC_ENDPOINTS: List[str] = [
    "/health",
    "/api/v1/license/activate",
    "/api/v1/license/status",
    "/tools",  # MCP tools listing
]

# Feature to tier mapping
# Features available at each tier level
FEATURE_TIER_MAPPING: Dict[str, LicenseTier] = {
    # Basic tier features
    "journeys": LicenseTier.BASIC,
    "basic_analytics": LicenseTier.BASIC,
    
    # Professional tier features
    "second_brain": LicenseTier.PROFESSIONAL,
    "advanced_analytics": LicenseTier.PROFESSIONAL,
    "export": LicenseTier.PROFESSIONAL,
    
    # Enterprise tier features
    "custom_stages": LicenseTier.ENTERPRISE,
    "api_access": LicenseTier.ENTERPRISE,
    "audit_logs": LicenseTier.ENTERPRISE,
    "multi_tenant": LicenseTier.ENTERPRISE,
}

# All features list
ALL_FEATURES = list(FEATURE_TIER_MAPPING.keys())

# Features by tier (cumulative - higher tiers include lower tier features)
TIER_FEATURES: Dict[LicenseTier, List[str]] = {
    LicenseTier.BASIC: [
        f for f, t in FEATURE_TIER_MAPPING.items() 
        if t == LicenseTier.BASIC
    ],
    LicenseTier.PROFESSIONAL: [
        f for f, t in FEATURE_TIER_MAPPING.items() 
        if t in (LicenseTier.BASIC, LicenseTier.PROFESSIONAL)
    ],
    LicenseTier.ENTERPRISE: ALL_FEATURES,  # Enterprise gets all features
}

# Error codes
class LicenseErrorCode:
    """License-related error codes."""
    INVALID_FORMAT = "LICENSE_INVALID_FORMAT"
    SIGNATURE_INVALID = "LICENSE_SIGNATURE_INVALID"
    EXPIRED = "LICENSE_EXPIRED"
    NOT_ACTIVATED = "LICENSE_NOT_ACTIVATED"
    REVOKED = "LICENSE_REVOKED"
    ALREADY_ACTIVATED = "LICENSE_ALREADY_ACTIVATED"
    FEATURE_NOT_LICENSED = "FEATURE_NOT_LICENSED"
    RENEWAL_INVALID = "LICENSE_RENEWAL_INVALID"
    DEACTIVATION_FAILED = "LICENSE_DEACTIVATION_FAILED"
    VALIDATION_ERROR = "LICENSE_VALIDATION_ERROR"

# DynamoDB table configuration (single-table design)
# These are fallback values; use get_license_table_name() for dynamic names
_LICENSE_TABLE_FALLBACK = "license"


def get_license_table_name() -> str:
    """
    Get the license DynamoDB table name from configuration.
    
    Returns:
        Table name following call-processing-{env}-license pattern
    """
    try:
        from ..config.config_provider import get_config
        return get_config().dynamodb_license_table
    except ImportError:
        return _LICENSE_TABLE_FALLBACK


def get_license_audit_table_name() -> str:
    """
    Get the license audit DynamoDB table name from configuration.
    
    Uses the same table as license records (single-table design).
    
    Returns:
        Table name following call-processing-{env}-license pattern
    """
    return get_license_table_name()


# Backwards compatibility - these will be deprecated
# Use get_license_table_name() instead
LICENSE_TABLE_NAME = _LICENSE_TABLE_FALLBACK
LICENSE_AUDIT_TABLE_NAME = _LICENSE_TABLE_FALLBACK  # Same table, different PK pattern

# License key format components
LICENSE_KEY_SEPARATOR = "."
LICENSE_KEY_COMPONENTS = ["version", "tier", "expiration", "holder_id", "features", "signature"]
