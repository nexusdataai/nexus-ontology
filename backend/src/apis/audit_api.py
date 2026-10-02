"""
Audit API

REST API endpoints for audit log querying.
Provides listing, retrieval, and summary statistics for audit entries.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["audit"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class AuditEntry(BaseModel):
    """Audit log entry."""
    id: str = Field(..., description="Audit entry identifier")
    timestamp: str = Field(..., description="ISO timestamp of the event")
    user: str = Field(..., description="User who performed the action")
    action_type: str = Field(..., description="Type of action performed")
    resource: str = Field(..., description="Resource affected")
    details: Optional[str] = Field(None, description="Additional details")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    status: str = Field(..., description="Status (success, failure, etc.)")


class AuditStats(BaseModel):
    """Audit summary statistics."""
    total_entries: int = Field(..., description="Total number of audit entries")
    entries_today: int = Field(..., description="Entries created today")
    unique_users: int = Field(..., description="Number of unique users")
    top_actions: List[dict] = Field(..., description="List of top actions with counts")


# =============================================================================
# Hardcoded Sample Data
# =============================================================================

SAMPLE_AUDIT_ENTRIES: List[dict] = [
    {
        "id": "audit-001",
        "timestamp": "2025-02-27T10:15:32.000Z",
        "user": "admin@example.com",
        "action_type": "login",
        "resource": "auth",
        "details": "Successful login",
        "ip_address": "192.168.1.100",
        "status": "success"
    },
    {
        "id": "audit-002",
        "timestamp": "2025-02-27T10:14:18.000Z",
        "user": "agent@example.com",
        "action_type": "tool_execution",
        "resource": "get_account",
        "details": "Executed with account_id=ACC-12345",
        "ip_address": "192.168.1.101",
        "status": "success"
    },
    {
        "id": "audit-003",
        "timestamp": "2025-02-27T10:12:05.000Z",
        "user": "manager@example.com",
        "action_type": "config_update",
        "resource": "prompts/call_summary",
        "details": "Updated prompt content",
        "ip_address": "192.168.1.102",
        "status": "success"
    },
    {
        "id": "audit-004",
        "timestamp": "2025-02-27T09:58:42.000Z",
        "user": "agent@example.com",
        "action_type": "tool_execution",
        "resource": "search_enterprise_knowledge",
        "details": "Query: credit policy",
        "ip_address": "192.168.1.101",
        "status": "success"
    },
    {
        "id": "audit-005",
        "timestamp": "2025-02-27T09:45:11.000Z",
        "user": "admin@example.com",
        "action_type": "user_create",
        "resource": "users",
        "details": "Created user agent2@example.com",
        "ip_address": "192.168.1.100",
        "status": "success"
    },
    {
        "id": "audit-006",
        "timestamp": "2025-02-26T16:22:33.000Z",
        "user": "agent@example.com",
        "action_type": "tool_execution",
        "resource": "get_ar_balance",
        "details": "customer_id=CUST-789",
        "ip_address": "192.168.1.101",
        "status": "failure"
    },
]


def _filter_entries(
    start_date: Optional[str],
    end_date: Optional[str],
    user: Optional[str],
    action_type: Optional[str],
    limit: int,
    offset: int
) -> List[dict]:
    """Filter and paginate audit entries (mock implementation)."""
    filtered = list(SAMPLE_AUDIT_ENTRIES)
    
    if start_date:
        filtered = [e for e in filtered if e["timestamp"] >= start_date]
    if end_date:
        filtered = [e for e in filtered if e["timestamp"] <= end_date]
    if user:
        filtered = [e for e in filtered if user.lower() in e["user"].lower()]
    if action_type:
        filtered = [e for e in filtered if e["action_type"] == action_type]
    
    paginated = filtered[offset : offset + limit]
    return paginated


def _find_entry(log_id: str) -> Optional[dict]:
    """Find an audit entry by ID."""
    for e in SAMPLE_AUDIT_ENTRIES:
        if e["id"] == log_id:
            return dict(e)
    return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/logs", response_model=List[AuditEntry])
async def list_audit_logs(
    start_date: Optional[str] = Query(None, description="Filter entries from this date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter entries until this date (ISO format)"),
    user: Optional[str] = Query(None, description="Filter by user (partial match)"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> List[AuditEntry]:
    """
    List audit log entries with optional filters.
    
    Returns entries with id, timestamp, user, action_type, resource, details, ip_address, status.
    """
    entries = _filter_entries(start_date, end_date, user, action_type, limit, offset)
    return [AuditEntry(**e) for e in entries]


@router.get("/stats", response_model=AuditStats)
async def get_audit_stats() -> AuditStats:
    """
    Get audit summary statistics.
    
    Returns total_entries, entries_today, unique_users, and top_actions.
    """
    from datetime import datetime, timezone
    
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    
    entries_today = sum(1 for e in SAMPLE_AUDIT_ENTRIES if e["timestamp"].startswith(today_str))
    unique_users = len(set(e["user"] for e in SAMPLE_AUDIT_ENTRIES))
    
    action_counts: dict = {}
    for e in SAMPLE_AUDIT_ENTRIES:
        action_counts[e["action_type"]] = action_counts.get(e["action_type"], 0) + 1
    
    top_actions = [
        {"action": k, "count": v}
        for k, v in sorted(action_counts.items(), key=lambda x: -x[1])[:10]
    ]
    
    return AuditStats(
        total_entries=len(SAMPLE_AUDIT_ENTRIES),
        entries_today=entries_today,
        unique_users=unique_users,
        top_actions=top_actions
    )


@router.get("/logs/{log_id}", response_model=AuditEntry)
async def get_audit_log(log_id: str) -> AuditEntry:
    """
    Get a specific audit entry by ID.
    """
    entry = _find_entry(log_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Audit entry not found: {log_id}")
    return AuditEntry(**entry)
