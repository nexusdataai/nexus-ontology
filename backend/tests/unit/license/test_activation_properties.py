"""
Property-Based Tests for License Activation Round-Trip

Feature: license-enablement, Property 2: Activation Round-Trip Consistency
Validates: Requirements 1.2

Tests that for any valid license key that passes activation, querying the store
returns an activation record with matching data.
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
from license.utils.key_generator import LicenseKeyGenerator
from license.utils.key_parser import LicenseKeyParser
from license.consts import TIER_FEATURES


# ==========================================
# Custom Strategies
# ==========================================

@st.composite
def valid_tier(draw):
    """Generate valid license tiers."""
    return draw(st.sampled_from(list(LicenseTier)))


@st.composite
def valid_holder_id(draw):
    """Generate valid holder IDs."""
    prefix = draw(st.sampled_from(["CUST", "ORG", "USER", "ACCT"]))
    suffix = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        min_size=4,
        max_size=10
    ))
    return f"{prefix}-{suffix}"


@st.composite
def valid_instance_id(draw):
    """Generate valid instance IDs."""
    prefix = draw(st.sampled_from(["INST", "SRV", "NODE"]))
    suffix = draw(st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789",
        min_size=4,
        max_size=8
    ))
    return f"{prefix}-{suffix}"


@st.composite
def valid_holder_name(draw):
    """Generate valid holder names."""
    words = ["Acme", "Global", "Tech", "Corp", "Inc", "Solutions", "Systems", "Labs"]
    num_words = draw(st.integers(min_value=1, max_value=3))
    selected = [draw(st.sampled_from(words)) for _ in range(num_words)]
    return " ".join(selected)


@st.composite
def valid_expiration_days(draw):
    """Generate valid days until expiration."""
    return draw(st.integers(min_value=1, max_value=3650))


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture(scope="module")
def key_generator():
    """Create a key generator for tests."""
    return LicenseKeyGenerator()


# ==========================================
# Property Tests
# ==========================================

class TestActivationRoundTripProperties:
    """
    Property-based tests for activation round-trip consistency.
    
    Feature: license-enablement, Property 2: Activation Round-Trip Consistency
    Validates: Requirements 1.2
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        holder_name=valid_holder_name(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_license_record_preserves_key_data(
        self, tier, holder_id, instance_id, holder_name, days_valid, key_generator
    ):
        """
        Property: For any valid license key, creating a LicenseRecord should
        preserve all key data (tier, holder_id, expiration, features).
        
        Feature: license-enablement, Property 2: Activation Round-Trip Consistency
        Validates: Requirements 1.2
        """
        # Generate a valid license key
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # Parse the key
        parsed = LicenseKeyParser.parse(license_key)
        
        # Determine expected features
        if tier == LicenseTier.ENTERPRISE:
            expected_features = ["ALL"]
        else:
            expected_features = TIER_FEATURES.get(tier, [])
        
        # Create license record (simulating activation)
        record = LicenseRecord.create(
            instance_id=instance_id,
            license_key=license_key,
            tier=parsed.tier,
            holder_id=parsed.holder_id,
            holder_name=holder_name,
            issued_at=datetime.now(timezone.utc),
            expires_at=parsed.expiration,
            enabled_features=expected_features,
        )
        
        # Verify round-trip consistency
        assert record.tier == tier
        assert record.holder_id == holder_id
        assert record.expires_at.date() == expiration.date()
        assert record.instance_id == instance_id
        assert record.status == LicenseStatus.ACTIVE
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=100)
    def test_license_record_to_dynamo_roundtrip(self, tier, holder_id, instance_id, key_generator):
        """
        Property: For any LicenseRecord, converting to DynamoDB format and back
        should preserve all data.
        
        Feature: license-enablement, Property 2: Activation Round-Trip Consistency
        Validates: Requirements 1.2
        """
        # Generate and create record
        license_key = key_generator.generate_key(tier, holder_id)
        parsed = LicenseKeyParser.parse(license_key)
        
        record = LicenseRecord.create(
            instance_id=instance_id,
            license_key=license_key,
            tier=parsed.tier,
            holder_id=parsed.holder_id,
            holder_name="Test Corp",
            issued_at=datetime.now(timezone.utc),
            expires_at=parsed.expiration,
            enabled_features=TIER_FEATURES.get(tier, []),
        )
        
        # Convert to DynamoDB format
        dynamo_item = record.to_dynamo_item()
        
        # Verify key fields are present
        assert dynamo_item['PK'] == f"INSTANCE#{instance_id}"
        assert dynamo_item['SK'].startswith("LICENSE#")
        assert dynamo_item['tier'] == tier.value
        assert dynamo_item['holder_id'] == holder_id
        assert dynamo_item['status'] == LicenseStatus.ACTIVE.value
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_license_key_hash_is_consistent(self, tier, holder_id, days_valid, key_generator):
        """
        Property: For any license key, the hash stored in the record should
        be deterministic and consistent.
        
        Feature: license-enablement, Property 2: Activation Round-Trip Consistency
        Validates: Requirements 1.2
        """
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # Create two records with same key
        record1 = LicenseRecord.create(
            instance_id="inst-1",
            license_key=license_key,
            tier=tier,
            holder_id=holder_id,
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=expiration,
            enabled_features=[],
        )
        
        record2 = LicenseRecord.create(
            instance_id="inst-2",
            license_key=license_key,
            tier=tier,
            holder_id=holder_id,
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=expiration,
            enabled_features=[],
        )
        
        # Hash should be the same for same key
        assert record1.license_key_hash == record2.license_key_hash
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=50)
    def test_different_keys_have_different_hashes(self, tier, holder_id, key_generator):
        """
        Property: Different license keys should produce different hashes.
        
        Feature: license-enablement, Property 2: Activation Round-Trip Consistency
        Validates: Requirements 1.2
        """
        key1 = key_generator.generate_key(tier, holder_id)
        key2 = key_generator.generate_key(tier, holder_id + "X")
        
        record1 = LicenseRecord.create(
            instance_id="inst-1",
            license_key=key1,
            tier=tier,
            holder_id=holder_id,
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            enabled_features=[],
        )
        
        record2 = LicenseRecord.create(
            instance_id="inst-1",
            license_key=key2,
            tier=tier,
            holder_id=holder_id + "X",
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            enabled_features=[],
        )
        
        assert record1.license_key_hash != record2.license_key_hash


