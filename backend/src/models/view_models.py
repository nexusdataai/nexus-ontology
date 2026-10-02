"""
View Pydantic Models

A View is an ordered collection of Dashboard tabs. Each tab references a single
Dashboard by uid and may attach simulator dataset references (S3 keys) and a
time-range override.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SimulatorRef(BaseModel):
    """Reference to simulator data stored in S3."""
    service: str  # e.g. "wxcc", "sfdc", "oracle-erp", "sap"
    scenario: Optional[str] = None
    s3_key: Optional[str] = Field(default=None, alias="s3Key")

    class Config:
        populate_by_name = True


class ViewTabPayload(BaseModel):
    """Create/update payload for a tab inside a View."""
    tab_id: Optional[str] = Field(default=None, alias="tabId")
    label: str = "Tab"
    icon: Optional[str] = None
    dashboard_id: str = Field(alias="dashboardId")
    simulator_refs: List[SimulatorRef] = Field(default_factory=list, alias="simulatorRefs")
    time_override: Optional[dict] = Field(default=None, alias="timeOverride")
    position: Optional[int] = None

    class Config:
        populate_by_name = True


class ViewTabResponse(BaseModel):
    """A tab as it appears within a View's ordered list."""
    tab_id: str = Field(alias="tabId")
    order: int = 0
    label: str
    icon: Optional[str] = None
    dashboard_id: str = Field(alias="dashboardId")
    simulator_refs: List[SimulatorRef] = Field(default_factory=list, alias="simulatorRefs")
    time_override: Optional[dict] = Field(default=None, alias="timeOverride")

    class Config:
        populate_by_name = True


class ViewPayload(BaseModel):
    """Create/update payload for a View."""
    view_id: Optional[str] = Field(default=None, alias="viewId")
    name: str = "New View"
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    default_tab_id: Optional[str] = Field(default=None, alias="defaultTabId")
    version: int = 0

    class Config:
        populate_by_name = True


class ViewResponse(BaseModel):
    """Full View detail including ordered tabs."""
    view_id: str = Field(alias="viewId")
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    default_tab_id: Optional[str] = Field(default=None, alias="defaultTabId")
    version: int = 0
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")
    tabs: List[ViewTabResponse] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class ViewSummary(BaseModel):
    """Lightweight View row for listing."""
    view_id: str = Field(alias="viewId")
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    tab_count: int = Field(alias="tabCount", default=0)
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")

    class Config:
        populate_by_name = True


class ReorderTabsRequest(BaseModel):
    tab_ids: List[str] = Field(alias="tabIds")

    class Config:
        populate_by_name = True
