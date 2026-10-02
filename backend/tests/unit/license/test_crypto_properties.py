"""
Property-Based Tests for License Cryptographic Validation

Feature: license-enablement, Property 1: License Key Cryptographic Validation
Validates: Requirements 1.1, 9.1, 9.3, 9.4

Tests that the License_Service correctly identifies whether cryptographic signatures
are valid by verifying against embedded data components.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.utils.key_parser import LicenseKeyParser
from license.utils.crypto import LicenseCrypto, LicenseCryptoError
from license.utils.key_generator import LicenseKeyGenerator, get_test_generator
from license.utils.keys import set_public_key, clear_public_key
from license.models.enums import LicenseTier


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture(scope="module")
def key_generator():
    """Create a key generator and set up public key for verification."""
    generator = LicenseKeyGenerator()
    set_public_key(generator.get_public_key_pem())
    yield generator
    clear_public_key()


@pytest.fixture
def crypto(key_generator):
    """Create crypto instance with matching public key."""
    return LicenseCrypto(key_generator.get_public_key_pem())


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
# Property Tests
# ==========================================

class TestCryptoValidationProperties:
    """
    Property-based tests for cryptographic validation.
    
    Feature: license-enablement, Property 1: License Key Cryptographic Validation
    Validates: Requirements 1.1, 9.1, 9.3, 9.4
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        days_valid=valid_expiration_days()
    )
    @settings(max_examples=100)
    def test_valid_signature_verifies(self, tier, holder_id, days_valid, key_generator, crypto):
        """
        Property: For any license key generated with valid signature,
        verification should succeed.
        
        Feature: license-enablement, Property 1: License Key Cryptographic Validation
        Validates: Requirements 1.1, 9.1, 9.3
        """
        # Generate a valid key
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # Parse the key
        parsed = LicenseKeyParser.parse(license_key)
        
        # Verify signature
        is_valid = crypto.verify_signature(parsed)
        
        assert is_valid is True
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        days_valid=valid_expiration_days()
    )
    @settings(max_examples=100)
    def test_tampered_data_fails_verification(self, tier, holder_id, days_valid, key_generator, crypto):
        """
        Property: For any license key with tampered data (but original signature),
        verification should fail.
        
        Feature: license-enablement, Property 1: License Key Cryptographic Validation
        Validates: Requirements 9.3, 9.4
        """
        # Generate a valid key
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # Parse the key
        parsed = LicenseKeyParser.parse(license_key)
        
        # Tamper with the holder_id
        tampered_holder = holder_id + "X"
        
        # Create tampered parsed key (keeping original signature)
        from license.models.license_model import ParsedLicenseKey
        tampered = ParsedLicenseKey(
            version=parsed.version,
            tier=parsed.tier,
            expiration=parsed.expiration,
            holder_id=tampered_holder,
            features=parsed.features,
            signature=parsed.signature,
            raw_key=parsed.raw_key,
        )
        
        # Verification should fail
        with pytest.raises(LicenseCryptoError):
            crypto.verify_signature(tampered)
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=100)
    def test_is_signature_valid_returns_tuple(self, tier, holder_id, key_generator, crypto):
        """
        Property: is_signature_valid should return (True, None) for valid keys
        and (False, error_message) for invalid keys.
        
        Feature: license-enablement, Property 1: License Key Cryptographic Validation
        Validates: Requirements 9.1
        """
        # Generate a valid key
        license_key = key_generator.generate_key(tier, holder_id)
        parsed = LicenseKeyParser.parse(license_key)
        
        # Check valid key
        is_valid, error = crypto.is_signature_valid(parsed)
        assert is_valid is True
        assert error is None
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
    )
    @settings(max_examples=50)
    def test_different_keys_have_different_signatures(self, tier, holder_id, key_generator):
        """
        Property: Different license keys should have different signatures.
        
        Feature: license-enablement, Property 1: License Key Cryptographic Validation
        Validates: Requirements 9.1
        """
        # Generate two keys with different holder IDs
        key1 = key_generator.generate_key(tier, holder_id)
        key2 = key_generator.generate_key(tier, holder_id + "2")
        
        parsed1 = LicenseKeyParser.parse(key1)
        parsed2 = LicenseKeyParser.parse(key2)
        
        # Signatures should be different
        assert parsed1.signature != parsed2.signature


# ==========================================
# Unit Tests for Edge Cases
# ==========================================

class TestCryptoEdgeCases:
    """Unit tests for cryptographic edge cases."""
    
    def test_wrong_public_key_fails_verification(self, key_generator):
        """Verification with wrong public key should fail."""
        # Generate key with one key pair
        license_key = key_generator.generate_key(LicenseTier.BASIC, "TEST-001")
        parsed = LicenseKeyParser.parse(license_key)
        
        # Create crypto with different key pair
        other_generator = LicenseKeyGenerator()
        other_crypto = LicenseCrypto(other_generator.get_public_key_pem())
        
        # Verification should fail
        is_valid, error = other_crypto.is_signature_valid(parsed)
        assert is_valid is False
        assert error is not None
    
    def test_all_tiers_generate_valid_signatures(self, key_generator, crypto):
        """All tier levels should generate valid signatures."""
        for tier in LicenseTier:
            license_key = key_generator.generate_key(tier, f"TEST-{tier.value}")
            parsed = LicenseKeyParser.parse(license_key)
            
            is_valid = crypto.verify_signature(parsed)
            assert is_valid is True, f"Failed for tier {tier}"
    
    def test_expired_key_still_has_valid_signature(self, key_generator, crypto):
        """Expired keys should still have valid signatures (expiration is business logic)."""
        license_key = key_generator.generate_expired_key(LicenseTier.BASIC, "TEST-001", days_expired=30)
        parsed = LicenseKeyParser.parse(license_key)
        
        # Signature should still be valid
        is_valid = crypto.verify_signature(parsed)
        assert is_valid is True
