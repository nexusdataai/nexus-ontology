import React from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Shield, AlertTriangle, Lock, ArrowLeft } from 'lucide-react';
import { useRole } from '@/hooks/useRole';
import { UserRole, Permission } from '@/types/auth';

interface RoleGuardProps {
  /**
   * Roles that are allowed to access this component
   */
  allowedRoles?: UserRole[];
  
  /**
   * Specific permissions required (alternative to allowedRoles)
   */
  requiredPermissions?: Permission[];
  
  /**
   * Whether to require ALL permissions or just ANY permission
   */
  requireAllPermissions?: boolean;
  
  /**
   * Children to render if access is granted
   */
  children: React.ReactNode;
  
  /**
   * Custom fallback component to show when access is denied
   */
  fallback?: React.ReactNode;
  
  /**
   * Fallback mode: 'hide' (render nothing), 'message' (show access denied), or 'custom' (use fallback prop)
   */
  fallbackMode?: 'hide' | 'message' | 'custom';
  
  /**
   * Custom message to show in message fallback mode
   */
  accessDeniedMessage?: string;
  
  /**
   * Whether to show user's current role in access denied message
   */
  showCurrentRole?: boolean;
  
  /**
   * Callback when access is denied
   */
  onAccessDenied?: () => void;
}

/**
 * RoleGuard Component
 * 
 * Conditionally renders children based on user roles or permissions.
 * Supports multiple fallback modes for better UX.
 */
export const RoleGuard: React.FC<RoleGuardProps> = ({
  allowedRoles = [],
  requiredPermissions = [],
  requireAllPermissions = false,
  children,
  fallback,
  fallbackMode = 'hide',
  accessDeniedMessage,
  showCurrentRole = true,
  onAccessDenied
}) => {
  const { 
    hasAccess, 
    hasPermission, 
    hasAnyPermission, 
    userRole, 
    getRoleDisplayName 
  } = useRole();

  // Determine if user has access
  const hasRoleAccess = allowedRoles.length === 0 || hasAccess(allowedRoles);
  
  const hasPermissionAccess = requiredPermissions.length === 0 || (
    requireAllPermissions 
      ? requiredPermissions.every(permission => hasPermission(permission))
      : hasAnyPermission(requiredPermissions)
  );

  const hasFullAccess = hasRoleAccess && hasPermissionAccess;

  // Call onAccessDenied callback if access is denied
  React.useEffect(() => {
    if (!hasFullAccess && onAccessDenied) {
      onAccessDenied();
    }
  }, [hasFullAccess, onAccessDenied]);

  // If access is granted, render children
  if (hasFullAccess) {
    return <>{children}</>;
  }

  // Handle different fallback modes
  switch (fallbackMode) {
    case 'hide':
      return null;
      
    case 'custom':
      return <>{fallback}</>;
      
    case 'message':
    default:
      return (
        <AccessDeniedMessage
          allowedRoles={allowedRoles}
          requiredPermissions={requiredPermissions}
          currentRole={userRole}
          currentRoleDisplay={getRoleDisplayName}
          customMessage={accessDeniedMessage}
          showCurrentRole={showCurrentRole}
        />
      );
  }
};

interface AccessDeniedMessageProps {
  allowedRoles: UserRole[];
  requiredPermissions: Permission[];
  currentRole: UserRole | null;
  currentRoleDisplay: string;
  customMessage?: string;
  showCurrentRole: boolean;
}

