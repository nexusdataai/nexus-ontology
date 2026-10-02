"""
Tools API

REST API endpoints for tool management.
Provides CRUD operations and test execution for registered tools.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="", tags=["tools"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (string, number, object, etc.)")
    required: bool = Field(default=False, description="Whether the parameter is required")


class Tool(BaseModel):
    """Tool representation."""
    id: str = Field(..., description="Tool identifier")
    name: str = Field(..., description="Tool display name")
    description: str = Field(..., description="Tool description")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    category: str = Field(..., description="Tool category")
    usage_count: int = Field(default=0, description="Number of times the tool has been used")


class ToolCreateRequest(BaseModel):
    """Request body for creating a tool."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: List[ToolParameter] = Field(default_factory=list, description="Tool parameters")
    implementation: Optional[str] = Field(None, description="Tool implementation (e.g., handler reference)")


class ToolUpdateRequest(BaseModel):
    """Request body for updating a tool."""
    name: Optional[str] = Field(None, description="Tool name")
    description: Optional[str] = Field(None, description="Tool description")
    parameters: Optional[List[ToolParameter]] = Field(None, description="Tool parameters")
    implementation: Optional[str] = Field(None, description="Tool implementation")


class ToolTestRequest(BaseModel):
    """Request body for testing a tool."""
    test_args: Dict[str, Any] = Field(default_factory=dict, description="Test arguments for tool execution")


class ToolTestResponse(BaseModel):
    """Response from tool test execution."""
    success: bool = Field(..., description="Whether the test succeeded")
    result: Any = Field(..., description="Mock result from tool execution")
    tool_id: str = Field(..., description="Tool that was executed")


# =============================================================================
# Hardcoded Sample Tools
# =============================================================================

SAMPLE_TOOLS: List[Dict[str, Any]] = [
    {
        "id": "get_account",
        "name": "Get Account",
        "description": "Retrieve account details from CRM",
        "parameters": [
            {"name": "account_id", "type": "string", "required": True},
            {"name": "fields", "type": "string", "required": False}
        ],
        "category": "crm",
        "usage_count": 1247
    },
    {
        "id": "get_ar_balance",
        "name": "Get AR Balance",
        "description": "Retrieve accounts receivable balance for a customer",
        "parameters": [
            {"name": "customer_id", "type": "string", "required": True}
        ],
        "category": "finance",
        "usage_count": 892
    },
    {
        "id": "propose_credit_change",
        "name": "Propose Credit Change",
        "description": "Propose a credit limit change for an account",
        "parameters": [
            {"name": "account_id", "type": "string", "required": True},
            {"name": "new_limit", "type": "number", "required": True},
            {"name": "justification", "type": "string", "required": True}
        ],
        "category": "finance",
        "usage_count": 156
    },
    {
        "id": "create_customer",
        "name": "Create Customer",
        "description": "Create a new customer record in CRM",
        "parameters": [
            {"name": "name", "type": "string", "required": True},
            {"name": "account_type", "type": "string", "required": True}
        ],
        "category": "crm",
        "usage_count": 423
    },
    {
        "id": "trigger_workflow",
        "name": "Trigger Workflow",
        "description": "Trigger an automation workflow",
        "parameters": [
            {"name": "workflow_id", "type": "string", "required": True},
            {"name": "trigger_data", "type": "object", "required": True}
        ],
        "category": "automation",
        "usage_count": 534
    },
    {
        "id": "search_enterprise_knowledge",
        "name": "Search Enterprise Knowledge",
        "description": "Search RAG-indexed enterprise knowledge base",
        "parameters": [
            {"name": "query", "type": "string", "required": True},
            {"name": "top_k", "type": "integer", "required": False}
        ],
        "category": "rag",
        "usage_count": 2103
    }
]


def _get_tools() -> List[Dict[str, Any]]:
    """Return copy of sample tools (in-memory only; mutations not persisted)."""
    return [dict(t) for t in SAMPLE_TOOLS]


def _find_tool(tool_id: str) -> Optional[Dict[str, Any]]:
    """Find a tool by ID."""
    for t in SAMPLE_TOOLS:
        if t["id"] == tool_id:
            return dict(t)
    return None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=List[Tool])
async def list_tools() -> List[Tool]:
    """
    List all registered tools.
    
    Returns tools with id, name, description, parameters, category, and usage_count.
    """
    tools = _get_tools()
    return [Tool(**t) for t in tools]


@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: str) -> Tool:
    """
    Get a specific tool by ID.
    """
    tool = _find_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    return Tool(**tool)


@router.post("/", response_model=Tool)
async def create_tool(request: ToolCreateRequest) -> Tool:
    """
    Create a new tool.
    
    Accepts name, description, parameters, and implementation.
    """
    tool_id = request.name.lower().replace(" ", "_").replace("-", "_")
    existing = _find_tool(tool_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Tool with id '{tool_id}' already exists")
    
    tool = Tool(
        id=tool_id,
        name=request.name,
        description=request.description,
        parameters=[ToolParameter(**p) for p in request.parameters],
        category="custom",
        usage_count=0
    )
    return tool


@router.put("/{tool_id}", response_model=Tool)
async def update_tool(tool_id: str, request: ToolUpdateRequest) -> Tool:
    """
    Update an existing tool.
    """
    tool = _find_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    updated = dict(tool)
    if request.name is not None:
        updated["name"] = request.name
    if request.description is not None:
        updated["description"] = request.description
    if request.parameters is not None:
        updated["parameters"] = [p.model_dump() for p in request.parameters]
    
    return Tool(**updated)


@router.delete("/{tool_id}")
async def delete_tool(tool_id: str) -> Dict[str, Any]:
    """
    Delete a tool.
    """
    tool = _find_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    return {"success": True, "deleted_id": tool_id}


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(tool_id: str, request: ToolTestRequest) -> ToolTestResponse:
    """
    Test execute a tool with provided arguments.
    
    Returns a mock result. Does not perform actual execution.
    """
    tool = _find_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_id}")
    
    mock_result = {
        "status": "success",
        "tool_id": tool_id,
        "args_received": request.test_args,
        "message": f"Mock execution of {tool_id} completed"
    }
    return ToolTestResponse(success=True, result=mock_result, tool_id=tool_id)
