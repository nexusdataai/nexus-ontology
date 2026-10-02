# Enterprise Authentication Setup Guide

This guide will help you configure AWS Cognito with ADFS integration for the Nexus Telco QA Dashboard.

## 🏗️ Architecture Overview

The enterprise authentication system supports:
- **ADFS/SAML SSO**: Corporate users authenticate through Active Directory
- **Direct Cognito**: External users or fallback authentication
- **Role-Based Access Control**: Executive, Sales Manager, and Rep roles
- **Team Hierarchy**: Manager-subordinate relationships

## 📋 Prerequisites

1. **AWS Account** with Cognito access
2. **AWS IAM Permissions** (see permissions section below)
3. **ADFS Server** configured in your organization (optional)
4. **Domain** for Cognito Hosted UI (optional but recommended)
5. **SSL Certificate** for production deployment

## 🔑 Required AWS IAM Permissions

Your AWS user/role needs these permissions for Cognito setup:

### Option 1: AWS Managed Policy (Recommended)
Attach the following managed policy to your user/role:
```
AmazonCognitoPowerUser
```

### Option 2: Custom IAM Policy
If you need more granular control, create this custom policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:CreateUserPool",
                "cognito-idp:UpdateUserPool",
                "cognito-idp:CreateUserPoolClient",
                "cognito-idp:UpdateUserPoolClient",
                "cognito-idp:CreateGroup",
                "cognito-idp:CreateIdentityProvider",
                "cognito-idp:UpdateIdentityProvider",
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminAddUserToGroup",
                "cognito-idp:DescribeUserPool",
                "cognito-idp:DescribeUserPoolClient",
                "cognito-idp:ListUsers",
                "cognito-idp:ListGroups",
                "cognito-idp:ListIdentityProviders"
            ],
            "Resource": "*"
        }
    ]
}
```

### Requesting Permissions
If you don't have admin access, ask your AWS administrator to:

1. **Attach the AmazonCognitoPowerUser policy** to your user/role, OR
2. **Create the custom policy above** and attach it to your user/role
3. **Verify permissions** by running: `aws cognito-idp describe-user-pools-limit`

## 🔧 Method 1: AWS CLI Setup (If You Have Permissions)

### 1.1 Create User Pool

```bash
# Create the user pool
aws cognito-idp create-user-pool \
  --pool-name "nexus-qa-dashboard" \
  --policies "PasswordPolicy={MinimumLength=12,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=true}" \
  --auto-verified-attributes email \
  --username-attributes email \
  --schema '[
    {
      "Name": "email",
      "AttributeDataType": "String",
      "Required": true,
      "Mutable": true
    },
    {
      "Name": "role",
      "AttributeDataType": "String",
      "Mutable": true
    },
    {
      "Name": "department",
      "AttributeDataType": "String", 
      "Mutable": true
    },
    {
      "Name": "manager_id",
      "AttributeDataType": "String",
      "Mutable": true
    },
    {
      "Name": "employee_id",
      "AttributeDataType": "String",
      "Mutable": true
    }
  ]'

# Save the UserPool ID from the response
export USER_POOL_ID="us-east-1_xxxxxxxxx"
```

### 1.2 Create User Pool Client

```bash
# Create the app client
aws cognito-idp create-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-name "nexus-qa-dashboard-client" \
  --generate-secret false \
  --supported-identity-providers "COGNITO" \
  --callback-urls "http://localhost:5173/auth/callback,https://nexus.totogicore.com/auth/callback" \
  --logout-urls "http://localhost:5173/login,https://nexus.totogicore.com/login" \
  --allowed-o-auth-flows "code" \
  --allowed-o-auth-scopes "email,openid,profile" \
  --allowed-o-auth-flows-user-pool-client

# Save the Client ID from the response
export CLIENT_ID="xxxxxxxxxxxxxxxxx"
```

### 1.3 Create User Groups

```bash
# Create Executive group
aws cognito-idp create-group \
  --group-name "Executive" \
  --user-pool-id $USER_POOL_ID \
  --description "Executive users with full system access"

# Create SalesManager group  
aws cognito-idp create-group \
  --group-name "SalesManager" \
  --user-pool-id $USER_POOL_ID \
  --description "Sales managers with team access"

# Create Rep group
aws cognito-idp create-group \
  --group-name "Rep" \
  --user-pool-id $USER_POOL_ID \
  --description "Sales representatives with individual access"
