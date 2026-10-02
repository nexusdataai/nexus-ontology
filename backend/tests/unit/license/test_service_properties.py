"""
Property-Based Tests for License Service

Tests for core license service operations including activation idempotence,
response completeness, deactivation effects, and renewal validation.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timezone, timedelta
import os
import sys
import asyncio
from typing import Dict, Any, Optional, List
from unittest.mock import AsyncMock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.license_model import LicenseRecord, LicenseAuditEntry
from license.models.enums import LicenseTier, LicenseStatus, LicenseEventType
from license.models.api_models import LicenseValidationResult
from license.utils.key_generator import LicenseKeyGenerator
from license.utils.key_parser import LicenseKeyParser
from license.utils.keys import set_public_key, clear_public_key
from license.utils.crypto import LicenseCrypto
from license.services.license_service import LicenseService
from license.services.cache_manager import LicenseCacheManager
from license.consts import TIER_FEATURES, DEFAULT_GRACE_PERIOD_DAYS


# ==========================================
# Mock Repository Classes
# ==========================================

class MockLicenseRepository:
    """In-memory mock repository for testing."""
    
    def __init__(self):
        self._licenses: Dict[str, LicenseRecord] = {}
    
    async def save_license(self, record: LicenseRecord) -> LicenseRecord:
        key = f"{record.PK}:{record.SK}"
        self._licenses[key] = record
        return record
    
    async def get_license_by_instance(self, instance_id: str) -> Optional[LicenseRecord]:
        pk = f"INSTANCE#{instance_id}"
        for key, record in self._licenses.items():
            if key.startswith(pk):
                return record
        return None
    
    async def get_license_by_id(self, instance_id: str, license_id: str) -> Optional[LicenseRecord]:
        key = f"INSTANCE#{instance_id}:LICENSE#{license_id}"
        return self._licenses.get(key)
    
    async def update_license_status(
        self,
        instance_id: str,
        license_id: str,
        status: LicenseStatus,
        deactivated_at: Optional[datetime] = None,
        grace_period_ends_at: Optional[datetime] = None,
    ) -> Optional[LicenseRecord]:
        pk = f"INSTANCE#{instance_id}"
        for key, record in self._licenses.items():
            if key.startswith(pk) and record.license_id == license_id:
                record.status = status
                if deactivated_at:
                    record.deactivated_at = deactivated_at
                if grace_period_ends_at:
                    record.grace_period_ends_at = grace_period_ends_at
                return record
        return None
    
    async def update_license_expiration(
        self,
        instance_id: str,
        license_id: str,
        expires_at: datetime,
        tier: Optional[LicenseTier] = None,
        enabled_features: Optional[List[str]] = None,
    ) -> Optional[LicenseRecord]:
        pk = f"INSTANCE#{instance_id}"
        for key, record in self._licenses.items():
            if key.startswith(pk) and record.license_id == license_id:
                record.expires_at = expires_at
                record.status = LicenseStatus.ACTIVE
                if tier:
                    record.tier = tier
                if enabled_features:
                    record.enabled_features = enabled_features
                return record
        return None
    
    def clear(self):
        self._licenses.clear()


class MockAuditRepository:
    """In-memory mock audit repository for testing."""
    
    def __init__(self):
        self._entries: List[LicenseAuditEntry] = []
    
    async def save_audit_entry(self, entry: LicenseAuditEntry) -> LicenseAuditEntry:
        self._entries.append(entry)
        return entry
    
    async def get_audit_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple:
        filtered = self._entries
        if start_date:
            filtered = [e for e in filtered if e.timestamp >= start_date]
        if end_date:
            filtered = [e for e in filtered if e.timestamp <= end_date]
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        return paginated, total
    
    def clear(self):
        self._entries.clear()


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
def valid_expiration_days(draw):
    """Generate valid days until expiration."""
    return draw(st.integers(min_value=1, max_value=3650))


@st.composite
def deactivation_reason(draw):
    """Generate valid deactivation reasons."""
    reasons = [
        "Transferring to new server",
        "License upgrade",
        "End of contract",
        "Testing purposes",
        "Server decommission",
    ]
    return draw(st.sampled_from(reasons))


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
def mock_repository():
    """Create a fresh mock repository for each test."""
    return MockLicenseRepository()


@pytest.fixture
def mock_audit_repository():
    """Create a fresh mock audit repository for each test."""
    return MockAuditRepository()


@pytest.fixture
def cache_manager():
    """Create a fresh cache manager for each test."""
    return LicenseCacheManager()


def create_service(
    key_generator: LicenseKeyGenerator,
    mock_repository: MockLicenseRepository,
    mock_audit_repository: MockAuditRepository,
    cache_manager: LicenseCacheManager,
    instance_id: str,
) -> LicenseService:
    """Create a license service with mocked dependencies."""
    crypto = LicenseCrypto(key_generator.get_public_key_pem())
    return LicenseService(
        repository=mock_repository,
        audit_repository=mock_audit_repository,
        cache_manager=cache_manager,
        crypto=crypto,
        instance_id=instance_id,
    )


# ==========================================
# Property Tests: Activation Idempotence
# ==========================================

class TestActivationIdempotenceProperties:
    """
    Property-based tests for activation idempotence.
    
    Feature: license-enablement, Property 3: Activation Idempotence
    Validates: Requirements 1.3
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_activation_idempotence(
        self, tier, holder_id, instance_id, days_valid, key_generator
    ):
        """
        Property: For any license key, activating it twice on the same instance
        SHALL return the same activation status and SHALL NOT create duplicate records.
        
        Feature: license-enablement, Property 3: Activation Idempotence
        Validates: Requirements 1.3
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Generate license key
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        # First activation
        result1 = asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Second activation with same key
        result2 = asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Both should succeed
        assert result1.status == "success"
        assert result2.status == "success"
        
        # Should return same license ID
        assert result1.data.license_id == result2.data.license_id
        
        # Should have same tier and holder
        assert result1.data.tier == result2.data.tier
        assert result1.data.holder_id == result2.data.holder_id
        
        # Should only have one license record in repository
        count = len([k for k in mock_repo._licenses.keys() if instance_id in k])
        assert count == 1
    
    @given(
        tier1=valid_tier(),
        tier2=valid_tier(),
        holder_id1=valid_holder_id(),
        holder_id2=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=50)
    def test_different_key_activation_blocked(
        self, tier1, tier2, holder_id1, holder_id2, instance_id, key_generator
    ):
        """
        Property: Activating a different license key on an already-activated
        instance SHALL return an error.
        
        Feature: license-enablement, Property 3: Activation Idempotence
        Validates: Requirements 1.3
        """
        # Ensure different holder IDs
        assume(holder_id1 != holder_id2)
        
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Generate two different license keys
        key1 = key_generator.generate_key(tier1, holder_id1)
        key2 = key_generator.generate_key(tier2, holder_id2)
        
        # First activation should succeed
        result1 = asyncio.get_event_loop().run_until_complete(
            service.activate_license(key1)
        )
        assert result1.status == "success"
        
        # Second activation with different key should fail
        result2 = asyncio.get_event_loop().run_until_complete(
            service.activate_license(key2)
        )
        assert result2.status == "error"
        assert result2.error_code == "LICENSE_ALREADY_ACTIVATED"


# ==========================================
# Property Tests: Activation Response Completeness
# ==========================================

class TestActivationResponseCompletenessProperties:
    """
    Property-based tests for activation response completeness.
    
    Feature: license-enablement, Property 5: Activation Response Completeness
    Validates: Requirements 1.6
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_activation_response_contains_all_required_fields(
        self, tier, holder_id, instance_id, days_valid, key_generator
    ):
        """
        Property: For any successful license activation, the response SHALL
        contain all required fields: license_id, tier, holder_name, holder_id,
        activated_at, expires_at, days_remaining, features, and is_active.
        
        Feature: license-enablement, Property 5: Activation Response Completeness
        Validates: Requirements 1.6
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Generate and activate license
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        result = asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Should succeed
        assert result.status == "success"
        assert result.data is not None
        
        # Verify all required fields are present
        data = result.data
        assert data.license_id is not None and len(data.license_id) > 0
        assert data.tier == tier
        assert data.holder_name is not None and len(data.holder_name) > 0
        assert data.holder_id == holder_id
        assert data.activated_at is not None
        assert data.expires_at is not None
        assert data.days_remaining >= 0
        assert data.features is not None
        assert data.is_active is True
        
        # Verify expiration matches
        assert data.expires_at.date() == expiration.date()
        
        # Verify days remaining is approximately correct
        assert abs(data.days_remaining - days_valid) <= 1


# ==========================================
# Property Tests: Status Response Completeness
# ==========================================

class TestStatusResponseCompletenessProperties:
    """
    Property-based tests for status response completeness.
    
    Feature: license-enablement, Property 8: Status Response Completeness
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        days_valid=valid_expiration_days(),
    )
    @settings(max_examples=100)
    def test_active_license_status_completeness(
        self, tier, holder_id, instance_id, days_valid, key_generator
    ):
        """
        Property: For any active license, status response SHALL include
        expiration_date, days_remaining, tier, features, holder_name, activated_at.
        
        Feature: license-enablement, Property 8: Status Response Completeness
        Validates: Requirements 3.1, 3.2, 3.5
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        expiration = datetime.now(timezone.utc) + timedelta(days=days_valid)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Get status
        status = asyncio.get_event_loop().run_until_complete(
            service.get_license_status()
        )
        
        assert status.status == "success"
        data = status.data
        
        # Verify required fields for active license
        assert data.license_status == LicenseStatus.ACTIVE
        assert data.expires_at is not None
        assert data.days_remaining is not None
        assert data.tier == tier
        assert data.features is not None
        assert data.holder_name is not None
        assert data.activated_at is not None
    
    @given(instance_id=valid_instance_id())
    @settings(max_examples=50)
    def test_not_activated_status_includes_instructions(
        self, instance_id, key_generator
    ):
        """
        Property: For not_activated state, status SHALL include activation_instructions.
        
        Feature: license-enablement, Property 8: Status Response Completeness
        Validates: Requirements 3.4
        """
        # Setup without activating
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Get status without activation
        status = asyncio.get_event_loop().run_until_complete(
            service.get_license_status()
        )
        
        assert status.status == "success"
        data = status.data
        
        assert data.license_status == LicenseStatus.NOT_ACTIVATED
        assert data.activation_instructions is not None
        assert len(data.activation_instructions) > 0
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=50)
    def test_expiring_soon_includes_warning(
        self, tier, holder_id, instance_id, key_generator
    ):
        """
        Property: For licenses within 30 days of expiration, status SHALL
        include is_expiring_soon=true and expiration_warning message.
        
        Feature: license-enablement, Property 8: Status Response Completeness
        Validates: Requirements 3.3
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license expiring in 15 days
        expiration = datetime.now(timezone.utc) + timedelta(days=15)
        license_key = key_generator.generate_key(tier, holder_id, expiration)
        
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Get status
        status = asyncio.get_event_loop().run_until_complete(
            service.get_license_status()
        )
        
        assert status.status == "success"
        data = status.data
        
        assert data.is_expiring_soon is True
        assert data.expiration_warning is not None
        assert "15" in data.expiration_warning or "14" in data.expiration_warning