const AccessDeniedMessage: React.FC<AccessDeniedMessageProps> = ({
  allowedRoles,
  requiredPermissions,
  currentRole,
  currentRoleDisplay,
  customMessage,
  showCurrentRole
}) => {
  const getRequiredRolesText = () => {
    if (allowedRoles.length === 0) return '';
    
    if (allowedRoles.length === 1) {
      return allowedRoles[0] === 'SalesManager' ? 'Sales Manager' : allowedRoles[0];
    }
    
    const roleNames = allowedRoles.map(role => 
      role === 'SalesManager' ? 'Sales Manager' : role
    );
    
    if (roleNames.length === 2) {
      return `${roleNames[0]} or ${roleNames[1]}`;
    }
    
    return `${roleNames.slice(0, -1).join(', ')}, or ${roleNames[roleNames.length - 1]}`;
  };

  const getPermissionsText = () => {
    if (requiredPermissions.length === 0) return '';
    
    const permissionNames = requiredPermissions.map(permission => 
      permission.replace(/_/g, ' ').toLowerCase()
    );
    
    if (permissionNames.length === 1) {
      return permissionNames[0];
    }
    
    return `${permissionNames.slice(0, -1).join(', ')} and ${permissionNames[permissionNames.length - 1]}`;
  };

  const defaultMessage = () => {
    const roleText = getRequiredRolesText();
    const permissionText = getPermissionsText();
    
    if (roleText && permissionText) {
      return `This feature requires ${roleText} role with ${permissionText} permissions.`;
    } else if (roleText) {
      return `This feature is only available to ${roleText} users.`;
    } else if (permissionText) {
      return `This feature requires ${permissionText} permissions.`;
    } else {
      return 'You do not have permission to access this feature.';
    }
  };

  return (
    <div className="p-6 bg-background border border-border rounded-lg">
      <Alert className="mb-4">
        <Shield className="h-4 w-4" />
        <AlertDescription className="font-medium">
          Access Restricted
        </AlertDescription>
      </Alert>
      
      <div className="space-y-4">
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-8 h-8 bg-destructive/10 rounded-full flex items-center justify-center">
              <Lock className="h-4 w-4 text-destructive" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-2">
              {customMessage || defaultMessage()}
            </p>
            
            {showCurrentRole && currentRole && (
              <div className="flex items-center space-x-2 mb-3">
                <span className="text-xs text-muted-foreground">Your current role:</span>
                <Badge variant="outline" className="text-xs">
                  {currentRoleDisplay}
                </Badge>
              </div>
            )}
            
            {allowedRoles.length > 0 && (
              <div className="mb-3">
                <p className="text-xs text-muted-foreground mb-1">Required roles:</p>
                <div className="flex flex-wrap gap-1">
                  {allowedRoles.map((role) => (
                    <Badge key={role} variant="secondary" className="text-xs">
                      {role === 'SalesManager' ? 'Sales Manager' : role}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            
            {requiredPermissions.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Required permissions:</p>
                <div className="flex flex-wrap gap-1">
                  {requiredPermissions.map((permission) => (
                    <Badge key={permission} variant="outline" className="text-xs">
                      {permission.replace(/_/g, ' ').toLowerCase()}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            <AlertTriangle className="h-3 w-3 inline mr-1" />
            If you believe you should have access, please contact your administrator.
          </p>
        </div>
      </div>
    </div>
  );
};

/**
 * PermissionGuard Component
 * 
 * Simplified component for permission-based access control
 */
interface PermissionGuardProps {
  permissions: Permission | Permission[];
  requireAll?: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showMessage?: boolean;
}

export const PermissionGuard: React.FC<PermissionGuardProps> = ({
  permissions,
  requireAll = false,
  children,
  fallback,
  showMessage = false
}) => {
  const permissionArray = Array.isArray(permissions) ? permissions : [permissions];
  
  return (
    <RoleGuard
      requiredPermissions={permissionArray}
      requireAllPermissions={requireAll}
      fallbackMode={showMessage ? 'message' : (fallback ? 'custom' : 'hide')}
      fallback={fallback}
    >
      {children}
    </RoleGuard>
  );
};

/**
 * ConditionalRender Component
 * 
 * Simple component for conditional rendering based on roles
 */
interface ConditionalRenderProps {
  condition: boolean;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const ConditionalRender: React.FC<ConditionalRenderProps> = ({
  condition,
  children,
  fallback = null
}) => {
  return condition ? <>{children}</> : <>{fallback}</>;
};

/**
 * RoleBasedWrapper Component
 * 
 * Wrapper that adds role-based styling or behavior
 */
interface RoleBasedWrapperProps {
  children: React.ReactNode;
  className?: string;
  executiveClassName?: string;
  managerClassName?: string;
  repClassName?: string;
}

export const RoleBasedWrapper: React.FC<RoleBasedWrapperProps> = ({
  children,
  className = '',
  executiveClassName = '',
  managerClassName = '',
  repClassName = ''
}) => {
  const { isExecutive, isSalesManager, isRep } = useRole();
  
  const roleClassName = isExecutive ? executiveClassName 
    : isSalesManager ? managerClassName 
    : isRep ? repClassName 
    : '';
  
  const combinedClassName = `${className} ${roleClassName}`.trim();
  
  return (
    <div className={combinedClassName}>
      {children}
    </div>
  );
};

export default RoleGuard;
