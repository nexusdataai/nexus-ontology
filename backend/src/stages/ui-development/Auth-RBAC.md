# Auth & RBAC Customization

## Authentication 

Plain login/password based cognito authentication

### Two Roles

```
Executive
  - VIEW_EXECUTIVE_DASHBOARD
  - VIEW_ALL_ALERTS
  - MANAGE_ALERT_RULES
  - MANAGE_USERS
  - MANAGE_SYSTEM_SETTINGS

OpsManager
  - VIEW_TEAM_DASHBOARD
  - VIEW_TEAM_ALERTS
  - MANAGE_TEAM_RULES
  - MANAGE_TEAM_MEMBERS
```

### 14 Permissions

- `VIEW_EXECUTIVE_DASHBOARD` - Exec only
- `VIEW_TEAM_DASHBOARD` - Exec + OpsManager
- `VIEW_ALL_ALERTS` - Exec only
- `VIEW_TEAM_ALERTS` - OpsManager only
- `MANAGE_ALERT_RULES` - Exec only
- `MANAGE_TEAM_RULES` - OpsManager only
- `VIEW_ALL_REMEDIATION` - Exec only
- `VIEW_TEAM_REMEDIATION` - OpsManager only
- `MANAGE_REMEDIATION` - Both roles
- `MANAGE_USERS` - Exec only
- `MANAGE_TEAM_MEMBERS` - OpsManager only
- `VIEW_COMPLIANCE` - Both roles
- `EXPORT_ALL_DATA` - Exec only
- `EXPORT_TEAM_DATA` - OpsManager only
- `ACCESS_AI_TOOLS` - Both roles
- `MANAGE_SYSTEM_SETTINGS` - Exec only


## ⚡ Testing Matrix

| Scenario | Expected | How to Test |
|----------|----------|------------|
| Executive logs in | Sees exec dashboard | Use: executive@company.com |
| OpsManager logs in | Sees team dashboard | Use: opsmanager@company.com |
| Invalid password | Shows error | Try wrong password |
| New password needed | Shows password change form | Use new user |
| Sign out | Redirected to login | Click sign out |
| Access without auth | Redirected to login | Clear cookies, refresh |
| OpsManager views exec section | Hidden | RoleGuard hides it |
| Executive exports data | Shows export button | Check canExportAllData |

## ✅ Success Checklist

- [ ] Users can log in with valid credentials
- [ ] Invalid credentials show error message
- [ ] New password challenge works
- [ ] Users redirected to correct dashboard based on role
- [ ] Executive sees executive-only sections
- [ ] OpsManager sees team-only sections
- [ ] Alert data filtered by role
- [ ] Sign out works and clears state
- [ ] Unauthenticated users can't access protected routes
- [ ] All TypeScript types are correct


### During Development

**Code Quality**
- [ ] All permission checks follow fail-secure pattern (`return false` on error)
- [ ] No hardcoded credentials anywhere in code
- [ ] All permissions use centralized `ROLE_PERMISSIONS` mapping
- [ ] useRole() hook used instead of direct context access
- [ ] No `any` types - full TypeScript coverage
- [ ] ESLint passes with no warnings

**Authentication**
- [ ] cognitoService wraps all AWS SDK calls
- [ ] Error messages are user-friendly (don't leak info)
- [ ] Token stored only in Context state (NOT localStorage)
- [ ] Session cleared on sign out
- [ ] EnterpriseAuthProvider wraps entire app in App.tsx
- [ ] useEnterpriseAuth() throws error if used outside provider

**Authorization**
- [ ] RoleGuard supports three fallback modes: hide, message, custom
- [ ] RoleGuard checks work with both allowedRoles and requiredPermissions
- [ ] canAccessAlert() and canManageRule() use alertAccessService
- [ ] Permission checks in services (not just UI)
- [ ] Navigation reflects user role

**Components**
- [ ] Login form validates email/password with Zod
- [ ] PasswordChangeForm handles NEW_PASSWORD_REQUIRED challenge
- [ ] All auth UI components use shadcn/ui components
- [ ] RoleGuard renders access denied message with role info
- [ ] No auth components render outside EnterpriseAuthProvider

### Before Testing

**Routes**
- [ ] /login is accessible without authentication
- [ ] /password-change is only shown during password flow
- [ ] All other routes wrapped in ProtectedRoute
- [ ] Unauthenticated users redirected to /login
- [ ] RoleGuard on executive-only routes

**Data Access**
- [ ] useAlertData filters by role/team
- [ ] useRuleData checks permissions before operations
- [ ] Executive sees all alerts, OpsManager sees team alerts only
- [ ] Team member list populated correctly based on role

**Error Handling**
- [ ] Cognito errors mapped to user-friendly messages
- [ ] Network errors handled gracefully
- [ ] Permission errors don't show role information
- [ ] Auth context errors caught by ErrorBoundary

### Before Deployment

**Security**
- [ ] Backend validates all requests with Bearer token
- [ ] Backend checks permissions before returning data
- [ ] CORS configured correctly
- [ ] No console.log of sensitive data in production
- [ ] Token expiration handled gracefully
- [ ] Sign out clears all local state

**Testing**
- [ ] Executive login test passed
- [ ] OpsManager login test passed
- [ ] Invalid credentials show error
- [ ] New password challenge works
- [ ] Sign out redirects to login
- [ ] Role-based access control tested
- [ ] Permission denied page shows correctly
- [ ] Session persists on refresh
- [ ] Data filtering works by role/team

**Documentation**
- [ ] AUTHENTICATION_SETUP.md created
- [ ] RBAC_GUIDE.md created
- [ ] Code comments explain permission checks
- [ ] Examples show common patterns
- [ ] Troubleshooting guide included

---

