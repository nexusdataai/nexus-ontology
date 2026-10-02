"""
Pydantic models for mapping rule request and response payloads.

Defines data models for virtual-entity mapping rules that translate between
source system fields and canonical virtual entity fields. Covers CRUD operations,
virtual query execution, and AI-powered mapping suggestions. All models use
camelCase aliases for JSON serialization consistent with existing API conventions.
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FieldMap(BaseModel):
    """A single field mapping from source to target."""

    source_field: str = Field(..., alias="sourceField")
    target_field: str = Field(..., alias="targetField")
    transform: Optional[str] = None
    default_value: Optional[str] = Field(default=None, alias="defaultValue")

    class Config:
        populate_by_name = True


class MappingRuleStatus(str, Enum):
    """Lifecycle status of a mapping rule."""

    draft = "draft"
    active = "active"
    inactive = "inactive"


class MappingRuleSourceType(str, Enum):
    """Source integration type for a mapping rule."""

    FDW = "FDW"
    ETL = "ETL"
    CDC = "CDC"
    ATHENA = "ATHENA"
    MIMIR = "MIMIR"


class MappingRuleCreateRequest(BaseModel):
    """Request body for creating a new mapping rule."""

    name: str
    virtual_entity: str = Field(..., alias="virtualEntity")
    source_type: MappingRuleSourceType = Field(..., alias="sourceType")
    source_system: str = Field(..., alias="sourceSystem")
    source_table: str = Field(..., alias="sourceTable")
    source_schema: str = Field(default="public", alias="sourceSchema")
    field_maps: List[FieldMap] = Field(..., alias="fieldMaps")
    business_logic: Optional[str] = Field(default=None, alias="businessLogic")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")

    class Config:
        populate_by_name = True


class MappingRuleUpdateRequest(BaseModel):
    """Request body for updating an existing mapping rule."""

    name: Optional[str] = None
    field_maps: Optional[List[FieldMap]] = Field(default=None, alias="fieldMaps")
    business_logic: Optional[str] = Field(default=None, alias="businessLogic")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    status: Optional[MappingRuleStatus] = None

    class Config:
        populate_by_name = True


class MappingRuleResponse(BaseModel):
    """Response model for a mapping rule."""

    id: str
    name: str
    virtual_entity: str = Field(..., alias="virtualEntity")
    source_type: MappingRuleSourceType = Field(..., alias="sourceType")
    source_system: str = Field(..., alias="sourceSystem")
    source_table: str = Field(..., alias="sourceTable")
    source_schema: str = Field(..., alias="sourceSchema")
    field_maps: List[FieldMap] = Field(..., alias="fieldMaps")
    business_logic: Optional[str] = Field(default=None, alias="businessLogic")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    status: MappingRuleStatus
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True


class VirtualFilter(BaseModel):
    """A single filter condition for a virtual query."""

    field: str
    operator: str = "eq"
    value: Any

    class Config:
        populate_by_name = True


class VirtualQueryRequest(BaseModel):
    """Request body for querying a virtual entity."""

    virtual_entity: str = Field(..., alias="virtualEntity")
    fields: Optional[List[str]] = None
    filters: Optional[List[VirtualFilter]] = None
    group_by: Optional[List[str]] = Field(default=None, alias="groupBy")
    aggregation: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)

    class Config:
        populate_by_name = True


class VirtualQueryResponse(BaseModel):
    """Response for a virtual entity query."""

    rows: List[dict]
    metadata: dict
    virtual_entity: str = Field(..., alias="virtualEntity")

    class Config:
        populate_by_name = True


class MappingSuggestionRequest(BaseModel):
    """Request body for AI-powered mapping suggestions."""

    virtual_entity: str = Field(..., alias="virtualEntity")
    source_schema: str = Field(..., alias="sourceSchema")
    source_table: str = Field(..., alias="sourceTable")

    class Config:
        populate_by_name = True


class AutoMapDetail(BaseModel):
    """Detail for a single entity in the auto-map response."""

    entity: str
    status: str  # "created", "skipped", "error"
    reason: Optional[str] = None

    class Config:
        populate_by_name = True


class AutoMapResponse(BaseModel):
    """Response for the bulk auto-map endpoint."""

    created: int = 0
    skipped: int = 0
    errors: int = 0
    details: List[AutoMapDetail] = Field(default_factory=list)

    class Config:
        populate_by_name = True
