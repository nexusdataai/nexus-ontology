"""
Property-Based Tests for License Key Parser

Feature: license-enablement, Property 14: License Key Format Parsing
Validates: Requirements 9.2, 9.5

Tests the round-trip property: for any valid license key, parsing then formatting
should produce an equivalent key.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
import base64
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.utils.key_parser import LicenseKeyParser, LicenseKeyParseError
from license.models.enums import LicenseTier, TIER_TO_ABBREVIATION
from license.models.license_model import ParsedLicenseKey


# ==========================================
# Custom Strategies for License Key Components
# ==========================================

@st.composite
def valid_version(draw):
    """Generate valid version strings."""
    return draw(st.sampled_from(["v1", "v2"]))


@st.composite
def valid_tier(draw):
    """Generate valid license tiers."""
    return draw(st.sampled_from(list(LicenseTier)))


@st.composite
def valid_expiration(draw):
    """Generate valid expiration dates (future dates)."""
    # Generate dates between now and 10 years from now
    days_ahead = draw(st.integers(min_value=1, max_value=3650))
    base_date = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    return datetime(base_date.year, base_date.month, base_date.day, 23, 59, 59, tzinfo=timezone.utc)


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
def valid_features(draw):
    """Generate valid feature strings."""
    return draw(st.sampled_from([
        "ALL",
        "JOURNEYS",
        "ANALYTICS",
        "JOURNEYS,ANALYTICS",
        "JOURNEYS,ANALYTICS,EXPORT",
    ]))


@st.composite
def valid_signature(draw):
    """Generate valid base64 signatures (at least 32 bytes when decoded)."""
    # Generate random bytes for signature (64 bytes = 512 bits, typical for ECDSA)
    sig_bytes = draw(st.binary(min_size=64, max_size=128))
    return base64.urlsafe_b64encode(sig_bytes).decode('ascii').rstrip('=')


@st.composite
def valid_license_key(draw):
    """Generate a complete valid license key string."""
    version = draw(valid_version())
    tier = draw(valid_tier())
    expiration = draw(valid_expiration())
    holder_id = draw(valid_holder_id())
    features = draw(valid_features())
    signature = draw(valid_signature())
    
    tier_abbrev = TIER_TO_ABBREVIATION[tier]
    expiration_str = expiration.strftime("%Y%m%d")
    
    return f"{version}.{tier_abbrev}.{expiration_str}.{holder_id}.{features}.{signature}"


@st.composite
def valid_parsed_license_key(draw):
    """Generate a valid ParsedLicenseKey object."""
    version = draw(valid_version())
    tier = draw(valid_tier())
    expiration = draw(valid_expiration())
    holder_id = draw(valid_holder_id())
    features = draw(valid_features())
    signature = draw(valid_signature())
    
    tier_abbrev = TIER_TO_ABBREVIATION[tier]
    expiration_str = expiration.strftime("%Y%m%d")
    raw_key = f"{version}.{tier_abbrev}.{expiration_str}.{holder_id}.{features}.{signature}"
    
    return ParsedLicenseKey(
        version=version,
        tier=tier,
        expiration=expiration,
        holder_id=holder_id,
        features=features.upper(),
        signature=signature,
        raw_key=raw_key,
    )


# ==========================================
# Property Tests
# ==========================================

class TestLicenseKeyParserProperties:
    """
    Property-based tests for license key parsing.
    
    Feature: license-enablement, Property 14: License Key Format Parsing
    Validates: Requirements 9.2, 9.5
    """
    
    @given(license_key=valid_license_key())
    @settings(max_examples=100)
    def test_parse_valid_key_succeeds(self, license_key: str):
        """
        Property: For any valid license key string, parsing should succeed.
        
        Feature: license-enablement, Property 14: License Key Format Parsing
        Validates: Requirements 9.2
        """
        parsed = LicenseKeyParser.parse(license_key)
        
        assert parsed is not None
        assert parsed.version in ["v1", "v2"]
        assert parsed.tier in LicenseTier
        assert parsed.expiration is not None
        assert parsed.holder_id is not None
        assert parsed.features is not None
        assert parsed.signature is not None
    
    @given(parsed=valid_parsed_license_key())
    @settings(max_examples=100)
    def test_format_then_parse_roundtrip(self, parsed: ParsedLicenseKey):
        """
        Property: For any valid ParsedLicenseKey, formatting then parsing
        should produce an equivalent object.
        
        Feature: license-enablement, Property 14: License Key Format Parsing
        Validates: Requirements 9.2, 9.5
        """
        # Format the parsed key back to string
        formatted = LicenseKeyParser.format_key(parsed)
        
        # Parse the formatted string
        reparsed = LicenseKeyParser.parse(formatted)
        
        # Verify equivalence
        assert reparsed.version == parsed.version
        assert reparsed.tier == parsed.tier
        assert reparsed.expiration.date() == parsed.expiration.date()
        assert reparsed.holder_id == parsed.holder_id
        assert reparsed.features == parsed.features
        assert reparsed.signature == parsed.signature
    
    @given(license_key=valid_license_key())
    @settings(max_examples=100)
    def test_parse_then_format_roundtrip(self, license_key: str):
        """
        Property: For any valid license key string, parsing then formatting
        should produce an equivalent key string.
        
        Feature: license-enablement, Property 14: License Key Format Parsing
        Validates: Requirements 9.2, 9.5
        """
        # Parse the key
        parsed = LicenseKeyParser.parse(license_key)
        
        # Format back to string
        reformatted = LicenseKeyParser.format_key(parsed)
        
        # Parse again
        reparsed = LicenseKeyParser.parse(reformatted)
        
        # The reparsed should match the original parsed
        assert reparsed.version == parsed.version
        assert reparsed.tier == parsed.tier
        assert reparsed.expiration.date() == parsed.expiration.date()
        assert reparsed.holder_id == parsed.holder_id
        assert reparsed.features == parsed.features
        assert reparsed.signature == parsed.signature
    
    @given(license_key=valid_license_key())
    @settings(max_examples=100)
    def test_is_valid_format_returns_true_for_valid_keys(self, license_key: str):
        """
        Property: For any valid license key, is_valid_format should return True.
        
        Feature: license-enablement, Property 14: License Key Format Parsing
        Validates: Requirements 9.2
        """
        is_valid, error = LicenseKeyParser.is_valid_format(license_key)
        assert is_valid is True
        assert error is None
    
    @given(parsed=valid_parsed_license_key())
    @settings(max_examples=100)
    def test_get_data_to_sign_is_deterministic(self, parsed: ParsedLicenseKey):
        """
        Property: For any ParsedLicenseKey, get_data_to_sign should return
        the same value when called multiple times.
        
        Feature: license-enablement, Property 14: License Key Format Parsing
        Validates: Requirements 9.2
        """
        data1 = parsed.get_data_to_sign()
        data2 = parsed.get_data_to_sign()
        
        assert data1 == data2
        # Should not include signature
        assert parsed.signature not in data1


# ==========================================
# Edge Case Tests (Unit Tests)
# ==========================================

class TestLicenseKeyParserEdgeCases:
    """Unit tests for edge cases and error conditions."""
    
    def test_empty_key_raises_error(self):
        """Empty license key should raise error."""
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse("")
        assert "empty" in exc_info.value.message.lower()
    
    def test_none_key_raises_error(self):
        """None license key should raise error."""
        with pytest.raises(LicenseKeyParseError):
            LicenseKeyParser.parse(None)
    
    def test_wrong_component_count_raises_error(self):
        """License key with wrong number of components should raise error."""
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse("v1.ENT.20261225.CUST-123")
        assert "6 components" in exc_info.value.message
    
    def test_invalid_version_raises_error(self):
        """Invalid version should raise error."""
        sig = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip('=')
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(f"v99.ENT.20261225.CUST-123.ALL.{sig}")
        assert "version" in exc_info.value.message.lower()
    
    def test_invalid_tier_raises_error(self):
        """Invalid tier abbreviation should raise error."""
        sig = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip('=')
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(f"v1.XXX.20261225.CUST-123.ALL.{sig}")
        assert "tier" in exc_info.value.message.lower()
    
    def test_invalid_expiration_format_raises_error(self):
        """Invalid expiration format should raise error."""
        sig = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip('=')
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(f"v1.ENT.2026-12-25.CUST-123.ALL.{sig}")
        assert "expiration" in exc_info.value.message.lower()
    
    def test_invalid_expiration_date_raises_error(self):
        """Invalid expiration date (e.g., month 13) should raise error."""
        sig = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip('=')
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(f"v1.ENT.20261325.CUST-123.ALL.{sig}")
        assert "expiration" in exc_info.value.message.lower() or "month" in exc_info.value.message.lower()
    
    def test_valid_key_parses_correctly(self):
        """A known valid key should parse correctly."""
        sig = base64.urlsafe_b64encode(b"x" * 64).decode().rstrip('=')
        key = f"v1.ENT.20261225.CUST-12345.ALL.{sig}"
        
        parsed = LicenseKeyParser.parse(key)
        
        assert parsed.version == "v1"
        assert parsed.tier == LicenseTier.ENTERPRISE
        assert parsed.expiration.year == 2026
        assert parsed.expiration.month == 12
        assert parsed.expiration.day == 25
        assert parsed.holder_id == "CUST-12345"
        assert parsed.features == "ALL"
        assert parsed.signature == sig
