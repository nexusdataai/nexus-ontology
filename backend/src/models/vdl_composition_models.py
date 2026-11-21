"""
Pydantic models for VDL entity compositions (multi-source runtime SQL bindings).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.mapping_rule_models import FieldMap, MappingRuleStatus


class VdlCompositionStrategy(str, Enum):
    runtime_sql = "runtime_sql"
    materialized_table = "materialized_table"
    promql = "promql"
    athena_select = "athena_select"


class CompositionSourceRef(BaseModel):
    alias: str
    source_system: str = Field(..., alias="sourceSystem")
    schema: str
    table: str

    class Config:
        populate_by_name = True


class CompositionJoin(BaseModel):
    left: str
    right: str
    type: str = "inner"
    on: str


class CompositionProjection(BaseModel):
    target_field: str = Field(..., alias="targetField")
    expr: str

    class Config:
        populate_by_name = True


class VdlCompositionUpsertRequest(BaseModel):
    virtual_entity: str = Field(..., alias="virtualEntity")
    name: Optional[str] = None
    status: MappingRuleStatus = MappingRuleStatus.draft
    strategy: VdlCompositionStrategy = VdlCompositionStrategy.runtime_sql
    sources: List[CompositionSourceRef] = Field(default_factory=list, alias="from")
    joins: List[CompositionJoin] = Field(default_factory=list)
    projections: List[CompositionProjection] = Field(default_factory=list, alias="select")
    field_maps: List[FieldMap] = Field(default_factory=list, alias="fieldMaps")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    business_logic: Optional[str] = Field(default=None, alias="businessLogic")

    class Config:
        populate_by_name = True


class VdlCompositionResponse(BaseModel):
    virtual_entity: str = Field(..., alias="virtualEntity")
    name: Optional[str] = None
    status: MappingRuleStatus
    strategy: VdlCompositionStrategy
    sources: List[CompositionSourceRef] = Field(default_factory=list, alias="from")
    joins: List[CompositionJoin] = Field(default_factory=list)
    projections: List[CompositionProjection] = Field(default_factory=list, alias="select")
    field_maps: List[FieldMap] = Field(default_factory=list, alias="fieldMaps")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    business_logic: Optional[str] = Field(default=None, alias="businessLogic")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True


class VdlCompositionValidateResponse(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    sql_preview: Optional[str] = Field(default=None, alias="sqlPreview")

    class Config:
        populate_by_name = True