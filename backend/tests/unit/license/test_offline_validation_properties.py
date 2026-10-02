"""
Property-Based Tests for Offline Validation

Feature: license-enablement, Property 15: Offline Validation Capability
Validates: Requirements 10.1, 10.2, 10.4

Tests that license validation works without network access.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.enums import LicenseTier
from license.utils.key_generator import LicenseKeyGenerator
from license.utils.key_parser import LicenseKeyParser
from license.utils.crypto import LicenseCrypto
from license.utils.keys import set_public_key, clear_public_key


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
def valid_expiration_days(draw):
    """Generate valid days until expiration."""
    return draw(st.integers(min_value=1, max_value=3650))


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture(scope="module")
def key_generator():
    """Create a key generator and set up public key for tests."""
    generator = LicenseKeyGenerator()
    set_public_key(generator.get_public_key_pem())
    yield generator
    clear_public_key()


@pytest.fixture
def crypto(key_generator):
    """Create a crypto instance with the test public key."""
    return LicenseCrypto(key_generator.get_public_key_pem())


# ==========================================
# Property Tests
# ==========================================

class TestOfflineValidationProperties:
    """
    Property-based tests for offline validation capability.
    
    Feature: license-enablement, Property 15: Offline Validation Capability
    Validates: Requirements 10.1, 10.2, 10.4
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_offline_validation_with_embedded_key(
        self, tier, holder_id, days_valid, key_generator, crypto
    ):
        """
        Property: For any activated license, validation SHALL succeed without
        network access by using locally stored validation data and the
        embedded public key.
        
        Feature: license-enablement, Property 15: Offline Validation Capability
        Validates: Requirements 10.1, 10.4
        """
        # Generate a license key
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # Parse the key (no network required)
        parsed = LicenseKeyParser.parse(license_key)
        
        # Verify signature using embedded public key (no network required)
        is_valid = crypto.verify_signature(parsed)
        
        assert is_valid is True
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=100)
    def test_validation_uses_local_data_only(
        self, tier, holder_id, key_generator, crypto
    ):
        """
        Property: License validation SHALL use only locally stored data
        and embedded public key, without external network calls.
        
        Feature: license-enablement, Property 15: Offline Validation Capability
        Validates: Requirements 10.1, 10.2
        """
        # Generate key
        license_key = key_generator.generate_key(tier, holder_id)
        
        # Parse extracts all data from the key itself
        parsed = LicenseKeyParser.parse(license_key)
        
        # All validation data is in the parsed key
        assert parsed.version is not None
        assert parsed.tier == tier
        assert parsed.holder_id == holder_id
        assert parsed.expiration is not None
        assert parsed.signature is not None
        
        # Signature verification uses embedded public key
        is_valid = crypto.verify_signature(parsed)
        assert is_valid is True
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=50)
    def test_tampered_key_detected_offline(
        self, tier, holder_id, key_generator, crypto
    ):
        """
        Property: Tampered license keys SHALL be detected using offline
        signature verification.
        
        Feature: license-enablement, Property 15: Offline Validation Capability
        Validates: Requirements 10.1
        """
        # Generate valid key
        license_key = key_generator.generate_key(tier, holder_id)
        
        # Tamper with the key (change holder ID)
        parts = license_key.split('.')
        parts[3] = "TAMPERED-ID"
        tampered_key = '.'.join(parts)
        
        # Parse tampered key
        parsed = LicenseKeyParser.parse(tampered_key)
        
        # Signature verification should fail
        is_valid, error = crypto.is_signature_valid(parsed)
        assert is_valid is False
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=50)
    def test_expired_key_detected_offline(
        self, tier, holder_id, key_generator
    ):
        """
        Property: Expired licenses SHALL be detected using locally stored
        expiration data.
        
        Feature: license-enablement, Property 15: Offline Validation Capability
        Validates: Requirements 10.4
        """
        # Generate expired key
        license_key = key_generator.generate_expired_key(tier, holder_id, days_expired=30)
        
        # Parse key
        parsed = LicenseKeyParser.parse(license_key)
        
        # Expiration is in the past
        now = datetime.now(timezone.utc)
        assert parsed.expiration < now


class TestOfflineValidationEdgeCases:
    """Unit tests for offline validation edge cases."""
    
    def test_public_key_embedded(self, key_generator):
        """Public key should be available without network."""
        from license.utils.keys import get_public_key_pem
        
        # Set the test public key
        set_public_key(key_generator.get_public_key_pem())
        
        # Should be able to get public key
        pem = get_public_key_pem()
        assert pem is not None
        assert "BEGIN PUBLIC KEY" in pem
    
    def test_validation_without_network_simulation(self, key_generator, crypto):
        """Simulate offline validation by not using any network calls."""
        # Generate key
        license_key = key_generator.generate_key(
            LicenseTier.ENTERPRISE,
            "OFFLINE-TEST",
        )
        
        # All operations are local:
        # 1. Parse key (string manipulation)
        parsed = LicenseKeyParser.parse(license_key)
        
        # 2. Verify signature (cryptographic operation with embedded key)
        is_valid = crypto.verify_signature(parsed)
        
        # 3. Check expiration (datetime comparison)
        is_expired = parsed.expiration < datetime.now(timezone.utc)
        
        assert is_valid is True
        assert is_expired is False
    
    def test_key_rotation_support(self, key_generator):
        """Should support key rotation via configuration."""
        from license.utils.keys import set_public_key, get_public_key_pem
        
        # Generate new key pair
        new_generator = LicenseKeyGenerator()
        new_public_key = new_generator.get_public_key_pem()
        
        # Set new public key
        set_public_key(new_public_key)
        
        # Verify it's updated
        current_key = get_public_key_pem()
        assert current_key == new_public_key
        
        # Generate and validate with new key
        license_key = new_generator.generate_key(LicenseTier.BASIC, "ROTATION-TEST")
        crypto = LicenseCrypto(new_public_key)
        parsed = LicenseKeyParser.parse(license_key)
        
        assert crypto.verify_signature(parsed) is True
