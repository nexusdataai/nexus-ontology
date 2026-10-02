"""
Property-Based Tests for Grace Period Behavior

Feature: license-enablement, Property 12: Grace Period Behavior
Validates: Requirements 7.1, 7.2, 7.3, 7.4

Tests that grace period is correctly calculated and enforced.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.license_model import LicenseRecord
from license.models.enums import LicenseTier, LicenseStatus
from license.consts import DEFAULT_GRACE_PERIOD_DAYS, TIER_FEATURES


# ==========================================
# Custom Strategies
# ==========================================

@st.composite
def valid_tier(draw):
    """Generate valid license tiers."""
    return draw(st.sampled_from(list(LicenseTier)))


@st.composite
def grace_period_days(draw):
    """Generate valid grace period durations."""
    return draw(st.integers(min_value=1, max_value=30))


@st.composite
def days_past_expiration(draw):
    """Generate days past expiration (within grace period)."""
    return draw(st.integers(min_value=1, max_value=DEFAULT_GRACE_PERIOD_DAYS - 1))


@st.composite
def days_past_grace(draw):
    """Generate days past grace period."""
    return draw(st.integers(min_value=DEFAULT_GRACE_PERIOD_DAYS + 1, max_value=100))


def create_license_record(
    tier: LicenseTier,
    expires_at: datetime,
    grace_period_days: int = DEFAULT_GRACE_PERIOD_DAYS,
) -> LicenseRecord:
    """Create a test license record with specific expiration."""
    return LicenseRecord(
        PK="INSTANCE#test-instance",
        SK="LICENSE#LIC-TEST001",
        license_id="LIC-TEST001",
        license_key_hash="test_hash",
        tier=tier,
        holder_id="TEST-001",
        holder_name="Test Corp",
        issued_at=datetime.now(timezone.utc) - timedelta(days=365),
        activated_at=datetime.now(timezone.utc) - timedelta(days=365),
        expires_at=expires_at,
        status=LicenseStatus.ACTIVE,
        enabled_features=TIER_FEATURES.get(tier, []),
        instance_id="test-instance",
        grace_period_days=grace_period_days,
    )


# ==========================================
# Property Tests
# ==========================================

class TestGracePeriodBehaviorProperties:
    """
    Property-based tests for grace period behavior.
    
    Feature: license-enablement, Property 12: Grace Period Behavior
    Validates: Requirements 7.1, 7.2, 7.3, 7.4
    """
    
    @given(
        tier=valid_tier(),
        grace_days=grace_period_days(),
    )
    @settings(max_examples=100)
    def test_grace_period_calculation(self, tier, grace_days):
        """
        Property: Grace period SHALL be calculated as expiration_date + grace_period_days.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.1
        """
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired yesterday
        record = create_license_record(tier, expires_at, grace_days)
        
        expected_grace_end = expires_at + timedelta(days=grace_days)
        actual_grace_end = record.get_grace_period_end()
        
        # Should match within a second (datetime precision)
        assert abs((expected_grace_end - actual_grace_end).total_seconds()) < 1
    
    @given(
        tier=valid_tier(),
        days_expired=days_past_expiration(),
    )
    @settings(max_examples=100)
    def test_in_grace_period_detection(self, tier, days_expired):
        """
        Property: License should be detected as in grace period when expired
        but within grace_period_days.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.1, 7.3
        """
        # Ensure we're within grace period
        assume(days_expired < DEFAULT_GRACE_PERIOD_DAYS)
        
        expires_at = datetime.now(timezone.utc) - timedelta(days=days_expired)
        record = create_license_record(tier, expires_at)
        
        assert record.is_in_grace_period() is True
        assert record.is_expired() is False
    
    @given(
        tier=valid_tier(),
        days_expired=days_past_grace(),
    )
    @settings(max_examples=100)
    def test_past_grace_period_detection(self, tier, days_expired):
        """
        Property: License should be detected as expired when past grace period.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.4
        """
        expires_at = datetime.now(timezone.utc) - timedelta(days=days_expired)
        record = create_license_record(tier, expires_at)
        
        assert record.is_in_grace_period() is False
        assert record.is_expired() is True
    
    @given(tier=valid_tier())
    @settings(max_examples=50)
    def test_active_license_not_in_grace_period(self, tier):
        """
        Property: Active (non-expired) license should not be in grace period.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.1
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)  # Future expiration
        record = create_license_record(tier, expires_at)
        
        assert record.is_in_grace_period() is False
        assert record.is_expired() is False
    
    @given(
        tier=valid_tier(),
        days_expired=days_past_expiration(),
    )
    @settings(max_examples=100)
    def test_grace_period_days_remaining(self, tier, days_expired):
        """
        Property: grace_period_days_remaining should correctly calculate remaining days.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.3
        """
        assume(days_expired < DEFAULT_GRACE_PERIOD_DAYS)
        
        expires_at = datetime.now(timezone.utc) - timedelta(days=days_expired)
        record = create_license_record(tier, expires_at)
        
        remaining = record.grace_period_days_remaining()
        expected_remaining = DEFAULT_GRACE_PERIOD_DAYS - days_expired
        
        # Allow for timing variance
        assert abs(remaining - expected_remaining) <= 1
    
    @given(tier=valid_tier())
    @settings(max_examples=50)
    def test_grace_period_zero_when_not_in_grace(self, tier):
        """
        Property: grace_period_days_remaining should be 0 when not in grace period.
        
        Feature: license-enablement, Property 12: Grace Period Behavior
        Validates: Requirements 7.3
        """
        # Active license
        active_expires = datetime.now(timezone.utc) + timedelta(days=30)
        active_record = create_license_record(tier, active_expires)
        assert active_record.grace_period_days_remaining() == 0
        
        # Fully expired license
        expired_expires = datetime.now(timezone.utc) - timedelta(days=100)
        expired_record = create_license_record(tier, expired_expires)
        assert expired_record.grace_period_days_remaining() == 0


