# Nexus Telco UI GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated deployment of the Nexus Telco UI React application.

## Workflow Files

| File | Environment | Trigger | Domain |
|------|-------------|---------|--------|
| `deploy-dev.yml` | Development | Push to `dev` branch | call-dev.totogicore.com |
| `deploy-test.yml` | Test | Push to `test` branch | call-test.totogicore.com |
| `deploy-stage.yml` | Staging | Push to `stage` branch | call-stage.totogicore.com |
| `deploy-prod.yml` | Production | Push to `main` + confirmation | call.totogicore.com |

## Quick Setup

### 1. Create IAM Roles

```bash
cd deploy/git-workflow
chmod +x setup-github-integration.sh
./setup-github-integration.sh
```

### 2. Add GitHub Secrets

Go to: `https://github.com/YOUR_ORG/nexus-ui/settings/secrets/actions`

**Required AWS Role Secrets:**

| Secret Name | Description |
|-------------|-------------|
| `AWS_ROLE_TO_ASSUME_DEV` | IAM role ARN for dev deployments |
| `AWS_ROLE_TO_ASSUME_TEST` | IAM role ARN for test deployments |
| `AWS_ROLE_TO_ASSUME_STAGE` | IAM role ARN for stage deployments |
| `AWS_ROLE_TO_ASSUME_PROD` | IAM role ARN for prod deployments |

Note: Authentication is handled by the backend API, so no Cognito secrets are required.

## Deployment Flow

```
dev branch → Development (automatic)
    ↓
test branch → Test environment (automatic)
    ↓
stage branch → Staging (automatic)
    ↓
main branch → Production (requires "DEPLOY_TO_PRODUCTION" confirmation)
```

## Manual Deployment

1. Go to **Actions** tab in GitHub
2. Select the appropriate workflow
3. Click **Run workflow**
4. For production: Type `DEPLOY_TO_PRODUCTION` when prompted

## Deployment Options

Each workflow supports these deployment types:

| Type | Description |
|------|-------------|
| `full` | Full deployment (build + upload + invalidate) |
| `skip-build` | Skip npm build, use existing dist/ |
| `skip-invalidate` | Skip CloudFront cache invalidation |

## Troubleshooting

### "Could not load credentials from any providers"

1. Verify GitHub secrets are set correctly
2. Check IAM role exists: `aws iam get-role --role-name GitHubActions-nexus-ui-dev`
3. Ensure OIDC trust policy is correct

### "S3 bucket not found"

Ensure the S3 bucket exists:
- `call-processing-dev-frontend`
- `call-processing-test-frontend`
- `call-processing-stage-frontend`
- `call-processing-prod-frontend`

### "CloudFront distribution not found"

The deployment script will warn but continue. Manually create invalidation if needed.

## Architecture

```
GitHub Actions
    ↓ (OIDC Authentication)
AWS IAM Role
    ↓
update-frontend.sh <env>
    ↓
┌─────────────────────────────────────────┐
│  1. npm run build                       │
│  2. Generate config.json                │
│  3. aws s3 sync dist/ s3://bucket/      │
│  4. aws cloudfront create-invalidation  │
└─────────────────────────────────────────┘
```

## Security

- Uses OIDC for authentication (no long-lived AWS keys)
- Production deployments require manual confirmation
- Security audit runs before production deployment
- IAM roles are scoped per environment
