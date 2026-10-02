"""
License Enums

Defines enumeration types for license management including tiers, statuses, and event types.
"""

from enum import Enum


class LicenseTier(str, Enum):
    """License tier levels with hierarchical ordering."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    
    @classmethod
    def get_tier_level(cls, tier: "LicenseTier") -> int:
        """Get numeric level for tier comparison."""
        levels = {
            cls.BASIC: 1,
            cls.PROFESSIONAL: 2,
            cls.ENTERPRISE: 3,
        }
        return levels.get(tier, 0)
    
    def __ge__(self, other: "LicenseTier") -> bool:
        """Compare tiers by level."""
        if not isinstance(other, LicenseTier):
            return NotImplemented
        return self.get_tier_level(self) >= self.get_tier_level(other)
    
    def __gt__(self, other: "LicenseTier") -> bool:
        """Compare tiers by level."""
        if not isinstance(other, LicenseTier):
            return NotImplemented
        return self.get_tier_level(self) > self.get_tier_level(other)
    
    def __le__(self, other: "LicenseTier") -> bool:
        """Compare tiers by level."""
        if not isinstance(other, LicenseTier):
            return NotImplemented
        return self.get_tier_level(self) <= self.get_tier_level(other)
    
    def __lt__(self, other: "LicenseTier") -> bool:
        """Compare tiers by level."""
        if not isinstance(other, LicenseTier):
            return NotImplemented
        return self.get_tier_level(self) < self.get_tier_level(other)


class LicenseStatus(str, Enum):
    """License status values."""
    ACTIVE = "active"
    EXPIRED = "expired"
    GRACE_PERIOD = "grace_period"
    REVOKED = "revoked"
    DEACTIVATED = "deactivated"
    NOT_ACTIVATED = "not_activated"


class LicenseEventType(str, Enum):
    """License audit event types."""
    ACTIVATED = "license_activated"
    VALIDATED = "license_validated"
    VALIDATION_FAILED = "license_validation_failed"
    DEACTIVATED = "license_deactivated"
    RENEWED = "license_renewed"
    EXPIRED = "license_expired"
    GRACE_PERIOD_STARTED = "grace_period_started"
    GRACE_PERIOD_ENDED = "grace_period_ended"
    FEATURE_ACCESS_DENIED = "feature_access_denied"
    FEATURE_ACCESS_GRANTED = "feature_access_granted"


# License key format version prefixes
LICENSE_KEY_VERSION_PREFIX = "v1"

# Tier abbreviations used in license keys
TIER_ABBREVIATIONS = {
    "BAS": LicenseTier.BASIC,
    "PRO": LicenseTier.PROFESSIONAL,
    "ENT": LicenseTier.ENTERPRISE,
}

# Reverse mapping for encoding
TIER_TO_ABBREVIATION = {v: k for k, v in TIER_ABBREVIATIONS.items()}
