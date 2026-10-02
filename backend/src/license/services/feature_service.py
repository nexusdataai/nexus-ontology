"""
Feature Service

Manages feature-to-tier mappings and feature access checks.
Implements tier hierarchy logic for feature gating.
"""

from typing import Optional, List, Dict
from loguru import logger

from ..models.enums import LicenseTier, LicenseStatus
from ..models.license_model import LicenseRecord, FeatureTierMapping
from ..models.api_models import FeatureAccessData
from ..consts import FEATURE_TIER_MAPPING, TIER_FEATURES, LicenseErrorCode


class FeatureService:
    """
    Service for managing feature access based on license tier.
    
    Implements tier hierarchy where higher tiers include all features
    from lower tiers. Enterprise tier has access to all features.
    """
    
    # Tier hierarchy levels (higher number = more features)
    TIER_LEVELS = {
        LicenseTier.BASIC: 1,
        LicenseTier.PROFESSIONAL: 2,
        LicenseTier.ENTERPRISE: 3,
    }
    
    def __init__(self, custom_mappings: Optional[Dict[str, LicenseTier]] = None):
        """
        Initialize feature service.
        
        Args:
            custom_mappings: Optional custom feature-to-tier mappings
        """
        self._mappings = custom_mappings or FEATURE_TIER_MAPPING
    
    def check_feature_access(
        self,
        feature_id: str,
        license_record: Optional[LicenseRecord],
    ) -> FeatureAccessData:
        """
        Check if a license permits access to a specific feature.
        
        Args:
            feature_id: The feature to check
            license_record: The current license record (or None if not activated)
            
        Returns:
            FeatureAccessData with access status
        """
        # Get required tier for feature
        required_tier = self._mappings.get(feature_id)
        
        if required_tier is None:
            # Unknown feature - deny by default
            logger.warning(f"Unknown feature requested: {feature_id}")
            return FeatureAccessData(
                feature_id=feature_id,
                is_allowed=False,
                required_tier=LicenseTier.ENTERPRISE,
                current_tier=None,
                upgrade_message=f"Unknown feature: {feature_id}",
            )
        
        # Check if license exists and is active
        if not license_record:
            return FeatureAccessData(
                feature_id=feature_id,
                is_allowed=False,
                required_tier=required_tier,
                current_tier=None,
                upgrade_message="No active license",
            )
        
        if license_record.status != LicenseStatus.ACTIVE:
            return FeatureAccessData(
                feature_id=feature_id,
                is_allowed=False,
                required_tier=required_tier,
                current_tier=license_record.tier,
                upgrade_message=f"License is {license_record.status.value}",
            )
        
        # Check tier hierarchy
        is_allowed = self._tier_has_access(license_record.tier, required_tier)
        
        upgrade_message = None
        if not is_allowed:
            upgrade_message = f"Upgrade to {required_tier.value} tier to access this feature"
        
        return FeatureAccessData(
            feature_id=feature_id,
            is_allowed=is_allowed,
            required_tier=required_tier,
            current_tier=license_record.tier,
            upgrade_message=upgrade_message,
        )
    
    def _tier_has_access(self, current_tier: LicenseTier, required_tier: LicenseTier) -> bool:
        """
        Check if current tier has access to features requiring the specified tier.
        
        Uses tier hierarchy: Enterprise >= Professional >= Basic
        """
        current_level = self.TIER_LEVELS.get(current_tier, 0)
        required_level = self.TIER_LEVELS.get(required_tier, 0)
        return current_level >= required_level
    
    def get_features_for_tier(self, tier: LicenseTier) -> List[str]:
        """
        Get all features available for a specific tier.
        
        Args:
            tier: The license tier
            
        Returns:
            List of feature IDs available for this tier
        """
        if tier == LicenseTier.ENTERPRISE:
            # Enterprise gets all features
            return list(self._mappings.keys())
        
        return TIER_FEATURES.get(tier, [])
    
    def get_all_features(self) -> List[Dict[str, any]]:
        """
        Get all features with their required tiers.
        
        Returns:
            List of feature info dicts
        """
        return [
            {
                "feature_id": feature_id,
                "required_tier": tier.value,
            }
            for feature_id, tier in self._mappings.items()
        ]
    
    def get_required_tier(self, feature_id: str) -> Optional[LicenseTier]:
        """
        Get the required tier for a feature.
        
        Args:
            feature_id: The feature to check
            
        Returns:
            Required tier or None if feature unknown
        """
        return self._mappings.get(feature_id)
    
    def is_enterprise_feature(self, feature_id: str) -> bool:
        """Check if a feature requires enterprise tier."""
        required = self._mappings.get(feature_id)
        return required == LicenseTier.ENTERPRISE if required else False
    
    def is_professional_feature(self, feature_id: str) -> bool:
        """Check if a feature requires professional tier or higher."""
        required = self._mappings.get(feature_id)
        if not required:
            return False
        return required in (LicenseTier.PROFESSIONAL, LicenseTier.ENTERPRISE)
    
    def is_basic_feature(self, feature_id: str) -> bool:
        """Check if a feature is available at basic tier."""
        required = self._mappings.get(feature_id)
        return required == LicenseTier.BASIC if required else False


# Singleton instance
_feature_service: Optional[FeatureService] = None


def get_feature_service() -> FeatureService:
    """Get or create the global feature service instance."""
    global _feature_service
    if _feature_service is None:
        _feature_service = FeatureService()
    return _feature_service


def reset_feature_service() -> None:
    """Reset the global feature service (for testing)."""
    global _feature_service
    _feature_service = None
