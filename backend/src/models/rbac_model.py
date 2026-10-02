"""
RBAC (Role-Based Access Control) Models

Pydantic models for RBAC configuration including roles, permissions,
categories, and role-permission mappings.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    """Permission risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataScope(str, Enum):
    """Data access scope levels"""
    INDIVIDUAL = "individual"
    TEAM = "team"
    ORGANIZATION = "organization"


class RBACRole(BaseModel):
    """Role definition in RBAC system"""
    id: str = Field(..., description="Unique role identifier")
    name: str = Field(..., description="Role name (used in code)")
    displayName: str = Field(..., description="Human-readable role name")
    description: str = Field(..., description="Role description")
    level: int = Field(..., description="Role hierarchy level (1=highest)")
    badgeColor: Optional[str] = Field(None, description="CSS classes for badge styling")


class RBACCategory(BaseModel):
    """Permission category grouping"""
    id: str = Field(..., description="Category identifier")
    name: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    icon: Optional[str] = Field(None, description="Icon for category")
    order: int = Field(1, description="Display order")


class RBACPermission(BaseModel):
    """Individual permission definition"""
    id: str = Field(..., description="Permission identifier (snake_case)")
    name: str = Field(..., description="Permission name (UPPER_SNAKE_CASE)")
    displayName: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Permission description")
    category: str = Field(..., description="Category ID this permission belongs to")
    riskLevel: RiskLevel = Field(RiskLevel.LOW, description="Risk level of this permission")
    dataScope: DataScope = Field(DataScope.INDIVIDUAL, description="Data scope this permission grants")


class RBACMetadata(BaseModel):
    """RBAC configuration metadata"""
    version: str = Field("1.0.0", description="Configuration version")
    lastUpdated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    description: str = Field("", description="Configuration description")
    updatedBy: str = Field("system", description="User who last updated")
    environment: str = Field("development", description="Environment name")