```

## 🖥️ Method 2: AWS Console Setup (Alternative)

If you don't have CLI permissions, use the AWS Console:

### 2.1 Create User Pool via Console

1. **Open AWS Console** → **Amazon Cognito**
2. **Create User Pool**
3. **Configure Sign-in Experience**:
   - Provider types: `Cognito user pool`
   - Sign-in options: `Email`

4. **Configure Security Requirements**:
   - Password policy: 
     - Minimum length: 12
     - Require uppercase, lowercase, numbers, symbols: ✓
   - Multi-factor authentication: `Optional` (or required for executives)

5. **Configure Sign-up Experience**:
   - Self-registration: Enable
   - Required attributes: `email`
   - Custom attributes: Add these:
     ```
     role (String, Mutable)
     department (String, Mutable)
     manager_id (String, Mutable)
     employee_id (String, Mutable)
     ```

6. **Configure Message Delivery**:
   - Email provider: `Send email with Cognito`

7. **Integrate Your App**:
   - User pool name: `nexus-qa-dashboard`
   - App client name: `nexus-qa-dashboard-client`
   - Client secret: `Don't generate a client secret`

8. **Review and Create**

### 2.2 Create Groups via Console

1. **Go to User Pool** → **Groups** tab
2. **Create group**:
   - Group name: `Executive`
   - Description: `Executive users with full system access`
   - Repeat for `SalesManager` and `Rep`

### 2.3 Configure OAuth (if using ADFS later)

1. **Go to App Integration** tab
2. **Edit App client settings**
3. **Add OAuth settings**:
   - Allowed OAuth Flows: `Authorization code grant`
   - Allowed OAuth Scopes: `email`, `openid`, `profile`
   - Callback URLs: `http://localhost:5173/auth/callback`
   - Sign out URLs: `http://localhost:5173/login`

## 📝 Method 3: Infrastructure as Code (CloudFormation/CDK)

### CloudFormation Template

```yaml
# cognito-stack.yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'Nexus Telco QA Dashboard - Cognito User Pool'

Parameters:
  AppName:
    Type: String
    Default: nexus-qa-dashboard

Resources:
  UserPool:
    Type: AWS::Cognito::UserPool
    Properties:
      UserPoolName: !Ref AppName
      UsernameAttributes:
        - email
      AutoVerifiedAttributes:
        - email
      Policies:
        PasswordPolicy:
          MinimumLength: 12
          RequireUppercase: true
          RequireLowercase: true
          RequireNumbers: true
          RequireSymbols: true
      Schema:
        - Name: email
          AttributeDataType: String
          Required: true
          Mutable: true
        - Name: role
          AttributeDataType: String
          Mutable: true
        - Name: department
          AttributeDataType: String
          Mutable: true
        - Name: manager_id
          AttributeDataType: String
          Mutable: true
        - Name: employee_id
          AttributeDataType: String
          Mutable: true

  UserPoolClient:
    Type: AWS::Cognito::UserPoolClient
    Properties:
      UserPoolId: !Ref UserPool
      ClientName: !Sub "${AppName}-client"
      GenerateSecret: false
      SupportedIdentityProviders:
        - COGNITO
      CallbackURLs:
        - http://localhost:5173/auth/callback
        - https://your-domain.com/auth/callback
      LogoutURLs:
        - http://localhost:5173/login
        - https://your-domain.com/login
      AllowedOAuthFlows:
        - code
      AllowedOAuthScopes:
        - email
        - openid
        - profile
      AllowedOAuthFlowsUserPoolClient: true

  ExecutiveGroup:
    Type: AWS::Cognito::UserPoolGroup
    Properties:
      UserPoolId: !Ref UserPool
      GroupName: Executive
      Description: Executive users with full system access

  SalesManagerGroup:
    Type: AWS::Cognito::UserPoolGroup
    Properties:
      UserPoolId: !Ref UserPool
      GroupName: SalesManager
      Description: Sales managers with team access

  RepGroup:
    Type: AWS::Cognito::UserPoolGroup
    Properties:
      UserPoolId: !Ref UserPool
      GroupName: Rep
      Description: Sales representatives with individual access

Outputs:
  UserPoolId:
    Description: User Pool ID
    Value: !Ref UserPool
    Export:
      Name: !Sub "${AWS::StackName}-UserPoolId"
      
  UserPoolClientId:
    Description: User Pool Client ID
    Value: !Ref UserPoolClient
    Export:
      Name: !Sub "${AWS::StackName}-UserPoolClientId"
```

Deploy with:
```bash
aws cloudformation create-stack \
  --stack-name nexus-cognito \
  --template-body file://cognito-stack.yaml \
  --parameters ParameterKey=AppName,ParameterValue=nexus-qa-dashboard
```

## 🏢 Step 4: ADFS Integration (Optional)

⚠️ **Skip this section if you don't have ADFS or want to start with Cognito-only authentication**

### 4.1 Configure Relying Party Trust

