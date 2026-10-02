import { useMemo, useCallback } from 'react';
import { useEnterpriseAuth } from '@/context/EnterpriseAuthContext';
import { UserRole, Permission } from '@/types/auth';

/**
 * Role-based access control hook
 * Provides convenient methods for checking user roles and permissions
 */
export const useRole = () => {
  const { 
    profile, 
    hasPermission,
    canAccessCall,
    canViewTeamMember
  } = useEnterpriseAuth();

  // Derive userRole from profile
  const userRole = profile?.role;
  
  // Mock team members for now (will be replaced with real data later)
  const teamMembers = profile?.teamIds?.map(id => ({
    id,
    email: '',
    full_name: '',
    role: 'Rep' as UserRole,
    department: '',
    lastActive: new Date().toISOString()
  })) || [];

  // Implement hasAnyPermission locally
  const hasAnyPermission = useCallback((permissions: Permission[]) => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  // Role checking methods
  const isAdmin = useMemo(() => userRole === 'Admin', [userRole]);
  const isExecutive = useMemo(() => userRole === 'Executive' || userRole === 'Admin', [userRole]);
  const isSalesManager = useMemo(() => userRole === 'SalesManager', [userRole]);
  const isRep = useMemo(() => userRole === 'Rep', [userRole]);

  // Permission checking methods
  const hasAccess = useCallback((requiredRoles: UserRole[]) => {
    return userRole ? requiredRoles.includes(userRole) : false;
  }, [userRole]);

  const hasAnyRole = useCallback((roles: UserRole[]) => {
    return userRole ? roles.includes(userRole) : false;
  }, [userRole]);

  // Dashboard access methods
  const canViewExecutiveDashboard = useMemo(() => 
    hasPermission(Permission.VIEW_EXECUTIVE_DASHBOARD), 
    [hasPermission]
  );

  const canViewTeamDashboard = useMemo(() => 
    hasPermission(Permission.VIEW_TEAM_DASHBOARD), 
    [hasPermission]
  );

  const canViewIndividualDashboard = useMemo(() => 
    hasPermission(Permission.VIEW_INDIVIDUAL_DASHBOARD), 
    [hasPermission]
  );

  const canViewCallAnalysis = useMemo(() => 
    hasPermission(Permission.VIEW_CALL_ANALYSIS), 
    [hasPermission]
  );

  const canViewRepPerformance = useMemo(() => 
    hasPermission(Permission.VIEW_REP_PERFORMANCE), 
    [hasPermission]
  );

  const canViewDealAnalysis = useMemo(() => 
    hasPermission(Permission.VIEW_DEAL_ANALYSIS), 
    [hasPermission]
  );

  const canViewEmailAnalysis = useMemo(() => 
    hasPermission(Permission.VIEW_EMAIL_ANALYSIS), 
    [hasPermission]
  );

  const canViewReports = useMemo(() => 
    hasPermission(Permission.VIEW_REPORTS), 
    [hasPermission]
  );

  const canViewLeadFailures = useMemo(() => 
    hasPermission(Permission.VIEW_LEAD_FAILURES), 
    [hasPermission]
  );

  const canAccessToolsCatalogue = useMemo(() => 
    hasPermission(Permission.ACCESS_TOOLS_CATALOGUE), 
    [hasPermission]
  );

  const canAccessAIWorkspace = useMemo(() => 
    hasPermission(Permission.ACCESS_AI_WORKSPACE), 
    [hasPermission]
  );

  const canAccessOperations = useMemo(() => 
    hasPermission(Permission.ACCESS_OPERATIONS), 
    [hasPermission]
  );

  // Call analysis access methods
  const canViewAllCalls = useMemo(() => 
    hasPermission(Permission.VIEW_ALL_CALLS), 
    [hasPermission]
  );

  const canViewTeamCalls = useMemo(() => 
    hasPermission(Permission.VIEW_TEAM_CALLS), 
    [hasPermission]
  );

  const canViewOwnCalls = useMemo(() => 
    hasPermission(Permission.VIEW_OWN_CALLS), 
    [hasPermission]
  );

  // Data export permissions
  const canExportAllData = useMemo(() => 
    hasPermission(Permission.EXPORT_ALL_DATA), 
    [hasPermission]
  );

  const canExportTeamData = useMemo(() => 
    hasPermission(Permission.EXPORT_TEAM_DATA), 
    [hasPermission]
  );

  const canExportOwnData = useMemo(() => 
    hasPermission(Permission.EXPORT_OWN_DATA), 
    [hasPermission]
  );

  // Administrative permissions
  const canManageUsers = useMemo(() => 
    hasPermission(Permission.MANAGE_USERS), 
    [hasPermission]
  );

  const canManageTeam = useMemo(() => 
    hasPermission(Permission.MANAGE_TEAM), 
    [hasPermission]
  );

  const canViewCompliance = useMemo(() => 
    hasPermission(Permission.VIEW_COMPLIANCE), 
    [hasPermission]
  );

  const canAccessAITools = useMemo(() => 
    hasPermission(Permission.ACCESS_AI_TOOLS), 
    [hasPermission]
  );

  // Helper methods for UI components
  const getRoleDisplayName = useMemo(() => {
    switch (userRole) {
      case 'Admin':
        return 'Administrator';
      case 'Executive':
        return 'Executive';
      case 'SalesManager':
        return 'Sales Manager';
      case 'Rep':
        return 'Sales Representative';
      default:
        return 'User';
    }
  }, [userRole]);

  const getRoleBadgeColor = useMemo(() => {
    switch (userRole) {
      case 'Admin':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'Executive':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'SalesManager':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'Rep':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  }, [userRole]);

  const getAccessLevel = useMemo(() => {
    if (canViewAllCalls) return 'all';
    if (canViewTeamCalls) return 'team';
    if (canViewOwnCalls) return 'personal';
    return 'none';
  }, [canViewAllCalls, canViewTeamCalls, canViewOwnCalls]);

  const getAccessLevelDisplayName = useMemo(() => {
    switch (getAccessLevel) {
      case 'all':
        return 'All Data Access';
      case 'team':
        return 'Team Data Access';
      case 'personal':
        return 'Personal Data Only';
      default:
        return 'No Access';
    }
  }, [getAccessLevel]);

  // Team management helpers
  const isTeamLead = useMemo(() => 
    isAdmin || isSalesManager || isExecutive, 
    [isAdmin, isSalesManager, isExecutive]
  );

  const teamSize = useMemo(() => 
    teamMembers?.length || 0, 
    [teamMembers]
  );

  const hasTeamMembers = useMemo(() => 
    (teamMembers?.length || 0) > 0, 
    [teamMembers]
  );

  // Data filtering helpers
  const shouldShowUserInList = useCallback((targetUserId: string) => {
    return canViewTeamMember(targetUserId);
  }, [canViewTeamMember]);

  const shouldShowCallInList = useCallback((callId: string) => {
    return canAccessCall(callId);
  }, [canAccessCall]);

  // Permission groups for bulk checking
  const dashboardPermissions = useMemo(() => [
    Permission.VIEW_EXECUTIVE_DASHBOARD,
    Permission.VIEW_TEAM_DASHBOARD,
    Permission.VIEW_INDIVIDUAL_DASHBOARD,
    Permission.VIEW_CALL_ANALYSIS,
    Permission.VIEW_REP_PERFORMANCE,
    Permission.VIEW_DEAL_ANALYSIS,
    Permission.VIEW_EMAIL_ANALYSIS,
    Permission.VIEW_REPORTS,
    Permission.VIEW_LEAD_FAILURES
  ], []);

  const callAnalysisPermissions = useMemo(() => [
    Permission.VIEW_ALL_CALLS,
    Permission.VIEW_TEAM_CALLS,
    Permission.VIEW_OWN_CALLS
  ], []);

  const exportPermissions = useMemo(() => [
    Permission.EXPORT_ALL_DATA,
    Permission.EXPORT_TEAM_DATA,
    Permission.EXPORT_OWN_DATA
  ], []);

  const adminPermissions = useMemo(() => [
    Permission.MANAGE_USERS,
    Permission.MANAGE_TEAM,
    Permission.VIEW_COMPLIANCE
  ], []);

  // Bulk permission checks
  const hasDashboardAccess = useMemo(() => 
    hasAnyPermission(dashboardPermissions), 
    [hasAnyPermission, dashboardPermissions]
  );

  const hasCallAnalysisAccess = useMemo(() => 
    hasAnyPermission(callAnalysisPermissions), 
    [hasAnyPermission, callAnalysisPermissions]
  );

  const hasExportAccess = useMemo(() => 
    hasAnyPermission(exportPermissions), 
    [hasAnyPermission, exportPermissions]
  );

  const hasAdminAccess = useMemo(() => 
    hasAnyPermission(adminPermissions), 
    [hasAnyPermission, adminPermissions]
  );

  return {
    // Basic role checks
    isAdmin,
    isExecutive,
    isSalesManager,
    isRep,
    userRole,
    
    // Permission methods
    hasPermission,
    hasAnyPermission,
    hasAccess,
    hasAnyRole,
    
    // Dashboard access
    canViewExecutiveDashboard,
    canViewTeamDashboard,
    canViewIndividualDashboard,
    canViewCallAnalysis,
    canViewRepPerformance,
    canViewDealAnalysis,
    canViewEmailAnalysis,
    canViewReports,
    canViewLeadFailures,
    
    // Feature access
    canAccessToolsCatalogue,
    canAccessAIWorkspace,
    canAccessOperations,
    
    // Call analysis access
    canViewAllCalls,
    canViewTeamCalls,
    canViewOwnCalls,
    canAccessCall,
    
    // Data export permissions
    canExportAllData,
    canExportTeamData,
    canExportOwnData,
    
    // Administrative permissions
    canManageUsers,
    canManageTeam,
    canViewCompliance,
    canAccessAITools,
    
    // Team management
    canViewTeamMember,
    isTeamLead,
    teamSize,
    hasTeamMembers,
    
    // UI helpers
    getRoleDisplayName,
    getRoleBadgeColor,
    getAccessLevel,
    getAccessLevelDisplayName,
    
    // Data filtering
    shouldShowUserInList,
    shouldShowCallInList,
    
    // Bulk permission checks
    hasDashboardAccess,
    hasCallAnalysisAccess,
    hasExportAccess,
    hasAdminAccess,
    
    // Raw data
    profile,
    teamMembers
  };
};

/**
 * Hook for checking specific permissions
 * Useful for component-level permission checks
 */
export const usePermissions = (requiredPermissions: Permission[]) => {
  const { hasPermission } = useEnterpriseAuth();
  
  const hasAnyPermission = useCallback((permissions: Permission[]) => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);
  
  const hasAllPermissions = useMemo(() => 
    requiredPermissions.every(permission => hasPermission(permission)), 
    [hasPermission, requiredPermissions]
  );
  
  const hasSomePermissions = useMemo(() => 
    hasAnyPermission(requiredPermissions), 
    [hasAnyPermission, requiredPermissions]
  );
  
  return {
    hasAllPermissions,
    hasSomePermissions,
    missingPermissions: requiredPermissions.filter(permission => !hasPermission(permission))
  };
};

/**
 * Hook for role-based component rendering
 * Returns boolean indicating if component should be rendered
 */
export const useRoleAccess = (allowedRoles: UserRole[], fallbackMode: 'hide' | 'disable' = 'hide') => {
  const { hasAccess, userRole } = useRole();
  
  const isAllowed = useMemo(() => 
    hasAccess(allowedRoles), 
    [hasAccess, allowedRoles]
  );
  
  return {
    isAllowed,
    shouldRender: fallbackMode === 'hide' ? isAllowed : true,
    shouldDisable: fallbackMode === 'disable' ? !isAllowed : false,
    userRole
  };
};

export default useRole;
