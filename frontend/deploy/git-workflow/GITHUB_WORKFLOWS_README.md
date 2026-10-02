# Nexus Telco UI GitHub Actions Integration

This guide explains how to set up and use GitHub Actions for automated deployment of the Nexus Telco UI React application to AWS S3 and CloudFront.

## Table of Contents

1. [Overview](#overview)
2. [Workflow Structure](#workflow-structure)
3. [Quick Setup](#quick-setup)
4. [GitHub Secrets Configuration](#github-secrets-configuration)
5. [Environment Configuration](#environment-configuration)
6. [Deployment Process](#deployment-process)
7. [Troubleshooting](#troubleshooting)

## Overview

The Nexus Telco UI project uses GitHub Actions for:
- **Automated deployments** to S3 with CloudFront CDN
- **Multi-environment support** (dev/test/stage/prod)
- **Security through OIDC** authentication (no long-lived AWS keys)
- **Flexible deployment options** (full, skip-build, skip-invalidate)

### Architecture

```
GitHub Actions (Push/PR/Manual)
        ↓
    OIDC Authentication
        ↓
    AWS IAM Role
        ↓
    update-frontend.sh <env>
        ↓
┌─────────────────────────────────┐
│  1. npm install && npm build   │
│  2. Generate config.json       │
│  3. S3 sync                    │
│  4. CloudFront invalidation    │
└─────────────────────────────────┘
        ↓
    https://call-<env>.totogicore.com
```

### Workflow Files

```
.github/workflows/
├── deploy-dev.yml      # Development (dev branch)
├── deploy-test.yml     # Test (test branch)
├── deploy-stage.yml    # Staging (stage branch)
├── deploy-prod.yml     # Production (main branch)
└── README.md           # This documentation
```

## Workflow Structure

### Development Workflow (`deploy-dev.yml`)
- **Trigger**: Push to `dev` branch or manual dispatch
- **Environment**: Development
- **URL**: https://call-dev.totogicore.com
- **Approval**: None required

### Test Workflow (`deploy-test.yml`)
- **Trigger**: Push to `test` branch or manual dispatch
- **Environment**: Test
- **URL**: https://call-test.totogicore.com
- **Approval**: None required

### Staging Workflow (`deploy-stage.yml`)
- **Trigger**: Push to `stage` branch or manual dispatch
- **Environment**: Staging
- **URL**: https://call-stage.totogicore.com
- **Approval**: None required

### Production Workflow (`deploy-prod.yml`)
- **Trigger**: Push to `main` branch, release, or manual dispatch
- **Environment**: Production
- **URL**: https://call.totogicore.com
- **Approval**: Manual confirmation required (`DEPLOY_TO_PRODUCTION`)
- **Features**: Security scan before deployment

## Quick Setup

### Prerequisites
- AWS CLI configured with appropriate permissions
- GitHub repository for nexus-ui
- Access to AWS account (764119721991) for IAM role creation
- Existing GitHub OIDC provider in AWS

### Automated Setup (Recommended)

```bash
cd /opt/mycode/trilogy/nexus-ui/deploy/git-workflow
chmod +x setup-github-integration.sh
./setup-github-integration.sh
```

The script will:
1. Deploy IAM roles for all 4 environments via CloudFormation
2. Generate the exact GitHub secrets you need
3. Save role ARNs to `role-arns-secrets.md`

### Manual Setup

1. **Deploy IAM Role for each environment**:
   ```bash
   # For dev environment
   aws cloudformation deploy \
     --template-file ./deploy/git-workflow/github-role-only.yml \
     --stack-name github-actions-role-nexus-ui-dev \
     --parameter-overrides \
       GitHubOrganization=YOUR_GITHUB_ORG \
       GitHubRepository=nexus-ui \
       BranchName=dev \
     --capabilities CAPABILITY_NAMED_IAM \
     --region ap-southeast-1
   ```

2. **Get Role ARN**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name github-actions-role-nexus-ui-dev \
     --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
     --output text
   ```

3. **Repeat for test, stage, prod** (changing BranchName accordingly)

## GitHub Secrets Configuration

Go to: `https://github.com/YOUR_ORG/nexus-ui/settings/secrets/actions`

### Required AWS Role Secrets

| Secret Name | Environment | Description |
|-------------|-------------|-------------|
| `AWS_ROLE_TO_ASSUME_DEV` | Development | IAM role ARN for dev deployments |
| `AWS_ROLE_TO_ASSUME_TEST` | Test | IAM role ARN for test deployments |
| `AWS_ROLE_TO_ASSUME_STAGE` | Staging | IAM role ARN for stage deployments |
| `AWS_ROLE_TO_ASSUME_PROD` | Production | IAM role ARN for prod deployments |

### Example Role ARN Values

```
AWS_ROLE_TO_ASSUME_DEV   = arn:aws:iam::764119721991:role/GitHubActions-nexus-ui-dev
AWS_ROLE_TO_ASSUME_TEST  = arn:aws:iam::764119721991:role/GitHubActions-nexus-ui-test
AWS_ROLE_TO_ASSUME_STAGE = arn:aws:iam::764119721991:role/GitHubActions-nexus-ui-stage
AWS_ROLE_TO_ASSUME_PROD  = arn:aws:iam::764119721991:role/GitHubActions-nexus-ui-prod
```

**Note**: Authentication is handled by the backend API. No additional secrets are required.

## Environment Configuration

| Environment | Domain | API URL | S3 Bucket |
|-------------|--------|---------|-----------|
| dev | call-dev.totogicore.com | call-api-dev.totogicore.com | call-processing-dev-frontend |
| test | call-test.totogicore.com | call-api-test.totogicore.com | call-processing-test-frontend |
| stage | call-stage.totogicore.com | call-api-stage.totogicore.com | call-processing-stage-frontend |
| prod | call.totogicore.com | call-api.totogicore.com | call-processing-prod-frontend |

## Deployment Process

### Development Deployment

```bash
# Push to dev branch triggers automatic deployment
git checkout dev
git add .
git commit -m "feat: add new component"
git push origin dev
```

### Staging Deployment

```bash
# Merge dev to stage
git checkout stage
git merge dev
git push origin stage
```

### Production Deployment

```bash
# Merge stage to main
git checkout main
git merge stage
git push origin main
```

Or trigger manually:
1. Go to **Actions** tab
2. Select **Deploy to Production**
3. Click **Run workflow**
4. Type `DEPLOY_TO_PRODUCTION` in confirmation field
5. Click **Run workflow**

### Manual Deployment Options

| Option | Description |
|--------|-------------|
| `full` | Complete deployment (build + upload + invalidate) |
| `skip-build` | Use existing `dist/` folder |
| `skip-invalidate` | Skip CloudFront cache invalidation |

## Troubleshooting

### "Could not load credentials from any providers"

**Cause**: Missing or incorrect AWS role configuration

**Solution**:
1. Verify GitHub secrets are set correctly
2. Check IAM role exists:
   ```bash
   aws iam get-role --role-name GitHubActions-nexus-ui-dev
   ```
3. Verify OIDC trust policy includes your repository

### "S3 bucket does not exist"

**Cause**: S3 bucket not created

**Solution**: Ensure these buckets exist:
- `call-processing-dev-frontend`
- `call-processing-test-frontend`
- `call-processing-stage-frontend`
- `call-processing-prod-frontend`

### "CloudFront distribution not found"

**Cause**: No CloudFront distribution matches the S3 bucket or domain

**Solution**: The script will warn but continue. Manually create invalidation:
```bash
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

### "Build failed"

**Cause**: TypeScript errors or dependency issues

**Solution**:
1. Run `npm run build` locally to see errors
2. Fix TypeScript/ESLint errors
3. Ensure all dependencies are in `package.json`

## Best Practices

### Security
- Use OIDC instead of long-lived AWS keys
- Production deployments require manual confirmation
- Security scan runs before production deployment

### Deployment Flow
- Always deploy: dev → test → stage → prod
- Use pull requests for code review
- Test in lower environments before production

### Monitoring
- Check GitHub Actions logs for deployment status
- Monitor CloudFront cache invalidation progress
- Verify site accessibility after deployment

---

## Support

If you encounter issues:
1. Check this README for common solutions
2. Review GitHub Actions logs for specific errors
3. Run `./update-frontend.sh <env> --dry-run` locally to preview
4. Verify AWS credentials and permissions