1. **Open ADFS Management Console**
2. **Add Relying Party Trust**
3. **Import metadata from URL**: 
   ```
   https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxxxxx/.well-known/saml_metadata
   ```
   Replace `us-east-1_xxxxxxxxx` with your User Pool ID

### 4.2 Configure Claim Rules

```xml
<!-- Email Claim Rule -->
<ClaimRule>
  <RuleName>Send LDAP Email</RuleName>
  <RuleTemplate>LdapClaims</RuleTemplate>
  <AttributeStore>Active Directory</AttributeStore>
  <LdapAttribute>E-Mail-Addresses</LdapAttribute>
  <OutgoingClaimType>http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress</OutgoingClaimType>
</ClaimRule>

<!-- Name Claim Rule -->
<ClaimRule>
  <RuleName>Send LDAP Name</RuleName>
  <RuleTemplate>LdapClaims</RuleTemplate>
  <AttributeStore>Active Directory</AttributeStore>
  <LdapAttribute>displayName</LdapAttribute>
  <OutgoingClaimType>http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name</OutgoingClaimType>
</ClaimRule>

<!-- Role Claim Rule -->
<ClaimRule>
  <RuleName>Send Group Membership</RuleName>
  <RuleTemplate>LdapClaims</RuleTemplate>
  <AttributeStore>Active Directory</AttributeStore>
  <LdapAttribute>memberOf</LdapAttribute>
  <OutgoingClaimType>http://schemas.microsoft.com/ws/2008/06/identity/claims/role</OutgoingClaimType>
</ClaimRule>
```

### 4.3 Add SAML Identity Provider in Cognito

**Via CLI:**
```bash
aws cognito-idp create-identity-provider \
  --user-pool-id $USER_POOL_ID \
  --provider-name "ADFS" \
  --provider-type "SAML" \
  --provider-details '{
    "MetadataURL": "https://your-adfs-server.company.com/FederationMetadata/2007-06/FederationMetadata.xml"
  }' \
  --attribute-mapping '{
    "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
    "name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    "custom:role": "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    "custom:department": "http://schemas.company.com/identity/claims/department"
  }'
```

**Via Console:**
1. **Go to User Pool** → **Sign-in experience** → **Identity providers**
2. **Add identity provider** → **SAML**
3. **Provider name**: `ADFS`
4. **Metadata document endpoint URL**: Your ADFS metadata URL
5. **Map attributes** as shown above

## 🔐 Step 5: Environment Configuration

### 5.1 Create Environment File

Create a `.env.local` file in your project root:

```env
# AWS Cognito Configuration
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx

# Cognito Domain (optional - for hosted UI)
VITE_COGNITO_DOMAIN=your-app-name.auth.us-east-1.amazoncognito.com

# OAuth Redirect URLs
VITE_OAUTH_REDIRECT_SIGNIN=http://localhost:5173/auth/callback
VITE_OAUTH_REDIRECT_SIGNOUT=http://localhost:5173/login

# ADFS Configuration (optional)
VITE_ADFS_METADATA_URL=https://your-adfs-server.company.com/FederationMetadata/2007-06/FederationMetadata.xml

# Security Configuration
VITE_COOKIE_DOMAIN=localhost

# Environment
NODE_ENV=development
```

### 5.2 Initialize Amplify in Your App

Update your `src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'
import { initializeAmplify } from './config/amplify'

// Initialize AWS Amplify
initializeAmplify();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

## 👥 Step 6: Create Test Users

### 6.1 Via AWS CLI

```bash
# Create Executive user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username "executive@company.com" \
  --user-attributes '[
    {"Name": "email", "Value": "executive@company.com"},
    {"Name": "name", "Value": "Executive User"},
    {"Name": "custom:role", "Value": "Executive"},
    {"Name": "custom:department", "Value": "Management"}
  ]' \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

# Add user to Executive group
aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username "executive@company.com" \
  --group-name "Executive"

# Create Sales Manager user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username "manager@company.com" \
  --user-attributes '[
    {"Name": "email", "Value": "manager@company.com"},
    {"Name": "name", "Value": "Sales Manager"},
    {"Name": "custom:role", "Value": "SalesManager"},
    {"Name": "custom:department", "Value": "Sales"}
  ]' \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username "manager@company.com" \
  --group-name "SalesManager"

# Create Rep user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username "rep@company.com" \
  --user-attributes '[
    {"Name": "email", "Value": "rep@company.com"},
    {"Name": "name", "Value": "Sales Rep"},
    {"Name": "custom:role", "Value": "Rep"},
    {"Name": "custom:department", "Value": "Sales"},
    {"Name": "custom:manager_id", "Value": "manager@company.com"}
  ]' \
  --temporary-password "TempPassword123!" \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id $USER_POOL_ID \
  --username "rep@company.com" \
  --group-name "Rep"
