"""
Pydantic models for Data Plane request and response payloads.

Defines data models for data plane configurations including enums for
data plane types (FDW, CDC, ETL) and statuses (connected, disconnected,
error, pending). All models use camelCase aliases for JSON serialization
consistent with existing API conventions.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DataPlaneType(str, Enum):
    """Integration mechanism type for a data plane."""

    FDW = "FDW"
    CDC = "CDC"
    ETL = "ETL"
    FILE_UPLOAD = "FILE_UPLOAD"
    CLOUD_DRIVE = "CLOUD_DRIVE"
    SOCIAL_LISTENING = "SOCIAL_LISTENING"
    RAW_API = "RAW_API"


class DataPlaneStatus(str, Enum):
    """Connection status of a data plane."""

    connected = "connected"
    disconnected = "disconnected"
    error = "error"
    pending = "pending"


class DataPlaneCreateRequest(BaseModel):
    """Request body for POST /api/data-planes."""

    name: str = Field(..., min_length=1)
    type: DataPlaneType
    connection_config: Dict[str, Any] = Field(..., alias="connectionConfig")

    class Config:
        populate_by_name = True


class DataPlaneUpdateRequest(BaseModel):
    """Request body for PUT /api/data-planes/{id}."""

    name: Optional[str] = Field(default=None, min_length=1)
    status: Optional[DataPlaneStatus] = None
    connection_config: Optional[Dict[str, Any]] = Field(default=None, alias="connectionConfig")

    class Config:
        populate_by_name = True


class DataPlaneResponse(BaseModel):
    """Response model for data plane records."""

    id: str
    name: str
    type: DataPlaneType
    status: DataPlaneStatus
    connection_config: Dict[str, Any] = Field(..., alias="connectionConfig")
    created_at: str = Field(..., alias="createdAt")
    updated_at: str = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
