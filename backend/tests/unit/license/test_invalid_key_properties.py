"""
Property-Based Tests for Invalid Key Error Handling

Feature: license-enablement, Property 4: Invalid Key Error Handling
Validates: Requirements 1.4

Tests that strings not conforming to license key format return LICENSE_INVALID_FORMAT error.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.utils.key_parser import LicenseKeyParser, LicenseKeyParseError
from license.consts import LicenseErrorCode


# ==========================================
# Strategies for Invalid Keys
# ==========================================

@st.composite
def invalid_component_count(draw):
    """Generate strings with wrong number of components (not 6)."""
    num_parts = draw(st.integers(min_value=1, max_value=10).filter(lambda x: x != 6))
    parts = [draw(st.text(min_size=1, max_size=20, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")) 
             for _ in range(num_parts)]
    return ".".join(parts)


@st.composite
def invalid_version_key(draw):
    """Generate keys with invalid version prefix."""
    invalid_versions = ["v0", "v99", "x1", "1", "version1", "V1", ""]
    version = draw(st.sampled_from(invalid_versions))
    # Rest of key is valid format
    return f"{version}.ENT.20261225.CUST-123.ALL.YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo"


@st.composite
def invalid_tier_key(draw):
    """Generate keys with invalid tier abbreviation."""
    invalid_tiers = ["XXX", "BASIC", "PRO1", "E", "enterprise", ""]
    tier = draw(st.sampled_from(invalid_tiers))
    return f"v1.{tier}.20261225.CUST-123.ALL.YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo"


@st.composite
def invalid_expiration_format_key(draw):
    """Generate keys with invalid expiration format."""
    invalid_expirations = [
        "2026-12-25",  # Wrong format (dashes)
        "26122025",    # Wrong order
        "202612",      # Too short
        "2026122500",  # Too long
        "abcdefgh",    # Not numeric
        "",            # Empty
    ]
    expiration = draw(st.sampled_from(invalid_expirations))
    return f"v1.ENT.{expiration}.CUST-123.ALL.YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo"


@st.composite
def invalid_expiration_date_key(draw):
    """Generate keys with invalid date values."""
    invalid_dates = [
        "20261325",  # Month 13
        "20260230",  # Feb 30
        "20260000",  # Day 0
        "20260132",  # Day 32
    ]
    date = draw(st.sampled_from(invalid_dates))
    return f"v1.ENT.{date}.CUST-123.ALL.YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo"


@st.composite
def empty_component_key(draw):
    """Generate keys with empty components."""
    # Pick which component to make empty
    component_idx = draw(st.integers(min_value=0, max_value=5))
    parts = ["v1", "ENT", "20261225", "CUST-123", "ALL", "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY3ODkwYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo"]
    parts[component_idx] = ""
    return ".".join(parts)


@st.composite
def random_garbage_string(draw):
    """Generate random strings that are unlikely to be valid keys."""
    length = draw(st.integers(min_value=1, max_value=100))
    return draw(st.text(min_size=length, max_size=length))


# ==========================================
# Property Tests
# ==========================================

class TestInvalidKeyErrorHandling:
    """
    Property-based tests for invalid key error handling.
    
    Feature: license-enablement, Property 4: Invalid Key Error Handling
    Validates: Requirements 1.4
    """
    
    @given(key=invalid_component_count())
    @settings(max_examples=100)
    def test_wrong_component_count_returns_invalid_format(self, key):
        """
        Property: Keys with wrong number of components should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=invalid_version_key())
    @settings(max_examples=50)
    def test_invalid_version_returns_invalid_format(self, key):
        """
        Property: Keys with invalid version should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=invalid_tier_key())
    @settings(max_examples=50)
    def test_invalid_tier_returns_invalid_format(self, key):
        """
        Property: Keys with invalid tier abbreviation should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=invalid_expiration_format_key())
    @settings(max_examples=50)
    def test_invalid_expiration_format_returns_invalid_format(self, key):
        """
        Property: Keys with invalid expiration format should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=invalid_expiration_date_key())
    @settings(max_examples=50)
    def test_invalid_expiration_date_returns_invalid_format(self, key):
        """
        Property: Keys with invalid date values should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=empty_component_key())
    @settings(max_examples=50)
    def test_empty_component_returns_invalid_format(self, key):
        """
        Property: Keys with empty components should return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    @given(key=random_garbage_string())
    @settings(max_examples=100)
    def test_random_strings_return_invalid_format_or_parse(self, key):
        """
        Property: Random strings should either parse (unlikely) or return LICENSE_INVALID_FORMAT.
        
        Feature: license-enablement, Property 4: Invalid Key Error Handling
        Validates: Requirements 1.4
        """
        try:
            # If it parses, that's fine (very unlikely for random strings)
            LicenseKeyParser.parse(key)
        except LicenseKeyParseError as e:
            # Should have the correct error code
            assert e.error_code == LicenseErrorCode.INVALID_FORMAT


# ==========================================
# Unit Tests for Specific Invalid Cases
# ==========================================

class TestInvalidKeyEdgeCases:
    """Unit tests for specific invalid key scenarios."""
    
    def test_none_returns_invalid_format(self):
        """None should return LICENSE_INVALID_FORMAT."""
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(None)
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    def test_empty_string_returns_invalid_format(self):
        """Empty string should return LICENSE_INVALID_FORMAT."""
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse("")
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    def test_whitespace_only_returns_invalid_format(self):
        """Whitespace-only string should return LICENSE_INVALID_FORMAT."""
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse("   ")
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
    
    def test_is_valid_format_returns_false_for_invalid(self):
        """is_valid_format should return (False, error_message) for invalid keys."""
        is_valid, error = LicenseKeyParser.is_valid_format("invalid.key")
        assert is_valid is False
        assert error is not None
    
    def test_short_signature_returns_invalid_format(self):
        """Signature that's too short should return LICENSE_INVALID_FORMAT."""
        # Signature decodes to less than 32 bytes
        short_sig = "YWJj"  # "abc" in base64
        key = f"v1.ENT.20261225.CUST-123.ALL.{short_sig}"
        
        with pytest.raises(LicenseKeyParseError) as exc_info:
            LicenseKeyParser.parse(key)
        assert exc_info.value.error_code == LicenseErrorCode.INVALID_FORMAT
