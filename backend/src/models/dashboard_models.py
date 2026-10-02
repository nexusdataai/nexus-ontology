"""
Dashboard Builder Pydantic Models

Data models for dashboard CRUD, batch query execution, and entity metadata.
All models use camelCase aliases for JSON serialization.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GridPos(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 12
    h: int = 8


class DataSourceRef(BaseModel):
    type: str = "vdl"
    uid: str = "vdl-default"


class QueryFilter(BaseModel):
    field: str
    operator: str = "eq"
    value: Any


class AggregationSpec(BaseModel):
    function: str = Field(alias="function")
    field: Optional[str] = None

    class Config:
        populate_by_name = True


class PanelQueryModel(BaseModel):
    ref_id: str = Field(alias="refId")
    entity: str
    fields: Optional[List[str]] = None
    filters: Optional[List[QueryFilter]] = None
    aggregation: Optional[AggregationSpec] = None
    group_by: Optional[List[str]] = Field(default=None, alias="groupBy")
    order_by: Optional[str] = Field(default=None, alias="orderBy")
    limit: Optional[int] = 100
    hide: bool = False

    class Config:
        populate_by_name = True


class FieldConfigModel(BaseModel):
    defaults: Optional[Dict[str, Any]] = None
    overrides: Optional[List[Dict[str, Any]]] = None


class TransformConfig(BaseModel):
    id: str
    options: Dict[str, Any] = Field(default_factory=dict)


class PanelModelPayload(BaseModel):
    id: int
    type: str
    title: str = "Panel Title"
    description: Optional[str] = None
    grid_pos: GridPos = Field(default_factory=GridPos, alias="gridPos")
    datasource: DataSourceRef = Field(default_factory=DataSourceRef)
    targets: List[PanelQueryModel] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    field_config: Optional[FieldConfigModel] = Field(default=None, alias="fieldConfig")
    transformations: Optional[List[TransformConfig]] = None
    transparent: bool = False

    class Config:
        populate_by_name = True


class VariableModel(BaseModel):
    name: str
    label: Optional[str] = None
    type: str = "custom"
    query: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None
    current: Optional[Dict[str, str]] = None
    multi: bool = False
    include_all: bool = Field(default=False, alias="includeAll")

    class Config:
        populate_by_name = True


class TimeRangeModel(BaseModel):
    from_time: str = Field(alias="from", default="now-6h")
    to_time: str = Field(alias="to", default="now")

    class Config:
        populate_by_name = True


class DashboardPayload(BaseModel):
    uid: Optional[str] = None
    title: str = "New Dashboard"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    panels: List[PanelModelPayload] = Field(default_factory=list)
    time: TimeRangeModel = Field(default_factory=TimeRangeModel)
    refresh: Optional[str] = None
    variables: List[VariableModel] = Field(default_factory=list)
    version: int = 0

    class Config:
        populate_by_name = True


class DashboardResponse(BaseModel):
    uid: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    panels: List[Dict[str, Any]] = Field(default_factory=list)
    time: Dict[str, str] = Field(default_factory=dict)
    refresh: Optional[str] = None
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    version: int = 0
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")

    class Config:
        populate_by_name = True


class DashboardListItem(BaseModel):
    uid: str
    title: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    panel_count: int = Field(alias="panelCount", default=0)
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")

    class Config:
        populate_by_name = True


# --- Batch Query Models ---

class BatchPanelQuery(BaseModel):
    ref_id: str = Field(alias="ref_id")
    entity: str
    fields: Optional[List[str]] = None
    filters: Optional[List[QueryFilter]] = None
    aggregation: Optional[AggregationSpec] = None
    group_by: Optional[List[str]] = None
    order_by: Optional[str] = None
    limit: int = 100

    class Config:
        populate_by_name = True


class BatchQueryRequest(BaseModel):
    queries: List[BatchPanelQuery]
    time_range: Optional[TimeRangeModel] = None

    class Config:
        populate_by_name = True


class BatchQueryResultItem(BaseModel):
    ref_id: str
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    source: str = "unknown"
    error: Optional[str] = None


class BatchQueryResponse(BaseModel):
    results: Dict[str, BatchQueryResultItem] = Field(default_factory=dict)


# --- Entity Metadata Models ---

class FieldDescriptor(BaseModel):
    name: str
    type: str = "string"
    sample_values: Optional[List[Any]] = Field(default=None, alias="sampleValues")

    class Config:
        populate_by_name = True


class EntityFieldsResponse(BaseModel):
    entity: str
    fields: List[FieldDescriptor]
