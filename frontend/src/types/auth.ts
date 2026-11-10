// Enterprise Authentication Types
export type UserRole = 'Admin' | 'Executive' | 'SalesManager' | 'Rep';
export type AuthMethod = 'ADFS' | 'COGNITO' | 'LOCAL';

export enum Permission {
  // Dashboard Access
  VIEW_EXECUTIVE_DASHBOARD = 'view_executive_dashboard',
  VIEW_TEAM_DASHBOARD = 'view_team_dashboard',
  VIEW_INDIVIDUAL_DASHBOARD = 'view_individual_dashboard',
  
  // Dashboard Feature Access
  VIEW_CALL_ANALYSIS = 'view_call_analysis',
  VIEW_REP_PERFORMANCE = 'view_rep_performance',
  VIEW_DEAL_ANALYSIS = 'view_deal_analysis',
  VIEW_EMAIL_ANALYSIS = 'view_email_analysis',
  VIEW_REPORTS = 'view_reports',
  VIEW_LEAD_FAILURES = 'view_lead_failures',
  
  // Call Analysis Access
  VIEW_ALL_CALLS = 'view_all_calls',
  VIEW_TEAM_CALLS = 'view_team_calls',
  VIEW_OWN_CALLS = 'view_own_calls',
  
  // Data Operations
  EXPORT_ALL_DATA = 'export_all_data',
  EXPORT_TEAM_DATA = 'export_team_data',
  EXPORT_OWN_DATA = 'export_own_data',
  
  // Administrative
  MANAGE_USERS = 'manage_users',
  MANAGE_TEAM = 'manage_team',
  MANAGE_SYSTEM = 'manage_system',
  MANAGE_RBAC = 'manage_rbac',
  INVITE_USERS = 'invite_users',
  VIEW_COMPLIANCE = 'view_compliance',
  ACCESS_AI_TOOLS = 'access_ai_tools',
  
  // Feature Access
  ACCESS_TOOLS_CATALOGUE = 'access_tools_catalogue',
  ACCESS_AI_WORKSPACE = 'access_ai_workspace',
  ACCESS_OPERATIONS = 'access_operations',
  
  // Tools Catalogue Access
  ACCESS_ANALYSIS_TOOLS = 'access_analysis_tools',
  ACCESS_ENHANCEMENT_TOOLS = 'access_enhancement_tools', 
  ACCESS_INTEGRATION_TOOLS = 'access_integration_tools',
  ACCESS_KNOWLEDGE_BASE = 'access_knowledge_base'
}

// Role-Permission Mapping
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  Admin: [
    Permission.VIEW_EXECUTIVE_DASHBOARD,
    Permission.VIEW_TEAM_DASHBOARD,
    Permission.VIEW_INDIVIDUAL_DASHBOARD,
    Permission.VIEW_CALL_ANALYSIS,
    Permission.VIEW_REP_PERFORMANCE,
    Permission.VIEW_DEAL_ANALYSIS,
    Permission.VIEW_EMAIL_ANALYSIS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_LEAD_FAILURES,
    Permission.VIEW_ALL_CALLS,
    Permission.VIEW_TEAM_CALLS,
    Permission.VIEW_OWN_CALLS,
    Permission.EXPORT_ALL_DATA,
    Permission.EXPORT_TEAM_DATA,
    Permission.EXPORT_OWN_DATA,
    Permission.MANAGE_USERS,
    Permission.MANAGE_TEAM,
    Permission.MANAGE_SYSTEM,
    Permission.INVITE_USERS,
    Permission.VIEW_COMPLIANCE,
    Permission.ACCESS_AI_TOOLS,
    Permission.ACCESS_TOOLS_CATALOGUE,
    Permission.ACCESS_AI_WORKSPACE,
    Permission.ACCESS_OPERATIONS,
    Permission.ACCESS_ANALYSIS_TOOLS,
    Permission.ACCESS_ENHANCEMENT_TOOLS,
    Permission.ACCESS_INTEGRATION_TOOLS,
    Permission.ACCESS_KNOWLEDGE_BASE
  ],

  Executive: [
    Permission.VIEW_EXECUTIVE_DASHBOARD,
    Permission.VIEW_TEAM_DASHBOARD,
    Permission.VIEW_INDIVIDUAL_DASHBOARD,
    Permission.VIEW_CALL_ANALYSIS,
    Permission.VIEW_REP_PERFORMANCE,
    Permission.VIEW_DEAL_ANALYSIS,
    Permission.VIEW_EMAIL_ANALYSIS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_LEAD_FAILURES,
    Permission.VIEW_ALL_CALLS,
    Permission.EXPORT_ALL_DATA,
    Permission.MANAGE_USERS,
    Permission.VIEW_COMPLIANCE,
    Permission.ACCESS_AI_TOOLS,
    Permission.ACCESS_TOOLS_CATALOGUE,
    Permission.ACCESS_AI_WORKSPACE,
    Permission.ACCESS_OPERATIONS,
    Permission.ACCESS_ANALYSIS_TOOLS,
    Permission.ACCESS_ENHANCEMENT_TOOLS,
    Permission.ACCESS_INTEGRATION_TOOLS,
    Permission.ACCESS_KNOWLEDGE_BASE
  ],
  
  SalesManager: [
    Permission.VIEW_TEAM_DASHBOARD,
    Permission.VIEW_INDIVIDUAL_DASHBOARD,
    Permission.VIEW_CALL_ANALYSIS,
    Permission.VIEW_REP_PERFORMANCE,
    Permission.VIEW_DEAL_ANALYSIS,
    Permission.VIEW_EMAIL_ANALYSIS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_LEAD_FAILURES,
    Permission.VIEW_TEAM_CALLS,
    Permission.VIEW_OWN_CALLS,
    Permission.EXPORT_TEAM_DATA,
    Permission.MANAGE_TEAM,
    Permission.VIEW_COMPLIANCE,
    Permission.ACCESS_AI_TOOLS,
    Permission.ACCESS_TOOLS_CATALOGUE,
    Permission.ACCESS_AI_WORKSPACE,
    Permission.ACCESS_ANALYSIS_TOOLS,
    Permission.ACCESS_ENHANCEMENT_TOOLS,
    Permission.ACCESS_KNOWLEDGE_BASE
  ],
  
  Rep: [
    Permission.VIEW_INDIVIDUAL_DASHBOARD,
    Permission.VIEW_OWN_CALLS,
    Permission.EXPORT_OWN_DATA,
    Permission.ACCESS_AI_TOOLS,
    Permission.ACCESS_TOOLS_CATALOGUE,
    Permission.ACCESS_KNOWLEDGE_BASE
  ]
};

// Extended User Profile
export interface EnterpriseProfile {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: UserRole;
  department: string | null;
  managerId: string | null;
  teamIds: string[];
  permissions: Permission[];
  authMethod: AuthMethod;
  lastLogin: string;
  created_at: string;
  updated_at: string;
  
  // ADFS/Enterprise specific
  employeeId?: string;
  adfsGroups?: string[];
  organizationalUnit?: string;
}

// Team Member Interface
export interface TeamMember {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department: string;
  lastActive: string;
  performanceScore?: number;
}

// Authentication Session
export interface EnterpriseSession {
  accessToken: string;
  idToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  authMethod: AuthMethod;
  issuedAt: number;
  expiresAt: number;
}

// User Invitation Interface
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'revoked';

export interface UserInvitation {
  id: string;
  email: string;
  role: UserRole;
  status: InvitationStatus;
  invitedBy: string;
  invitedByName: string;
  invitedAt: string;
  temporaryPassword?: string;
}