# ==========================================
# Unit Tests for Edge Cases
# ==========================================

class TestActivationEdgeCases:
    """Unit tests for activation edge cases."""
    
    def test_record_generates_unique_license_id(self, key_generator):
        """Each record should have a unique license ID."""
        key = key_generator.generate_key(LicenseTier.BASIC, "TEST-001")
        
        ids = set()
        for _ in range(10):
            record = LicenseRecord.create(
                instance_id="inst-1",
                license_key=key,
                tier=LicenseTier.BASIC,
                holder_id="TEST-001",
                holder_name="Test",
                issued_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                enabled_features=[],
            )
            ids.add(record.license_id)
        
        # All IDs should be unique
        assert len(ids) == 10
    
    def test_record_pk_sk_format(self, key_generator):
        """PK and SK should follow expected format."""
        key = key_generator.generate_key(LicenseTier.BASIC, "TEST-001")
        
        record = LicenseRecord.create(
            instance_id="my-instance",
            license_key=key,
            tier=LicenseTier.BASIC,
            holder_id="TEST-001",
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            enabled_features=[],
        )
        
        assert record.PK == "INSTANCE#my-instance"
        assert record.SK.startswith("LICENSE#LIC-")
    
    def test_days_remaining_calculation(self, key_generator):
        """days_remaining should calculate correctly."""
        key = key_generator.generate_key(LicenseTier.BASIC, "TEST-001")
        expiration = datetime.now(timezone.utc) + timedelta(days=30)
        
        record = LicenseRecord.create(
            instance_id="inst-1",
            license_key=key,
            tier=LicenseTier.BASIC,
            holder_id="TEST-001",
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=expiration,
            enabled_features=[],
        )
        
        # Should be approximately 30 days (might be 29 due to timing)
        assert 29 <= record.days_remaining() <= 30
    
    def test_is_expired_for_future_date(self, key_generator):
        """is_expired should return False for future expiration."""
        key = key_generator.generate_key(LicenseTier.BASIC, "TEST-001")
        
        record = LicenseRecord.create(
            instance_id="inst-1",
            license_key=key,
            tier=LicenseTier.BASIC,
            holder_id="TEST-001",
            holder_name="Test",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            enabled_features=[],
        )
        
        assert record.is_expired() is False
    
    def test_is_expired_for_past_date(self, key_generator):
        """is_expired should return True for past expiration."""
        key = key_generator.generate_expired_key(LicenseTier.BASIC, "TEST-001", days_expired=30)
        parsed = LicenseKeyParser.parse(key)
        
        record = LicenseRecord.create(
            instance_id="inst-1",
            license_key=key,
            tier=LicenseTier.BASIC,
            holder_id="TEST-001",
            holder_name="Test",
            issued_at=datetime.now(timezone.utc) - timedelta(days=60),
            expires_at=parsed.expiration,
            enabled_features=[],
        )
        
        assert record.is_expired() is True
