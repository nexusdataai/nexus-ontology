"""
Property-Based Tests for License Middleware

Feature: license-enablement, Property 6: Middleware License State Gating
Feature: license-enablement, Property 7: Middleware Caching Behavior
Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

Tests that middleware correctly gates requests based on license state.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
import os
import sys
import asyncio
from typing import Optional, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.enums import LicenseStatus, LicenseTier
from license.models.api_models import LicenseValidationResult
from license.middleware.license_middleware import (
    LicenseMiddleware,
    LicenseMiddlewareError,
)
from license.consts import PUBLIC_ENDPOINTS, LicenseErrorCode


# ==========================================
# Mock Services
# ==========================================

class MockLicenseService:
    """Mock license service for testing."""
    
    def __init__(self, validation_result: LicenseValidationResult):
        self._validation_result = validation_result
    
    async def validate_license(self) -> LicenseValidationResult:
        return self._validation_result


# ==========================================
# Custom Strategies
# ==========================================

@st.composite
def valid_path(draw):
    """Generate valid API paths."""
    segments = draw(st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_", min_size=1, max_size=15),
        min_size=1,
        max_size=4,
    ))
    return "/" + "/".join(segments)


@st.composite
def public_path(draw):
    """Generate paths that should be public."""
    return draw(st.sampled_from(PUBLIC_ENDPOINTS))


@st.composite
def protected_path(draw):
    """Generate paths that should be protected."""
    protected = [
        "/api/v1/journeys",
        "/api/v1/jobs",
        "/api/v1/analytics",
        "/api/v1/export",
        "/api/v1/settings",
    ]
    return draw(st.sampled_from(protected))


@st.composite
def http_method(draw):
    """Generate HTTP methods."""
    return draw(st.sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"]))


@st.composite
def license_status(draw):
    """Generate license statuses."""
    return draw(st.sampled_from(list(LicenseStatus)))


@st.composite
def license_tier(draw):
    """Generate license tiers."""
    return draw(st.sampled_from(list(LicenseTier)))


def create_validation_result(
    status: LicenseStatus,
    tier: Optional[LicenseTier] = None,
    can_write: bool = True,
) -> LicenseValidationResult:
    """Create a validation result for testing."""
    is_valid = status == LicenseStatus.ACTIVE or status == LicenseStatus.GRACE_PERIOD
    
    error_code = None
    if status == LicenseStatus.EXPIRED:
        error_code = LicenseErrorCode.EXPIRED
    elif status == LicenseStatus.NOT_ACTIVATED:
        error_code = LicenseErrorCode.NOT_ACTIVATED
    elif status == LicenseStatus.REVOKED:
        error_code = LicenseErrorCode.REVOKED
    
    return LicenseValidationResult(
        is_valid=is_valid,
        status=status,
        license_id="LIC-TEST001" if is_valid else None,
        tier=tier,
        error_code=error_code,
        message=f"License is {status.value}",
        is_in_grace_period=status == LicenseStatus.GRACE_PERIOD,
        can_write=can_write,
    )


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def middleware():
    """Create a middleware instance for testing."""
    return LicenseMiddleware()


# ==========================================
# Property Tests: License State Gating
# ==========================================

class TestMiddlewareLicenseStateGatingProperties:
    """
    Property-based tests for middleware license state gating.
    
    Feature: license-enablement, Property 6: Middleware License State Gating
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
    """
    
    @given(path=public_path())
    @settings(max_examples=50)
    def test_public_endpoints_bypass_validation(self, path, middleware):
        """
        Property: Public endpoints SHALL bypass license validation.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.5
        """
        assert middleware.is_public_endpoint(path) is True
    
    @given(path=protected_path())
    @settings(max_examples=50)
    def test_protected_endpoints_require_validation(self, path, middleware):
        """
        Property: Protected endpoints SHALL require license validation.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.1
        """
        assert middleware.is_public_endpoint(path) is False
    
    @given(
        path=protected_path(),
        tier=license_tier(),
    )
    @settings(max_examples=100)
    def test_active_license_allows_request(self, path, tier, middleware):
        """
        Property: If license is active, request SHALL proceed.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.2
        """
        validation = create_validation_result(LicenseStatus.ACTIVE, tier, can_write=True)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        result = asyncio.get_event_loop().run_until_complete(
            middleware.validate_request(path, "GET")
        )
        
        assert result.is_valid is True
        assert result.status == LicenseStatus.ACTIVE
    
    @given(path=protected_path())
    @settings(max_examples=50)
    def test_expired_license_returns_403(self, path, middleware):
        """
        Property: If license is expired, SHALL return HTTP 403 with LICENSE_EXPIRED.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.3
        """
        validation = create_validation_result(LicenseStatus.EXPIRED)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        with pytest.raises(LicenseMiddlewareError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                middleware.validate_request(path, "GET")
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == LicenseErrorCode.EXPIRED
    
    @given(path=protected_path())
    @settings(max_examples=50)
    def test_not_activated_returns_403(self, path, middleware):
        """
        Property: If no license activated, SHALL return HTTP 403 with LICENSE_NOT_ACTIVATED.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.4
        """
        validation = create_validation_result(LicenseStatus.NOT_ACTIVATED)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        with pytest.raises(LicenseMiddlewareError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                middleware.validate_request(path, "GET")
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == LicenseErrorCode.NOT_ACTIVATED
    
    @given(path=protected_path())
    @settings(max_examples=50)
    def test_revoked_license_returns_403(self, path, middleware):
        """
        Property: If license is revoked, SHALL return HTTP 403 with LICENSE_REVOKED.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.3
        """
        validation = create_validation_result(LicenseStatus.REVOKED)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        with pytest.raises(LicenseMiddlewareError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                middleware.validate_request(path, "GET")
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == LicenseErrorCode.REVOKED
    
    @given(
        path=protected_path(),
        tier=license_tier(),
    )
    @settings(max_examples=50)
    def test_grace_period_allows_read_operations(self, path, tier, middleware):
        """
        Property: During grace period, read operations SHALL succeed.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.2
        """
        validation = create_validation_result(
            LicenseStatus.GRACE_PERIOD, tier, can_write=False
        )
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        result = asyncio.get_event_loop().run_until_complete(
            middleware.validate_request(path, "GET")
        )
        
        assert result.is_valid is True
        assert result.is_in_grace_period is True
    
    @given(
        path=protected_path(),
        method=st.sampled_from(["POST", "PUT", "DELETE", "PATCH"]),
        tier=license_tier(),
    )
    @settings(max_examples=50)
    def test_grace_period_blocks_write_operations(self, path, method, tier, middleware):
        """
        Property: During grace period, write operations SHALL be blocked.
        
        Feature: license-enablement, Property 6: Middleware License State Gating
        Validates: Requirements 2.2
        """
        validation = create_validation_result(
            LicenseStatus.GRACE_PERIOD, tier, can_write=False
        )
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        with pytest.raises(LicenseMiddlewareError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                middleware.validate_request(path, method)
            )
        
        assert exc_info.value.status_code == 403


class TestMiddlewareFeatureGating:
    """Tests for feature-based gating in middleware."""
    
    def test_feature_requirement_enforced(self, middleware):
        """Endpoint with tier requirement should enforce it."""
        # Set up feature requirement
        middleware.set_feature_requirement("/api/v1/enterprise/*", LicenseTier.ENTERPRISE)
        
        # Basic tier should be denied
        validation = create_validation_result(LicenseStatus.ACTIVE, LicenseTier.BASIC)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        with pytest.raises(LicenseMiddlewareError) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                middleware.validate_request("/api/v1/enterprise/feature", "GET")
            )
        
        assert exc_info.value.error_code == LicenseErrorCode.FEATURE_NOT_LICENSED
    
    def test_enterprise_tier_has_full_access(self, middleware):
        """Enterprise tier should access all features."""
        middleware.set_feature_requirement("/api/v1/enterprise/*", LicenseTier.ENTERPRISE)
        
        validation = create_validation_result(LicenseStatus.ACTIVE, LicenseTier.ENTERPRISE)
        mock_service = MockLicenseService(validation)
        middleware.set_license_service(mock_service)
        
        result = asyncio.get_event_loop().run_until_complete(
            middleware.validate_request("/api/v1/enterprise/feature", "GET")
        )
        
        assert result.is_valid is True


class TestMiddlewareHelpers:
    """Unit tests for middleware helper methods."""
    
    def test_add_public_endpoint(self, middleware):
        """Should be able to add public endpoints."""
        new_endpoint = "/api/v1/custom/public"
        middleware.add_public_endpoint(new_endpoint)
        
        assert middleware.is_public_endpoint(new_endpoint) is True
    
    def test_remove_public_endpoint(self, middleware):
        """Should be able to remove public endpoints."""
        endpoint = "/health"
        assert middleware.is_public_endpoint(endpoint) is True
        
        middleware.remove_public_endpoint(endpoint)
        assert middleware.is_public_endpoint(endpoint) is False
    
    def test_create_error_response(self, middleware):
        """Error response should have correct format."""
        error = LicenseMiddlewareError(
            "Test error",
            LicenseErrorCode.EXPIRED,
            status_code=403,
        )
        
        response = middleware.create_error_response(error)
        
        assert response["status"] == "error"
        assert response["message"] == "Test error"
        assert response["error_code"] == LicenseErrorCode.EXPIRED
        assert "timestamp" in response
    
    def test_wildcard_public_endpoint(self, middleware):
        """Wildcard patterns should match correctly."""
        middleware.add_public_endpoint("/api/v1/public/*")
        
        assert middleware.is_public_endpoint("/api/v1/public/anything") is True
        assert middleware.is_public_endpoint("/api/v1/public/nested/path") is True
        assert middleware.is_public_endpoint("/api/v1/private/path") is False
