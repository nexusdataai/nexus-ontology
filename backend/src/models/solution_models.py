"""
Solution Pydantic Models

Solutions are top-level workspace containers. Each Solution holds an ordered
collection of Views that are surfaced as menu entries in the AppSidebar.
A Solution may optionally be linked to a frontend appRegistry entry via appId.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SolutionPayload(BaseModel):
    """Create/update payload for a Solution."""
    solution_id: Optional[str] = Field(default=None, alias="solutionId")
    name: str = "New Solution"
    description: Optional[str] = None
    app_id: Optional[str] = Field(default=None, alias="appId")
    icon: Optional[str] = None
    version: int = 0

    class Config:
        populate_by_name = True


class SolutionViewLinkResponse(BaseModel):
    """A View as it appears within a Solution's ordered list."""
    view_id: str = Field(alias="viewId")
    order: int = 0
    name: Optional[str] = None
    display_name: Optional[str] = Field(default=None, alias="displayName")

    class Config:
        populate_by_name = True


class SolutionResponse(BaseModel):
    """Full Solution detail including ordered views."""
    solution_id: str = Field(alias="solutionId")
    name: str
    description: Optional[str] = None
    app_id: Optional[str] = Field(default=None, alias="appId")
    icon: Optional[str] = None
    version: int = 0
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")
    views: List[SolutionViewLinkResponse] = Field(default_factory=list)

    class Config:
        populate_by_name = True


class SolutionSummary(BaseModel):
    """Lightweight Solution row for listing."""
    solution_id: str = Field(alias="solutionId")
    name: str
    description: Optional[str] = None
    app_id: Optional[str] = Field(default=None, alias="appId")
    icon: Optional[str] = None
    view_count: int = Field(alias="viewCount", default=0)
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")
    created_by: str = Field(alias="createdBy", default="")

    class Config:
        populate_by_name = True


class AddViewRequest(BaseModel):
    view_id: str = Field(alias="viewId")
    position: Optional[int] = None
    display_name: Optional[str] = Field(default=None, alias="displayName")

    class Config:
        populate_by_name = True


class ReorderViewsRequest(BaseModel):
    view_ids: List[str] = Field(alias="viewIds")

    class Config:
        populate_by_name = True
