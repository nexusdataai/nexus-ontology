"""
License Test Helper for BDD Tests

Provides helper functions for license-related BDD testing.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class LicenseTestHelper:
    """Helper class for license BDD tests."""
    
    _generator = None
    _public_key_set = False
    
    @classmethod
    def get_generator(cls):
        """Get or create license key generator."""
        if cls._generator is None:
            from src.license.utils.key_generator import LicenseKeyGenerator
            cls._generator = LicenseKeyGenerator()
        return cls._generator
    
    @classmethod
    def ensure_public_key_set(cls):
        """Ensure public key is set for verification."""
        if not cls._public_key_set:
            from src.license.utils.keys import set_public_key
            generator = cls.get_generator()
            set_public_key(generator.get_public_key_pem())
            cls._public_key_set = True
    
    @classmethod
    def generate_license_key(
        cls,
        tier: str,
        holder_id: Optional[str] = None,
        days_valid: int = 365
    ) -> str:
        """
        Generate a license key for testing.
        
        Args:
            tier: License tier (basic, professional, enterprise)
            holder_id: Optional holder ID
            days_valid: Days until expiration
            
        Returns:
            Generated license key string
        """
        from src.license.models.enums import LicenseTier
        
        cls.ensure_public_key_set()
        generator = cls.get_generator()
        
        tier_enum = getattr(LicenseTier, tier.upper())
        holder = holder_id or f"TEST-{tier.upper()}-001"
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        
        return generator.generate_key(tier_enum, holder, expiration)
    
    @classmethod
    def generate_expired_key(
        cls,
        tier: str = "basic",
        holder_id: Optional[str] = None,
        days_expired: int = 30
    ) -> str:
        """Generate an expired license key."""
        from src.license.models.enums import LicenseTier
        
        cls.ensure_public_key_set()
        generator = cls.get_generator()
        
        tier_enum = getattr(LicenseTier, tier.upper())
        holder = holder_id or f"TEST-EXPIRED-001"
        
        return generator.generate_expired_key(tier_enum, holder, days_expired)
    
    @classmethod
    def generate_expiring_soon_key(
        cls,
        tier: str = "basic",
        holder_id: Optional[str] = None,
        days_until_expiration: int = 7
    ) -> str:
        """Generate a license key expiring soon."""
        from src.license.models.enums import LicenseTier
        
        cls.ensure_public_key_set()
        generator = cls.get_generator()
        
        tier_enum = getattr(LicenseTier, tier.upper())
        holder = holder_id or f"TEST-EXPIRING-001"
        
        return generator.generate_expiring_soon_key(tier_enum, holder, days_until_expiration)
    
    @classmethod
    def reset(cls):
        """Reset the helper state (for test isolation)."""
        cls._generator = None
        cls._public_key_set = False
