"""
License Key Parser

Parses and validates license key format:
{version}.{tier}.{expiration}.{holder_id}.{features}.{signature}

Example: v1.ENT.20261225.CUST-12345.ALL.base64_signature_here
"""

import re
import base64
from datetime import datetime, timezone
from typing import Optional, Tuple

from ..models.enums import LicenseTier, TIER_ABBREVIATIONS, TIER_TO_ABBREVIATION
from ..models.license_model import ParsedLicenseKey
from ..consts import LICENSE_KEY_SEPARATOR, LicenseErrorCode


class LicenseKeyParseError(Exception):
    """Exception raised when license key parsing fails."""
    def __init__(self, message: str, error_code: str = LicenseErrorCode.INVALID_FORMAT):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class LicenseKeyParser:
    """Parser for license key format."""
    
    # Valid version prefixes
    VALID_VERSIONS = {"v1", "v2"}
    
    # Regex patterns
    VERSION_PATTERN = re.compile(r"^v\d+$")
    HOLDER_ID_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+$")
    EXPIRATION_PATTERN = re.compile(r"^\d{8}$")
    
    @classmethod
    def parse(cls, license_key: str) -> ParsedLicenseKey:
        """
        Parse a license key string into its components.
        
        Args:
            license_key: The license key string to parse
            
        Returns:
            ParsedLicenseKey with all components
            
        Raises:
            LicenseKeyParseError: If the key format is invalid
        """
        if not license_key or not isinstance(license_key, str):
            raise LicenseKeyParseError("License key cannot be empty")
        
        # Split into components
        parts = license_key.split(LICENSE_KEY_SEPARATOR)
        
        if len(parts) != 6:
            raise LicenseKeyParseError(
                f"Invalid license key format: expected 6 components, got {len(parts)}"
            )
        
        version, tier_abbrev, expiration_str, holder_id, features, signature = parts
        
        # Validate version
        version = cls._validate_version(version)
        
        # Validate and convert tier
        tier = cls._validate_tier(tier_abbrev)
        
        # Validate and parse expiration
        expiration = cls._validate_expiration(expiration_str)
        
        # Validate holder ID
        holder_id = cls._validate_holder_id(holder_id)
        
        # Validate features
        features = cls._validate_features(features)
        
        # Validate signature (base64)
        signature = cls._validate_signature(signature)
        
        return ParsedLicenseKey(
            version=version,
            tier=tier,
            expiration=expiration,
            holder_id=holder_id,
            features=features,
            signature=signature,
            raw_key=license_key,
        )
    
    @classmethod
    def _validate_version(cls, version: str) -> str:
        """Validate version component."""
        if not cls.VERSION_PATTERN.match(version):
            raise LicenseKeyParseError(f"Invalid version format: {version}")
        if version not in cls.VALID_VERSIONS:
            raise LicenseKeyParseError(f"Unsupported version: {version}")
        return version
    
    @classmethod
    def _validate_tier(cls, tier_abbrev: str) -> LicenseTier:
        """Validate and convert tier abbreviation."""
        tier = TIER_ABBREVIATIONS.get(tier_abbrev.upper())
        if tier is None:
            valid_tiers = ", ".join(TIER_ABBREVIATIONS.keys())
            raise LicenseKeyParseError(
                f"Invalid tier abbreviation: {tier_abbrev}. Valid values: {valid_tiers}"
            )
        return tier
    
    @classmethod
    def _validate_expiration(cls, expiration_str: str) -> datetime:
        """Validate and parse expiration date."""
        if not cls.EXPIRATION_PATTERN.match(expiration_str):
            raise LicenseKeyParseError(
                f"Invalid expiration format: {expiration_str}. Expected YYYYMMDD"
            )
        
        try:
            year = int(expiration_str[:4])
            month = int(expiration_str[4:6])
            day = int(expiration_str[6:8])
            
            # Validate date components
            if month < 1 or month > 12:
                raise ValueError("Invalid month")
            if day < 1 or day > 31:
                raise ValueError("Invalid day")
            
            # Create datetime at end of day in UTC
            expiration = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
            return expiration
        except ValueError as e:
            raise LicenseKeyParseError(f"Invalid expiration date: {expiration_str} - {e}")
    
    @classmethod
    def _validate_holder_id(cls, holder_id: str) -> str:
        """Validate holder ID format."""
        if not holder_id:
            raise LicenseKeyParseError("Holder ID cannot be empty")
        # Allow flexible holder ID format but require at least some structure
        if len(holder_id) < 3:
            raise LicenseKeyParseError("Holder ID too short")
        return holder_id
    
    @classmethod
    def _validate_features(cls, features: str) -> str:
        """Validate features component."""
        if not features:
            raise LicenseKeyParseError("Features cannot be empty")
        # Features can be "ALL" or comma-separated feature codes
        return features.upper()
    
    @classmethod
    def _validate_signature(cls, signature: str) -> str:
        """Validate signature is valid base64."""
        if not signature:
            raise LicenseKeyParseError("Signature cannot be empty")
        
        try:
            # Try to decode base64 to verify format
            # Use URL-safe base64 decoding (allows - and _)
            decoded = base64.urlsafe_b64decode(signature + "==")  # Add padding
            if len(decoded) < 32:  # Minimum signature length
                raise LicenseKeyParseError("Signature too short")
            return signature
        except Exception:
            # Try standard base64
            try:
                decoded = base64.b64decode(signature + "==")
                if len(decoded) < 32:
                    raise LicenseKeyParseError("Signature too short")
                return signature
            except Exception:
                raise LicenseKeyParseError("Invalid signature: not valid base64")
    
    @classmethod
    def format_key(cls, parsed: ParsedLicenseKey) -> str:
        """
        Format a ParsedLicenseKey back into a license key string.
        
        Args:
            parsed: The parsed license key components
            
        Returns:
            Formatted license key string
        """
        tier_abbrev = TIER_TO_ABBREVIATION[parsed.tier]
        expiration_str = parsed.expiration.strftime("%Y%m%d")
        
        return LICENSE_KEY_SEPARATOR.join([
            parsed.version,
            tier_abbrev,
            expiration_str,
            parsed.holder_id,
            parsed.features,
            parsed.signature,
        ])
    
    @classmethod
    def is_valid_format(cls, license_key: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a license key has valid format without full parsing.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            cls.parse(license_key)
            return True, None
        except LicenseKeyParseError as e:
            return False, e.message
