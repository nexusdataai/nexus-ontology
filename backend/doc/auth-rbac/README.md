# Authentication and RBAC Implementation

Complete documentation of the authentication, session management, and role-based access control system in the nexus-backend.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Authentication Flows](#authentication-flows)
- [Auth API Endpoints](#auth-api-endpoints)
- [Session Management](#session-management)
- [User Onboarding](#user-onboarding)
- [RBAC System](#rbac-system)
- [RBAC API Endpoints](#rbac-api-endpoints)
- [How the UI Uses RBAC APIs](#how-the-ui-uses-rbac-apis)
- [Configuration Loading](#configuration-loading)
- [Frontend Integration](#frontend-integration)
- [Middleware and Dependencies](#middleware-and-dependencies)
- [Key Files Reference](#key-files-reference)

---

## Architecture Overview

```
┌─────────────┐     Cookie/Bearer Token     ┌─────────────────────────┐
│  Frontend   │ ──────────────────────────── │  Backend (FastAPI)      │
│  (React)    │                              │                         │
│             │  POST /api/v1/auth/login     │  cognito_auth_api.py    │
│             │  GET  /api/v1/auth/me        │  session_middleware.py   │
│             │  POST /api/v1/auth/logout    │  cognito_auth_middleware │
│             │  GET  /api/v1/rbac/config    │  rbac_api.py            │
└─────────────┘                              └────────┬────────────────┘
                                                      │
                                            ┌─────────┴─────────┐
                                            │                   │
                                     ┌──────┴──────┐    ┌───────┴───────┐
                                     │  Cognito    │    │  DynamoDB     │
                                     │  User Pool  │    │  RBAC Table   │
                                     │  (OAuth)    │    │               │
                                     └─────────────┘    └───────────────┘
                                            │
                                     ┌──────┴──────┐
                                     │  SSM Params │
                                     │  /cognito/* │
                                     └─────────────┘
```

The system uses **AWS Cognito** for identity management and **HTTP-only session cookies** for request authentication. RBAC configuration is stored in DynamoDB with an in-memory cache.

---

## Authentication Flows

### Flow 1: Direct Cognito Login (Email/Password)

```
User enters email + password in EnterpriseLoginForm
  -> Frontend calls POST /api/v1/auth/login
  -> Backend calls Cognito AdminInitiateAuth (USER_PASSWORD_AUTH)
  -> If NEW_PASSWORD_REQUIRED:
       -> Return challenge to frontend
       -> User enters new password
       -> Frontend calls POST /api/v1/auth/login/new-password
       -> Backend calls Cognito AdminRespondToAuthChallenge
  -> Cognito returns tokens (access, id, refresh)
  -> Backend creates session, stores in memory
  -> Backend sets HTTP-only cookie (nexus_session)
  -> Backend returns user profile with role and permissions
  -> Frontend stores profile, navigates to dashboard
```

### Flow 2: OAuth / PKCE Flow

```
User clicks "Sign In" on login page
  -> Frontend calls GET /api/v1/auth/login/init
  -> Backend generates PKCE challenge (code_verifier + code_challenge)
  -> Backend stores PKCE state in memory
  -> Backend returns authorization_url with state + code_challenge
  -> Frontend redirects browser to Cognito Hosted UI
  -> User authenticates (Cognito email/password or federated IdP)
  -> Cognito redirects to /auth/callback?code=xxx&state=yyy
  -> AuthCallback component extracts code + state
  -> Frontend calls POST /api/v1/auth/login/callback?code=xxx&state=yyy
  -> Backend validates state, exchanges code for tokens using PKCE verifier
  -> Backend creates session, sets cookie
  -> Backend returns user profile
  -> Frontend navigates to dashboard
```

### Flow 3: ADFS SSO

```
User clicks "Sign in with Corporate SSO"
  -> Frontend calls GET /api/v1/auth/sso/adfs
  -> Backend builds Cognito authorize URL with identity_provider=ADFS
  -> Backend returns 302 redirect
  -> Browser follows redirect to Cognito -> ADFS
  -> User authenticates via corporate ADFS
  -> ADFS redirects back to Cognito -> /auth/callback?code=xxx
  -> Same callback flow as OAuth above
```

### Flow 4: Logout

```
User clicks Sign Out
  -> Frontend calls POST /api/v1/auth/logout
  -> Backend clears session from memory
  -> Backend clears nexus_session cookie
  -> Backend returns optional Cognito logout URL
  -> Frontend clears sessionStorage tokens
  -> Frontend redirects to /login (or Cognito logout URL)
```

---

## Auth API Endpoints

All endpoints are prefixed with `/api/v1/auth`.

### `POST /login`

Direct email/password login via Cognito.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "P@ssw0rd"
}
```

**Success Response (200):**
```json
{
  "user": {
    "sub": "uuid",
    "email": "user@example.com",
    "groups": ["Admin"],
    "role": "Admin",
    "permissions": ["view_all_calls", "manage_users", ...]
  },
  "expires_in": 3600,
  "message": "Login successful"
}
```

**Password Challenge Response (200):**
```json
{
  "challenge": "NEW_PASSWORD_REQUIRED",
  "session": "cognito-session-token",
  "message": "New password required"
}
```

### `POST /login/new-password`

Complete the new password challenge.

**Request:**
```json
{
  "email": "user@example.com",
  "new_password": "NewP@ssw0rd",
  "session": "cognito-session-token"
}
```

### `GET /login/init`

Initialize OAuth flow with PKCE.

**Response (200):**
```json
{
  "authorization_url": "https://domain.auth.region.amazoncognito.com/oauth2/authorize?...",
  "state": "random-state-string",
  "message": "Redirect user to authorization_url"
}
```

### `POST /login/callback`

Exchange OAuth authorization code for session.

**Query Parameters:** `code`, `state`

**Response (200):**
```json
{
  "user": {
    "sub": "uuid",
    "email": "user@example.com",
    "groups": ["Admin"],
    "role": "Admin",
    "permissions": [...]
  },
  "expires_in": 3600,
  "message": "Login successful"
}
```

### `GET /sso/adfs`

Redirect to ADFS SSO login.

**Response:** `302 Redirect` to Cognito authorize URL with `identity_provider=ADFS`.

### `GET /me`

Get current authenticated user profile.

**Response (200):**
```json
{
  "user": {
    "sub": "uuid",
    "email": "user@example.com",
    "groups": ["Admin"],
    "role": "Admin",
    "permissions": [...]
  }
}
```

**Response (401):** `{"detail": "Not authenticated. Please log in."}`

### `POST /refresh`

Refresh access token.

**Request:**
```json
{
  "refresh_token": "eyJjdH..."
}
```

### `POST /logout`

Clear session and get optional Cognito logout URL.

**Response (200):**
```json
{
  "message": "Logged out successfully",
  "logout_url": "https://domain.auth.region.amazoncognito.com/logout?..."
}
```

### `GET /health`

Auth service health check.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "cognito-auth",
  "cognito_configured": true,
  "timestamp": "2026-02-06T..."
}
```

---

## Session Management

**Implementation:** `src/apis/session_middleware.py`

### Session Storage

Sessions are stored in an in-memory dictionary keyed by session ID.

```python
# Session structure
{
    "session_id": "uuid",
    "user": {
        "sub": "cognito-sub",
        "email": "user@example.com",
        "groups": ["Admin"],
        "role": "Admin",
        "permissions": [...]
    },
    "access_token": "eyJ...",
    "id_token": "eyJ...",
    "refresh_token": "eyJ...",
    "created_at": "2026-02-06T...",
    "expires_at": "2026-02-06T..."
}
```

### Cookie Configuration

| Attribute | Value |
|-----------|-------|
| Name | `nexus_session` |
| HttpOnly | `true` (not accessible to JavaScript) |
| Secure | `true` (HTTPS only) |
| SameSite | `Lax` (CSRF protection) |
| Max-Age | `43200` (12 hours) |
| Path | `/` |

### Authentication Extraction

The middleware supports three methods (checked in order):

1. **HTTP-only cookie** (`nexus_session`) - Preferred for browser clients
2. **Authorization header** (`Bearer <session_id>`) - For API clients
3. **Cognito JWT** (`Bearer <jwt>`) - Backward compatibility

---

## User Onboarding

### Initial Admin User

When the Cognito User Pool is created (by the operator or manually), the first admin user must be created via the AWS Console or CLI. There are no backend API endpoints for user creation yet.

**Step 1: Create the first admin user in Cognito**

```bash
# Create user with temporary password
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username admin@company.com \
  --user-attributes Name=email,Value=admin@company.com Name=email_verified,Value=true \
  --temporary-password "TempP@ss123" \
  --region ap-southeast-1

# Add user to Admin group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id <USER_POOL_ID> \
  --username admin@company.com \
  --group-name Admin \
  --region ap-southeast-1
```

**Step 2: First login forces password change**

When the admin user logs in for the first time via `POST /api/v1/auth/login`, Cognito returns a `NEW_PASSWORD_REQUIRED` challenge. The frontend shows a password change form, and the new password is set via `POST /api/v1/auth/login/new-password`.

```
Admin enters temp password
  -> Backend receives NEW_PASSWORD_REQUIRED challenge from Cognito
  -> Returns { "challenge": "NEW_PASSWORD_REQUIRED", "session": "..." }
  -> Frontend shows password change form
  -> Admin enters new password
  -> POST /api/v1/auth/login/new-password
  -> Account activated, session created
```

### Onboarding Additional Users

Additional users are created via the AWS Console or CLI by the admin:

```bash
# Create user
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username user@company.com \
  --user-attributes Name=email,Value=user@company.com Name=email_verified,Value=true \
  --temporary-password "TempP@ss456" \
  --region ap-southeast-1

# Assign role (one of: Admin, Executive, SalesManager, Rep)
aws cognito-idp admin-add-user-to-group \
  --user-pool-id <USER_POOL_ID> \
  --username user@company.com \
  --group-name SalesManager \
  --region ap-southeast-1
```

The user receives the temporary password out of band and logs in, completing the same password change flow.

### Cognito Groups (Created by Operator)

The operator's `CognitoProvisioner._create_groups()` creates these groups automatically:

| Group | Description |
|-------|-------------|
| `Admin` | Administrators with full access |
| `Executive` | Executives with broad access |
| `SalesManager` | Sales managers |
| `Rep` | Sales representatives |

These groups map directly to the RBAC roles. The backend reads the user's Cognito group membership during login and maps it to the corresponding role and permissions.

### User Invitation (Frontend Placeholder)

The frontend has a `UserInviteManager` component (`nexus-ui/src/components/settings/UserInviteManager.tsx`) and `userInviteService` (`nexus-ui/src/services/userInviteService.ts`) with placeholder implementations for:

- `inviteUser(email, role)` - Create user invitation
- `resendInvitation(invitationId)` - Resend invitation email
- `revokeInvitation(invitationId)` - Revoke invitation

These are currently **not connected to a backend API**. Implementing user management requires adding Cognito `AdminCreateUser` and `AdminAddUserToGroup` endpoints to the backend.

---

## RBAC System

**Implementation:** `src/services/rbac_service.py` + `src/models/rbac_model.py`

### Roles

| Role | ID | Level | Description |
|------|----|-------|-------------|
| Administrator | `Admin` | 0 (Highest) | Full system access, all permissions |
| Executive | `Executive` | 1 | Company-wide read access, dashboards, compliance |
| Sales Manager | `SalesManager` | 2 | Team-level access, call reviews, team management |
| Sales Representative | `Rep` | 3 (Lowest) | Personal data only, own calls, basic tools |

### Permission Categories

| Category | ID | Icon | Description |
|----------|----|------|-------------|
| Dashboard Access | `dashboard_access` | - | Access to various dashboard views and analytics |
| Call Analysis | `call_analysis` | - | Access to call recordings and analysis tools |
| Data Export | `data_export` | - | Export capabilities for reports and data |
| Administrative | `administrative` | - | User management and system administration |
| AI & Analytics | `ai_analytics` | - | AI-powered analysis and enhancement tools |
| Tools Catalogue | `tools_access` | - | Access to various tools by category |

### All Permissions

| Permission ID | Display Name | Category | Risk Level | Data Scope |
|--------------|--------------|----------|------------|------------|
| `view_executive_dashboard` | View Executive Dashboard | dashboard_access | high | organization |
| `view_team_dashboard` | View Team Dashboard | dashboard_access | medium | team |
| `view_individual_dashboard` | View Individual Dashboard | dashboard_access | low | individual |
| `view_all_calls` | View All Calls | call_analysis | high | organization |
| `view_team_calls` | View Team Calls | call_analysis | medium | team |
| `view_own_calls` | View Own Calls | call_analysis | low | individual |
| `export_all_data` | Export All Data | data_export | high | organization |
| `export_team_data` | Export Team Data | data_export | medium | team |
| `export_own_data` | Export Own Data | data_export | low | individual |
| `manage_users` | Manage Users | administrative | critical | organization |
| `manage_team` | Manage Team | administrative | high | team |
| `manage_system` | Manage System | administrative | critical | organization |
| `manage_rbac` | Manage RBAC | administrative | critical | organization |
| `view_compliance` | View Compliance | administrative | medium | team |
| `access_ai_tools` | Access AI Tools | ai_analytics | low | individual |
| `access_analysis_tools` | Access Analysis Tools | tools_access | medium | team |
| `access_enhancement_tools` | Access Enhancement Tools | tools_access | medium | team |
| `access_integration_tools` | Access Integration Tools | tools_access | high | organization |
| `access_knowledge_base` | Access Knowledge Base | tools_access | low | individual |

### Default Role-Permission Matrix

| Permission | Admin | Executive | SalesManager | Rep |
|------------|:-----:|:---------:|:------------:|:---:|
| `view_executive_dashboard` | Y | Y | | |
| `view_team_dashboard` | Y | Y | Y | |
| `view_individual_dashboard` | Y | Y | Y | Y |
| `view_all_calls` | Y | Y | | |
| `view_team_calls` | Y | | Y | |
| `view_own_calls` | Y | | Y | Y |
| `export_all_data` | Y | Y | | |
| `export_team_data` | Y | | Y | |
| `export_own_data` | Y | | | Y |
| `manage_users` | Y | Y | | |
| `manage_team` | Y | | Y | |
| `manage_system` | Y | | | |
| `manage_rbac` | Y | | | |
| `view_compliance` | Y | Y | Y | |
| `access_ai_tools` | Y | Y | Y | Y |
| `access_analysis_tools` | Y | Y | Y | |
| `access_enhancement_tools` | Y | Y | Y | |
| `access_integration_tools` | Y | Y | | |
| `access_knowledge_base` | Y | Y | Y | Y |

**Note:** Admin always has all permissions (hardcoded in `has_permission()`), regardless of the matrix.

### Storage and Caching

- **Primary:** DynamoDB table `{capability}-{env}-rbac`
- **Fallback:** Default config from `DEFAULT_RBAC_CONFIG` in `rbac_model.py`
- **Cache:** In-memory with 1-minute TTL
- **Version tracking:** Semantic versioning, incremented on each update
- **Audit log:** Last 100 entries stored in the config document

---

## RBAC API Endpoints

All endpoints prefixed with `/api/v1/rbac`.

### `GET /config`

Returns the complete RBAC configuration (roles, permissions, categories, role-permission mappings).

**Auth:** Any authenticated session.

**Response:**
```json
{
  "status": "success",
  "data": {
    "metadata": {
      "version": "1.0.3",
      "lastUpdated": "2026-02-06T...",
      "updatedBy": "admin@company.com"
    },
    "roles": [...],
    "transactionCategories": [...],
    "permissions": [...],
    "rolePermissions": {
      "Admin": ["view_executive_dashboard", ...],
      "Executive": [...],
      "SalesManager": [...],
      "Rep": [...]
    },
    "auditLog": [...]
  }
}
```

**UI call:** `useRBAC` hook calls this on mount to load the permission matrix into the `RBACManager` component.

### `GET /roles`

Returns all role definitions.

**Response:**
```json
{
  "status": "success",
  "data": [
    { "id": "Admin", "name": "Admin", "displayName": "Administrator", "level": 0 },
    { "id": "Executive", "name": "Executive", "displayName": "Executive", "level": 1 },
    { "id": "SalesManager", "name": "SalesManager", "displayName": "Sales Manager", "level": 2 },
    { "id": "Rep", "name": "Rep", "displayName": "Sales Representative", "level": 3 }
  ],
  "count": 4
}
```

### `GET /roles/{role_id}`

Returns a specific role by ID.

**Example:** `GET /api/v1/rbac/roles/SalesManager`

### `GET /permissions`

Returns all permissions. Supports optional `?category=` filter.

**Example:** `GET /api/v1/rbac/permissions?category=call_analysis`

**Response:**
```json
{
  "status": "success",
  "data": [
    { "id": "view_all_calls", "displayName": "View All Calls", "category": "call_analysis", "riskLevel": "high", "dataScope": "organization" },
    { "id": "view_team_calls", "displayName": "View Team Calls", "category": "call_analysis", "riskLevel": "medium", "dataScope": "team" },
    { "id": "view_own_calls", "displayName": "View Own Calls", "category": "call_analysis", "riskLevel": "low", "dataScope": "individual" }
  ],
  "count": 3
}
```

### `GET /permissions/{permission_id}`

Returns a specific permission by ID.

### `GET /categories`

Returns all permission categories.

**Response:**
```json
{
  "status": "success",
  "data": [
    { "id": "dashboard_access", "name": "Dashboard Access", "order": 1 },
    { "id": "call_analysis", "name": "Call Analysis Access", "order": 2 },
    { "id": "data_export", "name": "Data Export Operations", "order": 3 },
    { "id": "administrative", "name": "Administrative Functions", "order": 4 },
    { "id": "ai_analytics", "name": "AI & Analytics Tools", "order": 5 },
    { "id": "tools_access", "name": "Tools Catalogue Access", "order": 6 }
  ],
  "count": 6
}
```

**UI call:** `RBACManager` uses categories to group permissions in the matrix view.

### `GET /roles/{role_id}/permissions`

Returns permissions assigned to a specific role.

**Example:** `GET /api/v1/rbac/roles/SalesManager/permissions`

**Response:**
```json
{
  "status": "success",
  "data": {
    "roleId": "SalesManager",
    "roleName": "Sales Manager",
    "permissions": ["view_team_dashboard", "view_individual_dashboard", "view_team_calls", "view_own_calls", ...],
    "count": 11
  }
}
```

### `PUT /roles/{role_id}/permissions`

Update permissions for a role. **Admin only.**

**Request:**
```json
{
  "permissions": ["view_team_dashboard", "view_individual_dashboard", "view_team_calls", "view_own_calls", "export_team_data"]
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Permissions updated successfully",
  "data": {
    "success": true,
    "roleId": "SalesManager",
    "permissions": ["view_team_dashboard", ...],
    "updatedAt": "2026-02-06T..."
  }
}
```

**Auth:** Returns 403 if caller is not Admin.

**UI call:** `RBACManager` in edit mode toggles permissions and calls `useRBAC.updateRolePermissions(roleId, permissions)` which sends this PUT request.

**Side effects:** Creates an audit log entry with previous and new permissions, increments config version.

### `GET /audit`

Returns RBAC audit log entries (most recent first).

**Query params:** `?limit=50` (default 50)

**Auth:** Admin or Executive only (returns 403 for others).

**Response:**
```json
{
  "status": "success",
  "data": [
    {
      "timestamp": "2026-02-06T10:30:00Z",
      "action": "UPDATE_ROLE_PERMISSIONS",
      "userId": "admin@company.com",
      "roleId": "SalesManager",
      "changes": "Updated permissions for role SalesManager",
      "previousValue": { "permissions": ["view_team_dashboard", ...] },
      "newValue": { "permissions": ["view_team_dashboard", "export_team_data", ...] },
      "version": "1.0.3"
    }
  ],
  "count": 1
}
```

**UI call:** `RBACManager` Audit Log tab calls `useRBAC.getAuditLog(limit)`.

### `POST /check`

Check if a role has a specific permission. Utility endpoint.

**Query params:** `?role=SalesManager&permission=view_all_calls`

**Response:**
```json
{
  "status": "success",
  "data": {
    "role": "SalesManager",
    "permission": "view_all_calls",
    "hasPermission": false
  }
}
```

### `GET /user/{role}/permissions`

Get all permissions for a given role name.

**Example:** `GET /api/v1/rbac/user/Executive/permissions`

**Response:**
```json
{
  "status": "success",
  "data": {
    "role": "Executive",
    "permissions": ["view_executive_dashboard", "view_team_dashboard", ...],
    "count": 12
  }
}
```

---

## How the UI Uses RBAC APIs

### RBACManager Component (Settings Page)

The `RBACManager` (`nexus-ui/src/components/settings/RBACManager.tsx`) is the admin UI for managing permissions:

1. **On mount:** `useRBAC` hook calls `GET /api/v1/rbac/config` to load the full RBAC configuration
2. **Permission Matrix tab:** Displays a grid of roles (columns) vs permissions (rows grouped by category). Each cell is a toggle checkbox.
3. **Edit Mode:** Admin clicks "Edit" to enable toggles. Toggling a permission calls `toggleRolePermission(roleId, permissionId)` which updates local state.
4. **Save:** Saving calls `PUT /api/v1/rbac/roles/{roleId}/permissions` for each modified role.
5. **Audit Log tab:** Calls `GET /api/v1/rbac/audit` to show change history.
6. **Access control:** Component checks `hasPermission('manage_rbac')` or Admin role - other users see a read-only view.

### Runtime Permission Checks (All Pages)

The `EnterpriseAuthContext` provides `hasPermission(permission)` to all components:

```typescript
// In any component
const { hasPermission } = useAuth();

// Admin has all permissions (hardcoded)
// Others checked against profile.permissions array
if (hasPermission('view_all_calls')) {
  // Show organization-wide call data
} else if (hasPermission('view_team_calls')) {
  // Show team calls only
} else {
  // Show own calls only
}
```

### Calls Page Example

The calls page (`calls_api.py`) uses session middleware to determine data scope:

```python
session = get_session_from_cookie(request)
if session and has_permission(session, "view_all_calls"):
    return get_all_calls()          # Organization-wide
elif session and has_permission(session, "view_team_calls"):
    return get_team_calls(session)  # Team only
else:
    return get_own_calls(session)   # Own calls only
```

---

## Configuration Loading

### Cognito Config from SSM

The backend loads Cognito configuration from SSM Parameter Store at startup:

**SSM Path:** `/{capability}/{environment}/cognito/`

| Parameter | Property | Env Var Fallback |
|-----------|----------|-----------------|
| `cognito/region` | `cognito_region` | `COGNITO_REGION` |
| `cognito/user-pool-id` | `cognito_user_pool_id` | `COGNITO_USER_POOL_ID` |
| `cognito/client-id` | `cognito_app_client_id` | `COGNITO_APP_CLIENT_ID` |
| `cognito/domain` | `cognito_domain` | `COGNITO_DOMAIN` |
| `cognito/redirect-uri` | `cognito_redirect_uri` | `COGNITO_REDIRECT_URI` |

### Loading Priority

```
1. SSM Parameter Store (ECS/EKS with IRSA)
   -> Loaded via SSMParameterLoader with 5-min cache
   
2. Environment variables (local dev)
   -> From .env.local or system env

3. Defaults
   -> Hardcoded in ConfigProvider
```

### Derived URLs

From the loaded config, the OAuth service constructs:

| URL | Pattern |
|-----|---------|
| Token endpoint | `https://{domain}.auth.{region}.amazoncognito.com/oauth2/token` |
| Authorize endpoint | `https://{domain}.auth.{region}.amazoncognito.com/oauth2/authorize` |
| JWKS URL | `https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json` |
| Logout URL | `https://{domain}.auth.{region}.amazoncognito.com/logout` |

---

## Frontend Integration

### Auth Service

**File:** `nexus-ui/src/services/backendAuthService.ts`

All auth calls use `credentials: 'include'` to send/receive HTTP-only cookies.

```typescript
// Login
backendAuthService.login(email, password)

// OAuth init
backendAuthService.initOAuthLogin()

// OAuth callback
backendAuthService.completeOAuthCallback(code, state)

// Get user profile
backendAuthService.getCurrentUser()

// Logout
backendAuthService.logout()

// Refresh token
backendAuthService.refreshToken(refreshToken)
```

### Auth Context

**File:** `nexus-ui/src/context/EnterpriseAuthContext.tsx`

Provides:
- `user` - Current user profile (or null)
- `isAuthenticated` - Boolean authentication status
- `signInWithCognito(email, password)` - Direct login
- `signInWithADFS()` - SSO login
- `signOutUser()` - Logout
- `hasPermission(permission)` - Permission check (Admin has all)

### Permission Checking in Components

```tsx
const { hasPermission } = useAuth();

// Conditionally render based on permission
{hasPermission('manage_users') && <AdminPanel />}

// Route protection
<ProtectedRoute>
  <Dashboard />
</ProtectedRoute>
```

### Key UI Files

| File | Purpose |
|------|---------|
| `src/services/backendAuthService.ts` | API calls to backend auth endpoints |
| `src/context/EnterpriseAuthContext.tsx` | Auth state provider |
| `src/pages/Login.tsx` | Login page |
| `src/pages/AuthCallback.tsx` | OAuth callback handler |
| `src/components/auth/EnterpriseLoginForm.tsx` | Login form component |
| `src/hooks/useRBAC.ts` | RBAC management hook |
| `src/components/settings/RBACManager.tsx` | RBAC admin UI |
| `src/types/auth.ts` | Auth type definitions and role-permission map |

---

## Middleware and Dependencies

### Session-Based (Preferred)

**File:** `src/apis/session_middleware.py`

```python
from .session_middleware import (
    require_authentication,     # Requires valid session
    require_role,               # Factory: require_role("Admin", "Executive")
    require_permission,         # Factory: require_permission("view_all_calls")
    require_rbac_permission,    # Factory: uses RBAC service
    get_session_from_cookie,    # Optional session (doesn't fail)
    has_permission,             # Check permission on session dict
    require_admin,              # Convenience: Admin only
    require_executive,          # Convenience: Admin or Executive
    require_sales_manager,      # Convenience: Admin, Executive, or SalesManager
)

# Usage in endpoints
@router.get("/admin-only")
async def admin(session: Dict = Depends(require_admin)):
    user = session["user"]
    ...

@router.get("/calls")
async def calls(session: Dict = Depends(get_session_from_cookie)):
    if session and has_permission(session, "view_all_calls"):
        return get_all_calls()
    return get_own_calls()
```

### Cognito JWT (Alternative)

**File:** `src/apis/cognito_auth_middleware.py`

```python
from .cognito_auth_middleware import (
    get_current_user,    # Validates Cognito JWT, returns CognitoUser
    get_optional_user,   # Optional (doesn't fail if not authenticated)
    require_role,        # Factory: require_role("Admin")
    require_admin,       # Admin only
    require_any_role,    # Any authenticated role
)

@router.get("/endpoint")
async def endpoint(user: CognitoUser = Depends(get_current_user)):
    ...
```

---

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `src/apis/cognito_auth_api.py` | Auth API endpoints (login, logout, callback, etc.) |
| `src/apis/cognito_auth_middleware.py` | JWT validation middleware |
| `src/apis/session_middleware.py` | Session-based auth middleware |
| `src/apis/rbac_api.py` | RBAC management API |
| `src/apis/auth_api.py` | Mock auth API (testing/development) |
| `src/services/cognito_oauth_service.py` | Cognito OAuth service (PKCE, token exchange) |
| `src/services/rbac_service.py` | RBAC service (DynamoDB storage, caching) |
| `src/models/rbac_model.py` | RBAC data models and default configuration |
| `src/config/config_provider.py` | Configuration loading (SSM, env vars) |
| `src/config/ssm_loader.py` | SSM Parameter Store loader |
| `src/config/secrets_loader.py` | Secrets Manager loader |

### Frontend

| File | Purpose |
|------|---------|
| `src/services/backendAuthService.ts` | Auth API client |
| `src/context/EnterpriseAuthContext.tsx` | Auth state provider |
| `src/pages/Login.tsx` | Login page |
| `src/pages/AuthCallback.tsx` | OAuth callback page |
| `src/components/auth/EnterpriseLoginForm.tsx` | Login form |
| `src/hooks/useRBAC.ts` | RBAC management hook |
| `src/types/auth.ts` | Auth types and role-permission map |
