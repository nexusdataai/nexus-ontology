"""
Property-Based Tests for Audit Logging Completeness

Feature: license-enablement, Property 13: Audit Logging Completeness
Validates: Requirements 8.1, 8.2, 8.3, 8.5

Tests that audit logging is complete and immutable.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
import os
import sys
import asyncio
from typing import List, Optional, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from license.models.license_model import LicenseAuditEntry
from license.models.enums import LicenseEventType
from license.services.audit_service import AuditService


# ==========================================
# Mock Repository
# ==========================================

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
        
        # Sort by timestamp descending
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        
        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        return paginated, total
    
    async def get_audit_logs_by_license(
        self,
        license_id: str,
        limit: int = 100,
    ) -> List[LicenseAuditEntry]:
        filtered = [e for e in self._entries if e.license_id == license_id]
        filtered.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered[:limit]
    
    def clear(self):
        self._entries.clear()


# ==========================================
# Custom Strategies
# ==========================================

@st.composite
def valid_event_type(draw):
    """Generate valid event types."""
    return draw(st.sampled_from(list(LicenseEventType)))


@st.composite
def valid_license_id(draw):
    """Generate valid license IDs."""
    suffix = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        min_size=6,
        max_size=8
    ))
    return f"LIC-{suffix}"


@st.composite
def valid_result(draw):
    """Generate valid result values."""
    return draw(st.sampled_from(["success", "failure", "denied"]))


@st.composite
def valid_details(draw):
    """Generate valid details dict."""
    keys = draw(st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=3, max_size=10),
        min_size=0,
        max_size=5,
    ))
    values = draw(st.lists(
        st.text(min_size=1, max_size=20),
        min_size=len(keys),
        max_size=len(keys),
    ))
    return dict(zip(keys, values))


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def mock_repository():
    """Create a fresh mock repository for each test."""
    return MockAuditRepository()


@pytest.fixture
def audit_service(mock_repository):
    """Create an audit service with mock repository."""
    return AuditService(repository=mock_repository)


# ==========================================
# Property Tests
# ==========================================

class TestAuditLoggingCompletenessProperties:
    """
    Property-based tests for audit logging completeness.
    
    Feature: license-enablement, Property 13: Audit Logging Completeness
    Validates: Requirements 8.1, 8.2, 8.3, 8.5
    """
    
    @given(
        event_type=valid_event_type(),
        result=valid_result(),
        license_id=valid_license_id(),
    )
    @settings(max_examples=100)
    def test_audit_entry_contains_required_fields(
        self, event_type, result, license_id, audit_service, mock_repository
    ):
        """
        Property: For any license operation, the audit entry SHALL contain
        timestamp, event_type, result, and operation-specific metadata.
        
        Feature: license-enablement, Property 13: Audit Logging Completeness
        Validates: Requirements 8.1, 8.2
        """
        mock_repository.clear()
        
        # Log an event
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_event(
                event_type=event_type,
                result=result,
                license_id=license_id,
            )
        )
        
        # Verify required fields
        assert entry.timestamp is not None
        assert entry.event_type == event_type
        assert entry.result == result
        assert entry.event_id is not None
        assert len(entry.event_id) > 0
    
    @given(
        event_type=valid_event_type(),
        result=valid_result(),
        license_id=valid_license_id(),
        details=valid_details(),
    )
    @settings(max_examples=100)
    def test_audit_entry_preserves_details(
        self, event_type, result, license_id, details, audit_service, mock_repository
    ):
        """
        Property: Audit entries SHALL preserve operation-specific metadata.
        
        Feature: license-enablement, Property 13: Audit Logging Completeness
        Validates: Requirements 8.2
        """
        mock_repository.clear()
        
        # Log an event with details
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_event(
                event_type=event_type,
                result=result,
                license_id=license_id,
                details=details,
            )
        )
        
        # Verify details are preserved
        assert entry.details == details
    
    @given(num_entries=st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    def test_audit_logs_paginated_chronologically(
        self, num_entries, audit_service, mock_repository
    ):
        """
        Property: Audit log queries SHALL return paginated results in chronological order.
        
        Feature: license-enablement, Property 13: Audit Logging Completeness
        Validates: Requirements 8.3
        """
        mock_repository.clear()
        
        # Create multiple entries
        for i in range(num_entries):
            asyncio.get_event_loop().run_until_complete(
                audit_service.log_event(
                    event_type=LicenseEventType.VALIDATED,
                    result="success",
                    license_id=f"LIC-{i:04d}",
                )
            )
        
        # Retrieve logs
        logs = asyncio.get_event_loop().run_until_complete(
            audit_service.get_logs(limit=100)
        )
        
        assert logs["total_count"] == num_entries
        
        # Verify chronological order (most recent first)
        entries = logs["entries"]
        for i in range(len(entries) - 1):
            assert entries[i]["timestamp"] >= entries[i + 1]["timestamp"]
    
    @given(
        page_size=st.integers(min_value=1, max_value=10),
        total_entries=st.integers(min_value=5, max_value=30),
    )
    @settings(max_examples=50)
    def test_audit_logs_pagination(
        self, page_size, total_entries, audit_service, mock_repository
    ):
        """
        Property: Audit logs SHALL support pagination with limit and offset.
        
        Feature: license-enablement, Property 13: Audit Logging Completeness
        Validates: Requirements 8.3
        """
        mock_repository.clear()
        
        # Create entries
        for i in range(total_entries):
            asyncio.get_event_loop().run_until_complete(
                audit_service.log_event(
                    event_type=LicenseEventType.VALIDATED,
                    result="success",
                    license_id=f"LIC-{i:04d}",
                )
            )
        
        # Get first page
        page1 = asyncio.get_event_loop().run_until_complete(
            audit_service.get_logs(limit=page_size, offset=0)
        )
        
        assert page1["total_count"] == total_entries
        assert page1["page_size"] == page_size
        assert len(page1["entries"]) == min(page_size, total_entries)
        
        # Get second page
        page2 = asyncio.get_event_loop().run_until_complete(
            audit_service.get_logs(limit=page_size, offset=page_size)
        )
        
        assert page2["offset"] == page_size
        
        # Entries should be different
        if len(page1["entries"]) > 0 and len(page2["entries"]) > 0:
            page1_ids = {e["event_id"] for e in page1["entries"]}
            page2_ids = {e["event_id"] for e in page2["entries"]}
            assert page1_ids.isdisjoint(page2_ids)
    
    @given(license_id=valid_license_id())
    @settings(max_examples=50)
    def test_audit_entries_immutable(
        self, license_id, audit_service, mock_repository
    ):
        """
        Property: Audit entries SHALL be immutable once created.
        
        Feature: license-enablement, Property 13: Audit Logging Completeness
        Validates: Requirements 8.5
        """
        mock_repository.clear()
        
        # Create an entry
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_event(
                event_type=LicenseEventType.ACTIVATED,
                result="success",
                license_id=license_id,
                details={"original": "data"},
            )
        )
        
        original_event_id = entry.event_id
        original_timestamp = entry.timestamp
        original_details = entry.details.copy()
        
        # Retrieve and verify unchanged
        logs = asyncio.get_event_loop().run_until_complete(
            audit_service.get_logs(limit=1)
        )
        
        retrieved = logs["entries"][0]
        assert retrieved["event_id"] == original_event_id
        assert retrieved["details"] == original_details


class TestAuditServiceHelpers:
    """Unit tests for audit service helper methods."""
    
    def test_log_activation(self, audit_service, mock_repository):
        """Test activation logging helper."""
        mock_repository.clear()
        
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_activation(
                license_id="LIC-TEST001",
                tier="enterprise",
                holder_id="CUST-001",
                expires_at="2026-12-25T23:59:59Z",
            )
        )
        
        assert entry.event_type == LicenseEventType.ACTIVATED
        assert entry.result == "success"
        assert entry.details["tier"] == "enterprise"
    
    def test_log_deactivation(self, audit_service, mock_repository):
        """Test deactivation logging helper."""
        mock_repository.clear()
        
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_deactivation(
                license_id="LIC-TEST001",
                reason="Server migration",
            )
        )
        
        assert entry.event_type == LicenseEventType.DEACTIVATED
        assert entry.details["reason"] == "Server migration"
    
    def test_log_renewal(self, audit_service, mock_repository):
        """Test renewal logging helper."""
        mock_repository.clear()
        
        entry = asyncio.get_event_loop().run_until_complete(
            audit_service.log_renewal(
                license_id="LIC-TEST001",
                previous_expiration="2025-12-25",
                new_expiration="2026-12-25",
                tier_changed=True,
                new_tier="enterprise",
            )
        )
        
        assert entry.event_type == LicenseEventType.RENEWED
        assert entry.details["tier_changed"] is True
    
    def test_get_logs_by_license(self, audit_service, mock_repository):
        """Test filtering logs by license ID."""
        mock_repository.clear()
        
        # Create entries for different licenses
        for i in range(5):
            asyncio.get_event_loop().run_until_complete(
                audit_service.log_event(
                    event_type=LicenseEventType.VALIDATED,
                    result="success",
                    license_id="LIC-TARGET",
                )
            )
            asyncio.get_event_loop().run_until_complete(
                audit_service.log_event(
                    event_type=LicenseEventType.VALIDATED,
                    result="success",
                    license_id="LIC-OTHER",
                )
            )
        
        # Get logs for specific license
        logs = asyncio.get_event_loop().run_until_complete(
            audit_service.get_logs_by_license("LIC-TARGET")
        )
        
        assert len(logs) == 5
        for log in logs:
            assert log.get("event_type") == "license_validated"
