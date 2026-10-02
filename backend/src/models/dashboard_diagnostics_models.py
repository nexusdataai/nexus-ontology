"""
Pydantic models for the Dashboard Diagnostics API.

The diagnostic runs each panel target through the live VDL stack and grades
the result against a fixed checklist. See
``services/dashboard_diagnostics_service.py`` for the runner and
``apis/dashboard_diagnostics_api.py`` for the HTTP surface.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CheckLevel(str, Enum):
    """Status pill returned per panel and rolled up per dashboard."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class OverallLevel(str, Enum):
    """Roll-up of CheckLevel across all panels of a dashboard / scan."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class PanelCheckCode(str, Enum):
    """
    Diagnostic outcome code per panel target. ``ok`` is the only PASS;
    every other code is a WARN or FAIL.
    """

    OK = "ok"
    NO_MAPPING_RULE = "no_mapping_rule"
    INACTIVE_RULE = "inactive_rule"
    BACKEND_UNREACHABLE = "backend_unreachable"
    QUERY_ERROR = "query_error"
    NO_ROWS = "no_rows"
    MISSING_COLUMNS = "missing_columns"
    NULL_GROUP_KEYS = "null_group_keys"
    SLOW_QUERY = "slow_query"


CODE_TO_LEVEL: Dict[PanelCheckCode, CheckLevel] = {
    PanelCheckCode.OK: CheckLevel.PASS,
    PanelCheckCode.NO_MAPPING_RULE: CheckLevel.FAIL,
    PanelCheckCode.INACTIVE_RULE: CheckLevel.FAIL,
    PanelCheckCode.BACKEND_UNREACHABLE: CheckLevel.FAIL,
    PanelCheckCode.QUERY_ERROR: CheckLevel.FAIL,
    PanelCheckCode.NO_ROWS: CheckLevel.WARN,
    PanelCheckCode.MISSING_COLUMNS: CheckLevel.WARN,
    PanelCheckCode.NULL_GROUP_KEYS: CheckLevel.WARN,
    PanelCheckCode.SLOW_QUERY: CheckLevel.WARN,
}


class PanelDiagnostic(BaseModel):
    """One panel target, one verdict."""

    panel_id: int = Field(..., alias="panelId")
    panel_title: str = Field(..., alias="panelTitle")
    panel_type: str = Field(..., alias="panelType")
    target_ref_id: str = Field(default="A", alias="targetRefId")
    entity: str
    source_type: Optional[str] = Field(default=None, alias="sourceType")
    rule_id: Optional[str] = Field(default=None, alias="ruleId")

    status: CheckLevel
    code: PanelCheckCode

    latency_ms: Optional[int] = Field(default=None, alias="latencyMs")
    row_count: Optional[int] = Field(default=None, alias="rowCount")
    expected_fields: List[str] = Field(default_factory=list, alias="expectedFields")
    returned_fields: List[str] = Field(default_factory=list, alias="returnedFields")
    missing_fields: List[str] = Field(default_factory=list, alias="missingFields")
    null_group_columns: List[str] = Field(default_factory=list, alias="nullGroupColumns")

    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    suggestion: Optional[str] = None

    query_payload: Dict[str, Any] = Field(default_factory=dict, alias="queryPayload")

    class Config:
        populate_by_name = True
        use_enum_values = True


class DashboardDiagnostic(BaseModel):
    """All panels of one dashboard plus a roll-up status."""

    uid: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    status: OverallLevel
    panel_count: int = Field(..., alias="panelCount")
    healthy_count: int = Field(default=0, alias="healthyCount")
    degraded_count: int = Field(default=0, alias="degradedCount")
    unhealthy_count: int = Field(default=0, alias="unhealthyCount")

    panels: List[PanelDiagnostic] = Field(default_factory=list)

    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class DashboardIndexEntry(BaseModel):
    """Light row used by the listing endpoint - no diagnostic run."""

    uid: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    panel_count: int = Field(default=0, alias="panelCount")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")

    class Config:
        populate_by_name = True


class ScanResult(BaseModel):
    """Aggregate result of run-all."""

    total: int
    healthy: int
    degraded: int
    unhealthy: int
    dashboards: List[DashboardDiagnostic] = Field(default_factory=list)
    duration_ms: int = Field(default=0, alias="durationMs")
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class BackendDiagnostic(BaseModel):
    """One VDL backend health snapshot."""

    name: str
    kind: str
    status: CheckLevel
    detail: Optional[str] = None
    latency_ms: Optional[int] = Field(default=None, alias="latencyMs")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        use_enum_values = True


class BackendsDiagnostic(BaseModel):
    """All known VDL backends checked once."""

    overall: OverallLevel
    backends: List[BackendDiagnostic] = Field(default_factory=list)
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class EntityDiagnostic(BaseModel):
    """Lower-level check for one virtual entity (sample query)."""

    entity: str
    status: CheckLevel
    code: PanelCheckCode
    rule_id: Optional[str] = Field(default=None, alias="ruleId")
    source_type: Optional[str] = Field(default=None, alias="sourceType")
    source_table: Optional[str] = Field(default=None, alias="sourceTable")
    row_count: Optional[int] = Field(default=None, alias="rowCount")
    sample_rows: List[Dict[str, Any]] = Field(default_factory=list, alias="sampleRows")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    latency_ms: Optional[int] = Field(default=None, alias="latencyMs")
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class RunOneRequest(BaseModel):
    limit_per_panel: int = Field(default=10, alias="limitPerPanel", ge=1, le=200)

    class Config:
        populate_by_name = True


class RunAllRequest(BaseModel):
    dashboard_uids: Optional[List[str]] = Field(default=None, alias="dashboardUids")
    limit_per_panel: int = Field(default=10, alias="limitPerPanel", ge=1, le=200)
    concurrency: int = Field(default=8, ge=1, le=32)

    class Config:
        populate_by_name = True