class RBACAuditEntry(BaseModel):
    """Audit log entry for RBAC changes"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: str = Field(..., description="Action performed (CREATE, UPDATE, DELETE)")
    userId: str = Field(..., description="User who performed the action")
    roleId: Optional[str] = Field(None, description="Role affected")
    permissionId: Optional[str] = Field(None, description="Permission affected")
    changes: str = Field(..., description="Description of changes")
    previousValue: Optional[Dict[str, Any]] = Field(None, description="Previous state")
    newValue: Optional[Dict[str, Any]] = Field(None, description="New state")
    version: str = Field("1.0.0", description="Config version at time of change")


class RBACConfig(BaseModel):
    """Complete RBAC configuration"""
    metadata: RBACMetadata = Field(default_factory=RBACMetadata)
    roles: List[RBACRole] = Field(default_factory=list)
    transactionCategories: List[RBACCategory] = Field(default_factory=list)
    permissions: List[RBACPermission] = Field(default_factory=list)
    rolePermissions: Dict[str, List[str]] = Field(default_factory=dict)
    auditLog: List[RBACAuditEntry] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" if v else None
        }


# Request/Response Models for API

class UpdateRolePermissionsRequest(BaseModel):
    """Request to update permissions for a role"""
    permissions: List[str] = Field(..., description="List of permission IDs to assign")


class UpdateRolePermissionsResponse(BaseModel):
    """Response after updating role permissions"""
    success: bool
    message: str
    roleId: str
    permissions: List[str]
    updatedAt: datetime


class RBACConfigResponse(BaseModel):
    """API response for RBAC configuration"""
    status: str = "success"
    data: RBACConfig
    message: str = "RBAC configuration retrieved"


class RolesListResponse(BaseModel):
    """API response for roles list"""
    status: str = "success"
    data: List[RBACRole]
    count: int


class PermissionsListResponse(BaseModel):
    """API response for permissions list"""
    status: str = "success"
    data: List[RBACPermission]
    count: int


class AuditLogResponse(BaseModel):
    """API response for audit log"""
    status: str = "success"
    data: List[RBACAuditEntry]
    count: int


# Default RBAC Configuration
DEFAULT_RBAC_CONFIG = {
    "metadata": {
        "version": "1.0.0",
        "lastUpdated": "2024-01-20T00:00:00Z",
        "description": "Role-Based Access Control (RBAC) Configuration for Nexus Telco QA Dashboard",
        "updatedBy": "system",
        "environment": "development"
    },
    "roles": [
        {
            "id": "Admin",
            "name": "Admin",
            "displayName": "Administrator",
            "description": "System administrators with full access to all features",
            "level": 0,
            "badgeColor": "bg-red-100 text-red-800 border-red-200"
        },
        {
            "id": "Executive",
            "name": "Executive",
            "displayName": "Executive",
            "description": "Senior leadership with company-wide access",
            "level": 1,
            "badgeColor": "bg-purple-100 text-purple-800 border-purple-200"
        },
        {
            "id": "SalesManager",
            "name": "SalesManager",
            "displayName": "Sales Manager",
            "description": "Team leaders with team-level access and management capabilities",
            "level": 2,
            "badgeColor": "bg-blue-100 text-blue-800 border-blue-200"
        },
        {
            "id": "Rep",
            "name": "Rep",
            "displayName": "Sales Representative",
            "description": "Individual contributors with personal data access",
            "level": 3,
            "badgeColor": "bg-green-100 text-green-800 border-green-200"
        }
    ],
    "transactionCategories": [
        {"id": "dashboard_access", "name": "Dashboard Access", "description": "Access to various dashboard views and analytics", "icon": "📊", "order": 1},
        {"id": "call_analysis", "name": "Call Analysis Access", "description": "Access to call recordings and analysis tools", "icon": "🎧", "order": 2},
        {"id": "data_export", "name": "Data Export Operations", "description": "Export capabilities for reports and data", "icon": "📁", "order": 3},
        {"id": "administrative", "name": "Administrative Functions", "description": "User management and system administration", "icon": "⚙️", "order": 4},
        {"id": "ai_analytics", "name": "AI & Analytics Tools", "description": "Access to AI-powered analysis and enhancement tools", "icon": "🤖", "order": 5},
        {"id": "tools_access", "name": "Tools Catalogue Access", "description": "Access to various tools in the catalogue by category", "icon": "🔧", "order": 6},
        {"id": "feature_access", "name": "Feature Access", "description": "Access to platform features and tools", "icon": "🧩", "order": 7}
    ],
    "permissions": [
        {"id": "view_executive_dashboard", "name": "VIEW_EXECUTIVE_DASHBOARD", "displayName": "View Executive Dashboard", "description": "Company-wide analytics & insights", "category": "dashboard_access", "riskLevel": "high", "dataScope": "organization"},
        {"id": "view_team_dashboard", "name": "VIEW_TEAM_DASHBOARD", "displayName": "View Team Dashboard", "description": "Team performance & metrics", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_individual_dashboard", "name": "VIEW_INDIVIDUAL_DASHBOARD", "displayName": "View Individual Dashboard", "description": "Personal performance metrics", "category": "dashboard_access", "riskLevel": "low", "dataScope": "individual"},
        {"id": "view_call_analysis", "name": "VIEW_CALL_ANALYSIS", "displayName": "View Call Analysis", "description": "Call analysis dashboard with detailed call insights", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_rep_performance", "name": "VIEW_REP_PERFORMANCE", "displayName": "View Rep Performance", "description": "Sales representative performance metrics and analytics", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_deal_analysis", "name": "VIEW_DEAL_ANALYSIS", "displayName": "View Deal Analysis", "description": "Deal pipeline analysis and conversion metrics", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_email_analysis", "name": "VIEW_EMAIL_ANALYSIS", "displayName": "View Email Analysis", "description": "Email communication analytics and insights", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_reports", "name": "VIEW_REPORTS", "displayName": "View Reports", "description": "Report viewer dashboard for generated reports", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_lead_failures", "name": "VIEW_LEAD_FAILURES", "displayName": "View Lead Failures", "description": "Lead creation failure report and diagnostics", "category": "dashboard_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "access_tools_catalogue", "name": "ACCESS_TOOLS_CATALOGUE", "displayName": "Access Tools Catalogue", "description": "Access to the Totogi Tools Catalogue", "category": "feature_access", "riskLevel": "low", "dataScope": "individual"},
        {"id": "access_ai_workspace", "name": "ACCESS_AI_WORKSPACE", "displayName": "Access AI Workspace", "description": "Access to the AI Workspace for agent configuration and chatbot editing", "category": "feature_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "access_operations", "name": "ACCESS_OPERATIONS", "displayName": "Access Operations", "description": "Access to the Operations management page", "category": "feature_access", "riskLevel": "high", "dataScope": "organization"},
        {"id": "view_all_calls", "name": "VIEW_ALL_CALLS", "displayName": "View All Calls", "description": "Access to entire organization's calls", "category": "call_analysis", "riskLevel": "high", "dataScope": "organization"},
        {"id": "view_team_calls", "name": "VIEW_TEAM_CALLS", "displayName": "View Team Calls", "description": "Access to team members' calls", "category": "call_analysis", "riskLevel": "medium", "dataScope": "team"},
        {"id": "view_own_calls", "name": "VIEW_OWN_CALLS", "displayName": "View Own Calls", "description": "Access to personal call recordings", "category": "call_analysis", "riskLevel": "low", "dataScope": "individual"},
        {"id": "export_all_data", "name": "EXPORT_ALL_DATA", "displayName": "Export All Data", "description": "Export company-wide data & reports", "category": "data_export", "riskLevel": "high", "dataScope": "organization"},
        {"id": "export_team_data", "name": "EXPORT_TEAM_DATA", "displayName": "Export Team Data", "description": "Export team performance data", "category": "data_export", "riskLevel": "medium", "dataScope": "team"},
        {"id": "export_own_data", "name": "EXPORT_OWN_DATA", "displayName": "Export Own Data", "description": "Export personal performance data", "category": "data_export", "riskLevel": "low", "dataScope": "individual"},
        {"id": "manage_users", "name": "MANAGE_USERS", "displayName": "Manage Users", "description": "Create, modify, delete user accounts", "category": "administrative", "riskLevel": "critical", "dataScope": "organization"},
        {"id": "manage_team", "name": "MANAGE_TEAM", "displayName": "Manage Team", "description": "Add/remove team members, assign roles", "category": "administrative", "riskLevel": "high", "dataScope": "team"},
        {"id": "manage_system", "name": "MANAGE_SYSTEM", "displayName": "Manage System", "description": "System configuration and settings", "category": "administrative", "riskLevel": "critical", "dataScope": "organization"},
        {"id": "manage_rbac", "name": "MANAGE_RBAC", "displayName": "Manage RBAC", "description": "Manage roles and permissions", "category": "administrative", "riskLevel": "critical", "dataScope": "organization"},
        {"id": "view_compliance", "name": "VIEW_COMPLIANCE", "displayName": "View Compliance", "description": "Access compliance reports & audits", "category": "administrative", "riskLevel": "medium", "dataScope": "team"},
        {"id": "access_ai_tools", "name": "ACCESS_AI_TOOLS", "displayName": "Access AI Tools", "description": "Use AI-powered analysis features", "category": "ai_analytics", "riskLevel": "low", "dataScope": "individual"},
        {"id": "access_analysis_tools", "name": "ACCESS_ANALYSIS_TOOLS", "displayName": "Access Analysis Tools", "description": "Use call analysis and customer segmentation tools", "category": "tools_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "access_enhancement_tools", "name": "ACCESS_ENHANCEMENT_TOOLS", "displayName": "Access Enhancement Tools", "description": "Use performance optimization and data enhancement tools", "category": "tools_access", "riskLevel": "medium", "dataScope": "team"},
        {"id": "access_integration_tools", "name": "ACCESS_INTEGRATION_TOOLS", "displayName": "Access Integration Tools", "description": "Use system integration tools and connectors", "category": "tools_access", "riskLevel": "high", "dataScope": "organization"},
        {"id": "access_knowledge_base", "name": "ACCESS_KNOWLEDGE_BASE", "displayName": "Access Knowledge Base", "description": "Use knowledge base tool for document search and AI assistance", "category": "tools_access", "riskLevel": "low", "dataScope": "individual"}
    ],
    "rolePermissions": {
        "Admin": [
            "view_executive_dashboard", "view_team_dashboard", "view_individual_dashboard",
            "view_call_analysis", "view_rep_performance", "view_deal_analysis",
            "view_email_analysis", "view_reports", "view_lead_failures",
            "view_all_calls", "view_team_calls", "view_own_calls",
            "export_all_data", "export_team_data", "export_own_data",
            "manage_users", "manage_team", "manage_system", "manage_rbac", "view_compliance",
            "access_ai_tools", "access_tools_catalogue", "access_ai_workspace", "access_operations",
            "access_analysis_tools", "access_enhancement_tools",
            "access_integration_tools", "access_knowledge_base"
        ],
        "Executive": [
            "view_executive_dashboard", "view_team_dashboard", "view_individual_dashboard",
            "view_call_analysis", "view_rep_performance", "view_deal_analysis",
            "view_email_analysis", "view_reports", "view_lead_failures",
            "view_all_calls", "export_all_data", "manage_users", "view_compliance",
            "access_ai_tools", "access_tools_catalogue", "access_ai_workspace", "access_operations",
            "access_analysis_tools", "access_enhancement_tools",
            "access_integration_tools", "access_knowledge_base"
        ],
        "SalesManager": [
            "view_team_dashboard", "view_individual_dashboard",
            "view_call_analysis", "view_rep_performance", "view_deal_analysis",
            "view_email_analysis", "view_reports", "view_lead_failures",
            "view_team_calls", "view_own_calls", "export_team_data",
            "manage_team", "view_compliance",
            "access_ai_tools", "access_tools_catalogue", "access_ai_workspace",
            "access_analysis_tools", "access_enhancement_tools",
            "access_knowledge_base"
        ],
        "Rep": [
            "view_individual_dashboard", "view_own_calls", "export_own_data",
            "access_ai_tools", "access_tools_catalogue", "access_knowledge_base"
        ]
    },
    "auditLog": [
        {
            "timestamp": "2024-01-20T00:00:00Z",
            "action": "INITIAL_SETUP",
            "userId": "system",
            "changes": "Initial RBAC configuration created",
            "version": "1.0.0"
        }
    ]
}
