# Nexus Telco UI - AI-Powered Call Analytics Platform

> **Enterprise Call Analytics Dashboard**  
> React-based frontend for comprehensive call analytics with Webex, Salesforce, and Office 365 integrations.

## Table of Contents

- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Development Workflow](#development-workflow)
- [Deployment Scripts](#deployment-scripts)
- [Docker & Container Management](#docker--container-management)
- [AWS Credentials](#aws-credentials)
- [Environment Configuration](#environment-configuration)
- [Technology Stack](#technology-stack)

---

## Quick Start

### Prerequisites

- Node.js v18+ (recommended)
- npm v8+ or bun
- Docker (for container builds)
- AWS CLI (for deployments)

### 1. Clone and Install

```bash
git clone <repo-url>
cd nexus-ui
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local
```

### 3. Run Locally (No Auth - Recommended for Development)

```bash
# Edit .env.local and set:
# VITE_BYPASS_AUTH=true
# VITE_API_BASE_URL=http://localhost:8000

npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Local Development

### Option 1: Run Without Authentication (Fastest)

Best for UI development when you don't need backend features.

```bash
# .env.local
VITE_BYPASS_AUTH=true
VITE_DATA_SOURCE=json          # Use mock data
VITE_ENABLE_FALLBACK=true
```

```bash
npm run dev
```

### Option 2: Run With Local Backend

Connect to the locally running backend API.

```bash
# .env.local
VITE_BYPASS_AUTH=true
VITE_API_BASE_URL=http://localhost:8000
VITE_DATA_SOURCE=api
```

```bash
# Terminal 1: Start backend (in nexus-backend/)
cd ../nexus-backend
./start_gateway.sh

# Terminal 2: Start frontend
npm run dev
```

### Option 3: Run With Cognito Authentication

For testing the full authentication flow.

```bash
# .env.local
VITE_BYPASS_AUTH=false
VITE_API_BASE_URL=http://localhost:8000
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_XXXXXXX
VITE_COGNITO_CLIENT_ID=your-client-id
VITE_COGNITO_DOMAIN=your-domain.auth.ap-southeast-1.amazoncognito.com
VITE_OAUTH_REDIRECT_SIGNIN=http://localhost:5173/auth/callback
VITE_OAUTH_REDIRECT_SIGNOUT=http://localhost:5173/login
```

### Option 4: Connect to Dev/Prod API

Test against deployed environments.

```bash
# .env.local - Connect to Dev
VITE_BYPASS_AUTH=true
VITE_API_BASE_URL=https://call-api-dev.totogicore.com
VITE_DATA_SOURCE=api

# .env.local - Connect to Prod
VITE_BYPASS_AUTH=true
VITE_API_BASE_URL=https://call-api.totogicore.com
VITE_DATA_SOURCE=api
```

---

## Development Workflow

### Feature Development

1. **Create feature branch**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Start development server with hot reload**
   ```bash
   npm run dev
   ```

3. **Make changes** - Files in `src/` auto-reload in browser

4. **Run linting and type checks**
   ```bash
   npm run lint
   npm run type-check
   ```

5. **Build and test locally**
   ```bash
   npm run build
   npm run preview    # Preview production build
   ```

6. **Commit and push**
   ```bash
   git add .
   git commit -m "feat: description"
   git push origin feature/my-feature
   ```

### Updating Local Running Instance

When making changes during development:

- **Source code changes**: Automatically hot-reloaded (no action needed)
- **Environment changes**: Restart dev server (`Ctrl+C` then `npm run dev`)
- **Dependency changes**: Re-install and restart
  ```bash
  npm install
  npm run dev
  ```

### Available npm Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Build production bundle |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint |
| `npm run clean` | Remove dist folder |

---

## Deployment Scripts

### Update Dev Environment: `./update-frontend.sh`

**Quick deployment to dev/stage/prod** - builds, uploads to S3, invalidates CloudFront.

```bash
# Deploy to dev environment
./update-frontend.sh dev

# Deploy to staging
./update-frontend.sh stage

# Deploy to production
./update-frontend.sh prod

# Options
./update-frontend.sh dev --skip-build      # Use existing dist/
./update-frontend.sh dev --skip-invalidate # Skip CloudFront invalidation
./update-frontend.sh dev --dry-run         # Preview without changes
./update-frontend.sh dev --profile myprofile
```

**Environment URLs:**
| Environment | Frontend URL | API URL |
|-------------|--------------|---------|
| dev | https://call-dev.totogicore.com | https://call-api-dev.totogicore.com |
| stage | https://call-stage.totogicore.com | https://call-api-stage.totogicore.com |
| prod | https://call.totogicore.com | https://call-api.totogicore.com |

### Build and Upload: `./build-and-upload.sh`

**Build and upload zip to S3** - useful for artifact storage or manual deployments.

```bash
# Upload to S3 bucket root
./build-and-upload.sh my-bucket

# Upload to specific path
./build-and-upload.sh my-bucket nexus-ui/builds

# Windows
build-and-upload.bat my-bucket
```

Creates versioned zip: `nexus-ui-{version}.zip`

---

## Docker & Container Management

### Build Docker Image: `./build.sh`

**Full CI/CD pipeline** - builds Docker image, runs security scans, pushes to AWS ECR.

```bash
# Full build, scan, and push to ECR
./build.sh

# Build with specific tag
./build.sh v1.2.3

# Build without pushing to ECR (local only)
./build.sh --no-push

# Build without security scanning
./build.sh --no-scan

# Build without tests
./build.sh --no-test

# Force rebuild without Docker cache
./build.sh --no-cache

# Specify AWS profile/region
./build.sh --profile external-access --region ap-southeast-1
```

**What it does:**
1. Checks prerequisites (Docker, AWS CLI, Trivy)
2. Logs into AWS ECR
3. Creates ECR repository if needed
4. Builds Docker image with BuildKit
5. Runs container tests
6. Scans for vulnerabilities (Trivy + ECR)
7. Pushes to ECR
8. Generates security reports

**Environment Variables:**
```bash
SKIP_TESTS=true ./build.sh        # Skip tests
SKIP_SCAN=true ./build.sh         # Skip security scans
SKIP_PUSH=true ./build.sh         # Skip ECR push
NO_CACHE=true ./build.sh          # Disable Docker cache
AWS_PROFILE=external-access       # AWS profile (default)
AWS_REGION=ap-southeast-1         # AWS region (default)
```

### Rebuild and Test: `./rebuild-and-test.sh`

**Complete local rebuild and test cycle** - stops containers, rebuilds image, runs tests.

```bash
# Full rebuild and test
./rebuild-and-test.sh

# Skip tests (faster)
./rebuild-and-test.sh --skip-tests

# Force rebuild (clear Docker cache)
./rebuild-and-test.sh --force-rebuild

# Minimal output
./rebuild-and-test.sh --quiet

# No Docker cache
./rebuild-and-test.sh --no-cache

# Combine options
./rebuild-and-test.sh --skip-tests --quiet
```

**What it does:**
1. Refreshes AWS credentials
2. Stops and removes existing containers
3. Removes existing Docker image
4. Rebuilds image from scratch
5. Starts fresh container on port 8080
6. Runs health checks and basic tests

**After running:**
- UI available at: http://localhost:8080
- Health check: http://localhost:8080/health

**Container Management:**
```bash
docker logs -f nexus-ui         # View logs
docker stop nexus-ui            # Stop container
docker restart nexus-ui         # Restart container
docker exec -it nexus-ui sh     # Shell access
```

---

## AWS Credentials

### Refresh Credentials: `./refresh-aws-credentials.sh`

Checks and refreshes AWS credentials for deployment operations.

```bash
./refresh-aws-credentials.sh
```

**What it does:**
1. Checks AWS CLI installation
2. Verifies current credentials
3. Attempts to refresh if expired
4. Provides manual login instructions if needed

**Manual credential refresh:**
```bash
# For AWS SSO
aws sso login --profile external-access

# For standard credentials
aws configure --profile external-access
```

**Note:** The UI can run without AWS credentials. They're only needed for:
- Cognito authentication
- S3 storage access
- ECR image push
- CloudFront operations

---

## Environment Configuration

### Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Template with all available options |
| `.env.local` | Your local configuration (git-ignored) |
| `.env.local.example` | Template for build/AWS settings |
| `public/config.json` | Runtime config (generated for deployments) |

### Key Environment Variables

**API Configuration:**
```bash
VITE_API_BASE_URL=http://localhost:8000   # Backend API URL
VITE_API_TIMEOUT=30000                     # Request timeout (ms)
```

**Authentication:**
```bash
VITE_BYPASS_AUTH=true                      # Skip auth (dev mode)
VITE_COGNITO_USER_POOL_ID=ap-southeast-1_xxx
VITE_COGNITO_CLIENT_ID=your-client-id
VITE_COGNITO_DOMAIN=your-domain.auth.region.amazoncognito.com
```

**Data Source:**
```bash
VITE_DATA_SOURCE=api                       # 'api' or 'json' (mock)
VITE_ENABLE_FALLBACK=true                  # Fallback to mock if API fails
```

**AWS/Build Settings (in .env.local):**
```bash
AWS_REGION=ap-southeast-1
AWS_PROFILE=external-access
SKIP_TESTS=false
SKIP_SCAN=false
SKIP_PUSH=false
```

### Configuration Priority

1. Environment variables (`.env.local`) - checked first
2. `/public/config.json` - fallback
3. Default values - last resort

---

## Technology Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS
- **UI Components**: Radix UI, shadcn/ui
- **Charts**: Recharts, Mapbox GL
- **Build Tool**: Vite
- **State Management**: React Query
- **Routing**: React Router DOM
- **Container**: Docker, nginx
- **Cloud**: AWS (S3, CloudFront, ECR, Cognito)

---

## Quick Reference

### Daily Development
```bash
npm run dev                           # Start dev server
./update-frontend.sh dev              # Deploy to dev
```

### Docker Testing
```bash
./rebuild-and-test.sh --skip-tests    # Quick local container
./build.sh --no-push                  # Build without ECR push
```

### Production Deployment
```bash
./refresh-aws-credentials.sh          # Ensure credentials valid
./build.sh v1.0.0                     # Build and push to ECR
./update-frontend.sh prod             # Deploy to production
```

---

*Built for enterprise call analytics with Webex, Salesforce, and Office 365 integration.*
