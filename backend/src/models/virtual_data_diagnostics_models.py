"""
Pydantic models for the Virtual Data Diagnostics API.

The diagnostic walks every mapped virtual entity through the same
``VirtualQueryService.query_virtual_entity`` path that powers the Data
Plane > Virtual Data > Preview button, classifies every layer-by-layer
failure, and emits a one-line remediation per failed check.

See ``services/virtual_data_diagnostics_service.py`` for the runner and
``apis/virtual_data_diagnostics_api.py`` for the HTTP surface.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CheckLevel(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class OverallLevel(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class VirtualEntityCheck(BaseModel):
    """One discrete check inside the virtual-entity probe."""

    code: str
    status: CheckLevel
    message: str
    suggestion: Optional[str] = None
    detail: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        use_enum_values = True


class VirtualEntityDiagnostic(BaseModel):
    """All checks for one virtual entity, plus a roll-up status."""

    virtual_entity: str = Field(..., alias="virtualEntity")
    overall: OverallLevel

    source_type: Optional[str] = Field(default=None, alias="sourceType")
    source_system: Optional[str] = Field(default=None, alias="sourceSystem")
    source_schema: Optional[str] = Field(default=None, alias="sourceSchema")
    source_table: Optional[str] = Field(default=None, alias="sourceTable")
    rule_id: Optional[str] = Field(default=None, alias="ruleId")

    active_rule_count: int = Field(default=0, alias="activeRuleCount")
    total_rule_count: int = Field(default=0, alias="totalRuleCount")

    row_count: Optional[int] = Field(default=None, alias="rowCount")
    latency_ms: Optional[int] = Field(default=None, alias="latencyMs")

    checks: List[VirtualEntityCheck] = Field(default_factory=list)
    sample_row: Optional[Dict[str, Any]] = Field(default=None, alias="sampleRow")

    duration_ms: Optional[int] = Field(default=None, alias="durationMs")
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class VirtualEntityIndexEntry(BaseModel):
    """Light row used by the listing endpoint - no probe run."""

    virtual_entity: str = Field(..., alias="virtualEntity")
    total_rule_count: int = Field(default=0, alias="totalRuleCount")
    active_rule_count: int = Field(default=0, alias="activeRuleCount")
    source_systems: List[str] = Field(default_factory=list, alias="sourceSystems")
    source_schemas: List[str] = Field(default_factory=list, alias="sourceSchemas")

    class Config:
        populate_by_name = True


class ScanResult(BaseModel):
    """Aggregate result of run-all."""

    overall: OverallLevel
    total: int
    healthy: int
    degraded: int
    unhealthy: int
    entities: List[VirtualEntityDiagnostic] = Field(default_factory=list)
    duration_ms: int = Field(default=0, alias="durationMs")
    scanned_at: str = Field(..., alias="scannedAt")

    class Config:
        populate_by_name = True
        use_enum_values = True


class RunOneRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=100)

    class Config:
        populate_by_name = True


class RunAllRequest(BaseModel):
    entities: Optional[List[str]] = None
    limit: int = Field(default=5, ge=1, le=100)
    concurrency: int = Field(default=8, ge=1, le=32)

    class Config:
        populate_by_name = True