# ==========================================
# Property Tests: Deactivation Effects
# ==========================================

class TestDeactivationEffectsProperties:
    """
    Property-based tests for deactivation effects.
    
    Feature: license-enablement, Property 9: Deactivation Effects
    Validates: Requirements 4.1, 4.2, 4.3, 4.4
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        reason=deactivation_reason(),
    )
    @settings(max_examples=100)
    def test_deactivation_updates_status(
        self, tier, holder_id, instance_id, reason, key_generator
    ):
        """
        Property: For any active license, after deactivation the License_Store
        record status SHALL be "deactivated".
        
        Feature: license-enablement, Property 9: Deactivation Effects
        Validates: Requirements 4.1
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        license_key = key_generator.generate_key(tier, holder_id)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Deactivate
        result = asyncio.get_event_loop().run_until_complete(
            service.deactivate_license(reason)
        )
        
        assert result.status == "success"
        
        # Verify status in repository
        record = asyncio.get_event_loop().run_until_complete(
            mock_repo.get_license_by_instance(instance_id)
        )
        assert record.status == LicenseStatus.DEACTIVATED
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        reason=deactivation_reason(),
    )
    @settings(max_examples=100)
    def test_deactivation_clears_cache(
        self, tier, holder_id, instance_id, reason, key_generator
    ):
        """
        Property: After deactivation, the license cache SHALL be cleared.
        
        Feature: license-enablement, Property 9: Deactivation Effects
        Validates: Requirements 4.2
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        license_key = key_generator.generate_key(tier, holder_id)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Verify cache has license
        cached = cache.get_license(instance_id)
        assert cached is not None
        
        # Deactivate
        asyncio.get_event_loop().run_until_complete(
            service.deactivate_license(reason)
        )
        
        # Verify cache is cleared
        cached_after = cache.get_license(instance_id)
        assert cached_after is None
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        reason=deactivation_reason(),
    )
    @settings(max_examples=100)
    def test_deactivation_creates_audit_entry(
        self, tier, holder_id, instance_id, reason, key_generator
    ):
        """
        Property: After deactivation, an audit log entry SHALL be created
        with event_type "license_deactivated".
        
        Feature: license-enablement, Property 9: Deactivation Effects
        Validates: Requirements 4.4
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        license_key = key_generator.generate_key(tier, holder_id)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Clear audit entries from activation
        initial_count = len(mock_audit._entries)
        
        # Deactivate
        asyncio.get_event_loop().run_until_complete(
            service.deactivate_license(reason)
        )
        
        # Verify audit entry was created
        assert len(mock_audit._entries) > initial_count
        
        # Find deactivation entry
        deactivation_entries = [
            e for e in mock_audit._entries 
            if e.event_type == LicenseEventType.DEACTIVATED
        ]
        assert len(deactivation_entries) >= 1
        
        # Verify entry has reason in details
        entry = deactivation_entries[-1]
        assert entry.details.get("reason") == reason
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
        reason=deactivation_reason(),
    )
    @settings(max_examples=50)
    def test_validation_fails_after_deactivation(
        self, tier, holder_id, instance_id, reason, key_generator
    ):
        """
        Property: After deactivation, license validation SHALL return invalid.
        
        Feature: license-enablement, Property 9: Deactivation Effects
        Validates: Requirements 4.3
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        license_key = key_generator.generate_key(tier, holder_id)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Verify valid before deactivation
        validation_before = asyncio.get_event_loop().run_until_complete(
            service.validate_license()
        )
        assert validation_before.is_valid is True
        
        # Deactivate
        asyncio.get_event_loop().run_until_complete(
            service.deactivate_license(reason)
        )
        
        # Verify invalid after deactivation
        validation_after = asyncio.get_event_loop().run_until_complete(
            service.validate_license()
        )
        assert validation_after.is_valid is False
        assert validation_after.status == LicenseStatus.DEACTIVATED


# ==========================================
# Property Tests: Renewal Validation
# ==========================================

class TestRenewalValidationProperties:
    """
    Property-based tests for renewal validation and update.
    
    Feature: license-enablement, Property 10: Renewal Validation and Update
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
    """
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=100)
    def test_renewal_holder_must_match(
        self, tier, holder_id, instance_id, key_generator
    ):
        """
        Property: The renewal key holder_id SHALL match the existing license holder_id.
        
        Feature: license-enablement, Property 10: Renewal Validation and Update
        Validates: Requirements 5.1
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license
        license_key = key_generator.generate_key(tier, holder_id)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Try to renew with different holder
        different_holder = holder_id + "X"
        renewal_key = key_generator.generate_key(tier, different_holder)
        
        result = asyncio.get_event_loop().run_until_complete(
            service.renew_license(renewal_key)
        )
        
        assert result.status == "error"
        assert result.error_code == "LICENSE_RENEWAL_INVALID"
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=100)
    def test_renewal_updates_expiration(
        self, tier, holder_id, instance_id, key_generator
    ):
        """
        Property: When renewal is valid, the expiration date SHALL be updated.
        
        Feature: license-enablement, Property 10: Renewal Validation and Update
        Validates: Requirements 5.2
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license expiring in 30 days (within renewal window)
        original_expiration = datetime.now(timezone.utc) + timedelta(days=30)
        license_key = key_generator.generate_key(tier, holder_id, original_expiration)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Renew with new expiration
        new_expiration = datetime.now(timezone.utc) + timedelta(days=365)
        renewal_key = key_generator.generate_key(tier, holder_id, new_expiration)
        
        result = asyncio.get_event_loop().run_until_complete(
            service.renew_license(renewal_key)
        )
        
        assert result.status == "success"
        assert result.data.previous_expiration.date() == original_expiration.date()
        assert result.data.new_expiration.date() == new_expiration.date()
    
    @given(
        original_tier=valid_tier(),
        new_tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=100)
    def test_renewal_tier_change_updates_features(
        self, original_tier, new_tier, holder_id, instance_id, key_generator
    ):
        """
        Property: If the renewal key is for a different tier, the tier and
        enabled_features SHALL be updated.
        
        Feature: license-enablement, Property 10: Renewal Validation and Update
        Validates: Requirements 5.3
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license expiring in 30 days
        original_expiration = datetime.now(timezone.utc) + timedelta(days=30)
        license_key = key_generator.generate_key(original_tier, holder_id, original_expiration)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Renew with different tier
        new_expiration = datetime.now(timezone.utc) + timedelta(days=365)
        renewal_key = key_generator.generate_key(new_tier, holder_id, new_expiration)
        
        result = asyncio.get_event_loop().run_until_complete(
            service.renew_license(renewal_key)
        )
        
        assert result.status == "success"
        assert result.data.tier == new_tier
        assert result.data.tier_changed == (original_tier != new_tier)
    
    @given(
        tier=valid_tier(),
        holder_id=valid_holder_id(),
        instance_id=valid_instance_id(),
    )
    @settings(max_examples=50)
    def test_renewal_response_contains_required_fields(
        self, tier, holder_id, instance_id, key_generator
    ):
        """
        Property: When renewal succeeds, the response SHALL contain
        previous_expiration and new_expiration.
        
        Feature: license-enablement, Property 10: Renewal Validation and Update
        Validates: Requirements 5.4
        """
        # Setup
        mock_repo = MockLicenseRepository()
        mock_audit = MockAuditRepository()
        cache = LicenseCacheManager()
        service = create_service(key_generator, mock_repo, mock_audit, cache, instance_id)
        
        # Activate license expiring in 30 days
        original_expiration = datetime.now(timezone.utc) + timedelta(days=30)
        license_key = key_generator.generate_key(tier, holder_id, original_expiration)
        asyncio.get_event_loop().run_until_complete(
            service.activate_license(license_key)
        )
        
        # Renew
        new_expiration = datetime.now(timezone.utc) + timedelta(days=365)
        renewal_key = key_generator.generate_key(tier, holder_id, new_expiration)
        
        result = asyncio.get_event_loop().run_until_complete(
            service.renew_license(renewal_key)
        )
        
        assert result.status == "success"
        assert result.data is not None
        assert result.data.license_id is not None
        assert result.data.previous_expiration is not None
        assert result.data.new_expiration is not None
        assert result.data.tier is not None
        assert result.data.features is not None