```

### 6.2 Via AWS Console

1. **Go to User Pool** → **Users** tab
2. **Create user**
3. **Fill in user details** with custom attributes
4. **Set temporary password**
5. **Go to Groups tab** → **Add user to group**

## 🚀 Step 7: Application Integration

### 7.1 Update App.tsx

Replace your existing AuthProvider with the EnterpriseAuthProvider:

```tsx
import { EnterpriseAuthProvider } from '@/context/EnterpriseAuthContext';

const App = () => {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <EnterpriseAuthProvider>
              <AuthRoutes />
            </EnterpriseAuthProvider>
          </BrowserRouter>
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
};
```

### 7.2 Update Login Page

Replace your existing login component:

```tsx
import { EnterpriseLoginForm } from '@/components/auth/EnterpriseLoginForm';

const Login = () => {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <EnterpriseLoginForm 
        defaultTab="cognito"  // Start with direct login for testing
        showTabSwitcher={false}  // Hide ADFS option initially
      />
    </div>
  );
};
```

## 🔍 Step 8: Testing

### 8.1 Start with Cognito-Only Testing

1. **Start your development server**:
   ```bash
   npm run dev
   ```

2. **Navigate to login page**
3. **Test with created users**:
   - Email: `executive@company.com`
   - Password: `TempPassword123!`
   - You'll be prompted to set a new password

4. **Verify role-based access** works properly

### 8.2 Test Role-Based Components

```tsx
// Test role guards in your components
import { RoleGuard } from '@/components/auth/RoleGuard';
import { useRole } from '@/hooks/useRole';

// In a component:
const { isExecutive, isSalesManager, canViewTeamCalls } = useRole();

return (
  <div>
    <RoleGuard allowedRoles={['Executive', 'SalesManager']}>
      <TeamManagementPanel />
    </RoleGuard>
    
    {canViewTeamCalls && (
      <TeamCallAnalysisDashboard />
    )}
  </div>
);
```

## 🛠️ Step 9: Production Deployment

### 9.1 Security Checklist

- [ ] Enable MFA for Executive and SalesManager roles
- [ ] Configure proper redirect URLs for production
- [ ] Set up CloudWatch logging
- [ ] Configure IP restrictions if needed
- [ ] Use HTTPS everywhere
- [ ] Set secure cookie options

### 9.2 Environment Variables for Production

```env
# Production Environment
NODE_ENV=production
VITE_AWS_REGION=us-east-1
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_OAUTH_REDIRECT_SIGNIN=https://your-production-domain.com/auth/callback
VITE_OAUTH_REDIRECT_SIGNOUT=https://your-production-domain.com/login
VITE_COOKIE_DOMAIN=your-production-domain.com
```

## 🆘 Troubleshooting

### Common Permission Issues

**AWS CLI Access Denied:**
```bash
# Check your current AWS identity
aws sts get-caller-identity

# Check Cognito permissions
aws cognito-idp describe-user-pools-limit
```

**If you still get permission errors:**
1. Contact your AWS administrator
2. Request the `AmazonCognitoPowerUser` managed policy
3. Or use the AWS Console method instead
4. Or use the CloudFormation template with proper IAM permissions

### Testing Authentication Flow

```bash
# Test your configuration
curl -s "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_$USER_POOL_ID/.well-known/jwks.json"

# Should return JSON with JWKS keys
```

### Common Configuration Issues

**Environment Variables Not Loading:**
- Ensure `.env.local` is in project root
- Restart development server after changes
- Check that variables start with `VITE_`

**Authentication Redirects Not Working:**
- Verify callback URLs match exactly
- Check for trailing slashes
- Ensure HTTPS in production

## 📞 Support

For additional support:
- **AWS Documentation**: [Amazon Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html)
- **ADFS Configuration**: Contact your IT administrator
- **Application Issues**: Check the project repository issues

## 🔄 Migration from Supabase

To migrate from existing Supabase authentication:

1. **Keep both systems running in parallel** during transition
2. **Create test users** in Cognito with same roles
3. **Update components gradually** to use EnterpriseAuthContext
4. **Test all functionality** with new auth system
5. **Remove Supabase dependencies** after full migration
6. **Clean up unused authentication code**

---

## 🚦 Quick Start (Minimum Setup)

If you just want to get started quickly for development:

1. **Use AWS Console** to create User Pool (Method 2)
2. **Create a few test users** with different roles
3. **Set up `.env.local`** with your User Pool credentials
4. **Start with Cognito-only** authentication (skip ADFS initially)
5. **Test role-based access** in your application

This gets you up and running without complex CLI permissions or ADFS configuration!
