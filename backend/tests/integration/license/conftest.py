"""
Pytest fixtures for license integration tests.
"""

import pytest
import pytest_asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from httpx import AsyncClient

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "30"))
API_KEY = os.getenv("API_KEY", "super-secret")


@pytest_asyncio.fixture
async def api_client():
    """Create async HTTP client for license API tests."""
    async with AsyncClient(
        base_url=TEST_BASE_URL,
        timeout=TEST_TIMEOUT,
        headers={"x-api-key": API_KEY}
    ) as client:
        yield client


@pytest.fixture
def license_key_generator():
    """Create a license key generator for tests."""
    from src.license.utils.key_generator import LicenseKeyGenerator
    from src.license.utils.keys import set_public_key
    
    generator = LicenseKeyGenerator()
    # Set the public key for verification
    set_public_key(generator.get_public_key_pem())
    return generator


@pytest.fixture
def valid_enterprise_key(license_key_generator):
    """Generate a valid enterprise license key."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_key(
        tier=LicenseTier.ENTERPRISE,
        holder_id="TEST-ENTERPRISE-001",
        expiration=datetime.now(timezone.utc) + timedelta(days=365),
    )


@pytest.fixture
def valid_professional_key(license_key_generator):
    """Generate a valid professional license key."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_key(
        tier=LicenseTier.PROFESSIONAL,
        holder_id="TEST-PRO-001",
        expiration=datetime.now(timezone.utc) + timedelta(days=365),
    )


@pytest.fixture
def valid_basic_key(license_key_generator):
    """Generate a valid basic license key."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_key(
        tier=LicenseTier.BASIC,
        holder_id="TEST-BASIC-001",
        expiration=datetime.now(timezone.utc) + timedelta(days=365),
    )


@pytest.fixture
def expired_license_key(license_key_generator):
    """Generate an expired license key."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_expired_key(
        tier=LicenseTier.BASIC,
        holder_id="TEST-EXPIRED-001",
        days_expired=30,
    )


@pytest.fixture
def expiring_soon_key(license_key_generator):
    """Generate a license key expiring soon (within 7 days)."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_expiring_soon_key(
        tier=LicenseTier.BASIC,
        holder_id="TEST-EXPIRING-001",
        days_until_expiration=7,
    )


@pytest.fixture
def renewal_key(license_key_generator):
    """Generate a renewal key for the same holder."""
    from src.license.models.enums import LicenseTier
    return license_key_generator.generate_key(
        tier=LicenseTier.ENTERPRISE,
        holder_id="TEST-ENTERPRISE-001",  # Same holder as enterprise key
        expiration=datetime.now(timezone.utc) + timedelta(days=730),  # 2 years
    )


class LicenseTestHelper:
    """Helper class for license integration tests."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
    
    async def activate_license(self, license_key: str) -> Dict[str, Any]:
        """Activate a license via API."""
        response = await self.client.post(
            "/api/v1/license/activate",
            json={"license_key": license_key}
        )
        return {"status_code": response.status_code, "data": response.json()}
    
    async def get_license_status(self) -> Dict[str, Any]:
        """Get license status via API."""
        response = await self.client.get("/api/v1/license/status")
        return {"status_code": response.status_code, "data": response.json()}
    
    async def deactivate_license(self, reason: str = "Test deactivation") -> Dict[str, Any]:
        """Deactivate license via API."""
        response = await self.client.post(
            "/api/v1/license/deactivate",
            json={"reason": reason, "confirm": True}
        )
        return {"status_code": response.status_code, "data": response.json()}
    
    async def renew_license(self, renewal_key: str) -> Dict[str, Any]:
        """Renew license via API."""
        response = await self.client.post(
            "/api/v1/license/renew",
            json={"renewal_key": renewal_key}
        )
        return {"status_code": response.status_code, "data": response.json()}
    
    async def check_feature(self, feature_id: str) -> Dict[str, Any]:
        """Check feature access via API."""
        response = await self.client.get(f"/api/v1/license/features/{feature_id}")
        return {"status_code": response.status_code, "data": response.json()}
    
    async def get_audit_logs(self, limit: int = 100) -> Dict[str, Any]:
        """Get audit logs via API."""
        response = await self.client.get(f"/api/v1/license/audit?limit={limit}")
        return {"status_code": response.status_code, "data": response.json()}
    
    async def validate_license(self) -> Dict[str, Any]:
        """Validate license via API."""
        response = await self.client.get("/api/v1/license/validate")
        return {"status_code": response.status_code, "data": response.json()}
    
    async def call_license_tool(self, **kwargs) -> Dict[str, Any]:
        """Call license tool via MCP endpoint."""
        response = await self.client.post(
            "/tools/license_tool",
            json={"arguments": kwargs}
        )
        return {"status_code": response.status_code, "data": response.json()}


@pytest_asyncio.fixture
async def license_helper(api_client):
    """Create license test helper."""
    return LicenseTestHelper(api_client)


@pytest_asyncio.fixture
async def clean_license_state(license_helper):
    """Ensure clean license state before and after tests."""
    # Try to deactivate any existing license
    try:
        await license_helper.deactivate_license("Test cleanup")
    except Exception:
        pass
    
    yield
    
    # Cleanup after test
    try:
        await license_helper.deactivate_license("Test cleanup")
    except Exception:
        pass
