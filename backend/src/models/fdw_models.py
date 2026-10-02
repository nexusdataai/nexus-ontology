"""
Pydantic models for FDW request and response payloads.

Defines data models for foreign server/table discovery, query requests/responses,
health checks, and filter operations. All models use camelCase aliases for
JSON serialization consistent with existing API conventions.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7**
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ForeignServerInfo(BaseModel):
    """Foreign server metadata from pg_foreign_server."""

    server_name: str = Field(..., alias="serverName")
    wrapper_type: str = Field(..., alias="wrapperType")
    server_options: dict = Field(default_factory=dict, alias="serverOptions")

    class Config:
        populate_by_name = True


class ForeignTableInfo(BaseModel):
    """Foreign table metadata from information_schema."""

    schema_name: str = Field(..., alias="schemaName")
    table_name: str = Field(..., alias="tableName")
    server_name: str = Field(..., alias="serverName")
    column_count: int = Field(..., alias="columnCount")

    class Config:
        populate_by_name = True


class ColumnInfo(BaseModel):
    """Column metadata for a foreign table."""

    column_name: str = Field(..., alias="columnName")
    data_type: str = Field(..., alias="dataType")
    is_nullable: bool = Field(..., alias="isNullable")
    ordinal_position: int = Field(..., alias="ordinalPosition")

    class Config:
        populate_by_name = True


class FilterOperator(str, Enum):
    """Supported filter operators for FDW queries."""

    eq = "eq"
    neq = "neq"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    like = "like"
    in_ = "in"


class QueryFilter(BaseModel):
    """A single filter condition for a query."""

    column: str
    operator: FilterOperator
    value: Any

    class Config:
        populate_by_name = True


class OrderByItem(BaseModel):
    """A single ordering directive for a query."""

    column: str
    direction: str = Field(default="asc", pattern="^(asc|desc)$")

    class Config:
        populate_by_name = True


class QueryRequest(BaseModel):
    """Request body for POST /api/fdw/query."""

    table: str
    schema_name: str = Field(default="public", alias="schemaName")
    filters: Optional[List[QueryFilter]] = None
    columns: Optional[List[str]] = None
    limit: Optional[int] = Field(default=None, ge=1, le=10000)
    offset: Optional[int] = Field(default=None, ge=0)
    order_by: Optional[List[OrderByItem]] = Field(default=None, alias="orderBy")

    class Config:
        populate_by_name = True


class QueryMetadata(BaseModel):
    """Metadata about a query execution."""

    duration_ms: float = Field(..., alias="durationMs")
    table_queried: str = Field(..., alias="tableQueried")
    row_count: int = Field(..., alias="rowCount")

    class Config:
        populate_by_name = True


class QueryResponse(BaseModel):
    """Response for POST /api/fdw/query."""

    rows: List[dict]
    metadata: QueryMetadata

    class Config:
        populate_by_name = True


class FDWHealthResponse(BaseModel):
    """Response for GET /health/fdw."""

    status: str
    latency_ms: Optional[float] = Field(default=None, alias="latencyMs")
    foreign_servers_count: Optional[int] = Field(default=None, alias="foreignServersCount")
    foreign_tables_count: Optional[int] = Field(default=None, alias="foreignTablesCount")
    error: Optional[str] = None

    class Config:
        populate_by_name = True