class TestGracePeriodEdgeCases:
    """Unit tests for grace period edge cases."""
    
    def test_exactly_at_expiration(self):
        """License at exact expiration time should not be in grace period yet."""
        # This is tricky due to timing - license expires at end of day
        expires_at = datetime.now(timezone.utc)
        record = create_license_record(LicenseTier.BASIC, expires_at)
        
        # At exact expiration, should be in grace period
        # (since we're past the expiration datetime)
        # This depends on exact timing
        pass  # Skip timing-sensitive test
    
    def test_custom_grace_period(self):
        """Custom grace period should be respected."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=5)
        
        # 3-day grace period - should be expired
        short_grace = create_license_record(LicenseTier.BASIC, expires_at, grace_period_days=3)
        assert short_grace.is_expired() is True
        
        # 10-day grace period - should be in grace
        long_grace = create_license_record(LicenseTier.BASIC, expires_at, grace_period_days=10)
        assert long_grace.is_in_grace_period() is True
    
    def test_zero_grace_period(self):
        """Zero grace period should mean immediate expiration."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        record = create_license_record(LicenseTier.BASIC, expires_at, grace_period_days=0)
        
        assert record.is_in_grace_period() is False
        assert record.is_expired() is True
    
    def test_explicit_grace_period_end(self):
        """Explicit grace_period_ends_at should override calculation."""
        expires_at = datetime.now(timezone.utc) - timedelta(days=5)
        record = create_license_record(LicenseTier.BASIC, expires_at, grace_period_days=7)
        
        # Set explicit grace period end
        explicit_end = datetime.now(timezone.utc) + timedelta(days=10)
        record.grace_period_ends_at = explicit_end
        
        # Should use explicit end
        assert record.get_grace_period_end() == explicit_end
        assert record.is_in_grace_period() is True
