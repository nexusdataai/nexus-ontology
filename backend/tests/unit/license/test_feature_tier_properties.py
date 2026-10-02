"""
Property-Based Tests for Feature Tier Gating

Feature: license-enablement, Property 11: Feature Tier Gating
Validates: Requirements 6.1, 6.2, 6.4, 6.5

Tests that feature access is correctly gated by license tier.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.license_model import LicenseRecord
from license.models.enums import LicenseTier, LicenseStatus
from license.services.feature_service import FeatureService
from license.consts import FEATURE_TIER_MAPPING, TIER_FEATURES


# ==========================================
# Custom Strategies
# ==========================================

@st.composite
def valid_tier(draw):
    """Generate valid license tiers."""
    return draw(st.sampled_from(list(LicenseTier)))


@st.composite
def valid_feature_id(draw):
    """Generate valid feature IDs from the mapping."""
    return draw(st.sampled_from(list(FEATURE_TIER_MAPPING.keys())))


@st.composite
def basic_feature(draw):
    """Generate features that require basic tier."""
    basic_features = [f for f, t in FEATURE_TIER_MAPPING.items() if t == LicenseTier.BASIC]
    if not basic_features:
        return draw(st.just("journeys"))  # Default basic feature
    return draw(st.sampled_from(basic_features))


@st.composite
def professional_feature(draw):
    """Generate features that require professional tier."""
    pro_features = [f for f, t in FEATURE_TIER_MAPPING.items() if t == LicenseTier.PROFESSIONAL]
    if not pro_features:
        return draw(st.just("second_brain"))  # Default pro feature
    return draw(st.sampled_from(pro_features))


@st.composite
def enterprise_feature(draw):
    """Generate features that require enterprise tier."""
    ent_features = [f for f, t in FEATURE_TIER_MAPPING.items() if t == LicenseTier.ENTERPRISE]
    if not ent_features:
        return draw(st.just("api_access"))  # Default enterprise feature
    return draw(st.sampled_from(ent_features))


def create_license_record(tier: LicenseTier, status: LicenseStatus = LicenseStatus.ACTIVE) -> LicenseRecord:
    """Create a test license record."""
    return LicenseRecord(
        PK="INSTANCE#test-instance",
        SK="LICENSE#LIC-TEST001",
        license_id="LIC-TEST001",
        license_key_hash="test_hash",
        tier=tier,
        holder_id="TEST-001",
        holder_name="Test Corp",
        issued_at=datetime.now(timezone.utc),
        activated_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        status=status,
        enabled_features=TIER_FEATURES.get(tier, []),
        instance_id="test-instance",
    )


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def feature_service():
    """Create a feature service for tests."""
    return FeatureService()


# ==========================================
# Property Tests
# ==========================================

class TestFeatureTierGatingProperties:
    """
    Property-based tests for feature tier gating.
    
    Feature: license-enablement, Property 11: Feature Tier Gating
    Validates: Requirements 6.1, 6.2, 6.4, 6.5
    """
    
    @given(feature_id=valid_feature_id(), current_tier=valid_tier())
    @settings(max_examples=100)
    def test_tier_hierarchy_access(self, feature_id, current_tier, feature_service):
        """
        Property: If feature's required_tier <= current_tier, access is granted.
        If feature's required_tier > current_tier, access is denied.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.1, 6.2
        """
        record = create_license_record(current_tier)
        result = feature_service.check_feature_access(feature_id, record)
        
        required_tier = FEATURE_TIER_MAPPING.get(feature_id)
        
        # Check tier hierarchy
        tier_levels = {
            LicenseTier.BASIC: 1,
            LicenseTier.PROFESSIONAL: 2,
            LicenseTier.ENTERPRISE: 3,
        }
        
        current_level = tier_levels[current_tier]
        required_level = tier_levels[required_tier]
        
        expected_allowed = current_level >= required_level
        assert result.is_allowed == expected_allowed
    
    @given(feature_id=valid_feature_id())
    @settings(max_examples=100)
    def test_enterprise_has_all_access(self, feature_id, feature_service):
        """
        Property: Enterprise tier SHALL have access to all features.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.5
        """
        record = create_license_record(LicenseTier.ENTERPRISE)
        result = feature_service.check_feature_access(feature_id, record)
        
        assert result.is_allowed is True
        assert result.current_tier == LicenseTier.ENTERPRISE
    
    @given(feature_id=basic_feature())
    @settings(max_examples=50)
    def test_basic_features_accessible_to_all(self, feature_id, feature_service):
        """
        Property: Basic tier features are accessible to all tiers.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.2
        """
        for tier in LicenseTier:
            record = create_license_record(tier)
            result = feature_service.check_feature_access(feature_id, record)
            assert result.is_allowed is True
    
    @given(feature_id=enterprise_feature())
    @settings(max_examples=50)
    def test_enterprise_features_restricted(self, feature_id, feature_service):
        """
        Property: Enterprise features are only accessible to enterprise tier.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.1, 6.2
        """
        # Basic should not have access
        basic_record = create_license_record(LicenseTier.BASIC)
        basic_result = feature_service.check_feature_access(feature_id, basic_record)
        assert basic_result.is_allowed is False
        
        # Professional should not have access
        pro_record = create_license_record(LicenseTier.PROFESSIONAL)
        pro_result = feature_service.check_feature_access(feature_id, pro_record)
        assert pro_result.is_allowed is False
        
        # Enterprise should have access
        ent_record = create_license_record(LicenseTier.ENTERPRISE)
        ent_result = feature_service.check_feature_access(feature_id, ent_record)
        assert ent_result.is_allowed is True
    
    @given(feature_id=valid_feature_id(), tier=valid_tier())
    @settings(max_examples=100)
    def test_denied_access_includes_upgrade_message(self, feature_id, tier, feature_service):
        """
        Property: When access is denied, response includes upgrade message.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.4
        """
        record = create_license_record(tier)
        result = feature_service.check_feature_access(feature_id, record)
        
        if not result.is_allowed:
            assert result.upgrade_message is not None
            assert len(result.upgrade_message) > 0
    
    @given(feature_id=valid_feature_id())
    @settings(max_examples=50)
    def test_no_license_denies_access(self, feature_id, feature_service):
        """
        Property: Without an active license, all features are denied.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.1
        """
        result = feature_service.check_feature_access(feature_id, None)
        
        assert result.is_allowed is False
        assert result.current_tier is None
        assert result.upgrade_message is not None
    
    @given(feature_id=valid_feature_id(), tier=valid_tier())
    @settings(max_examples=50)
    def test_inactive_license_denies_access(self, feature_id, tier, feature_service):
        """
        Property: Inactive licenses deny feature access.
        
        Feature: license-enablement, Property 11: Feature Tier Gating
        Validates: Requirements 6.1
        """
        for status in [LicenseStatus.EXPIRED, LicenseStatus.DEACTIVATED, LicenseStatus.REVOKED]:
            record = create_license_record(tier, status)
            result = feature_service.check_feature_access(feature_id, record)
            
            assert result.is_allowed is False


class TestFeatureServiceHelpers:
    """Unit tests for feature service helper methods."""
    
    def test_get_features_for_basic_tier(self, feature_service):
        """Basic tier should get basic features only."""
        features = feature_service.get_features_for_tier(LicenseTier.BASIC)
        
        for feature in features:
            required = FEATURE_TIER_MAPPING.get(feature)
            assert required == LicenseTier.BASIC
    
    def test_get_features_for_enterprise_tier(self, feature_service):
        """Enterprise tier should get all features."""
        features = feature_service.get_features_for_tier(LicenseTier.ENTERPRISE)
        
        # Should include all features
        assert set(features) == set(FEATURE_TIER_MAPPING.keys())
    
    def test_get_all_features(self, feature_service):
        """Should return all features with their tiers."""
        all_features = feature_service.get_all_features()
        
        assert len(all_features) == len(FEATURE_TIER_MAPPING)
        
        for feature_info in all_features:
            assert "feature_id" in feature_info
            assert "required_tier" in feature_info
    
    def test_unknown_feature_denied(self, feature_service):
        """Unknown features should be denied."""
        record = create_license_record(LicenseTier.ENTERPRISE)
        result = feature_service.check_feature_access("unknown_feature_xyz", record)
        
        assert result.is_allowed is False
        assert "Unknown feature" in result.upgrade_message
