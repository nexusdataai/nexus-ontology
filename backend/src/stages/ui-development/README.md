# UI Development Stage

This stage provides comprehensive automated UI development using Claude API for both planning and code generation, with testing and deployment phases.

## Overview

The UI Development Stage automates the entire UI development lifecycle by:
- Reading and analyzing UI specifications
- Creating comprehensive planning documents (PRD, Phasewise Plan, Implementation Checklist)
- Generating UI code using Claude API
- Managing Git workflows and development branches
- Running automated tests and verifications
- Provisioning AWS infrastructure and deploying the application

## Stage Steps

### 1. Planning (5 minutes)
- Reads all UI specifications from `src/stages/ui-development/` directory
- Uses Claude API to intelligently generate documents based on all specifications:
  - Product Requirements Document (PRD) - comprehensive requirements based on specs
  - Phasewise Implementation Plan - detailed timeline with tasks
  - Implementation Checklist - actionable checklist items
- Falls back to template-based generation if Claude API is not available
- Saves all documents locally and to S3

### 2. Development (10 minutes)
- Clones/forks boilerplate repository
- Creates development branch
- Generates core UI components using Claude API:
  - Authentication module (Login, MFA, RBAC)
  - Dashboard components
  - Layout and navigation
  - API integration layer
- Commits generated code to Git

### 3. Tests (5 minutes)
- Runs code linting (ESLint)
- Performs TypeScript type checking
- Executes unit tests
- Runs integration tests
- Performs security scans
- Generates performance metrics
- Creates comprehensive test report

### 4. Deploy (7 minutes)
- Builds production bundle
- Provisions AWS infrastructure:
  - S3 bucket for static hosting
  - CloudFront distribution
  - Domain configuration
- Uploads build artifacts
- Generates deployment report
- Creates access guide and user documentation

## Specification Files

The stage reads specifications from the following files in `src/stages/ui-development/`:

1. **spec.md** - Main specification with boilerplate repo and development requirements
2. **Application-Generic-spec.md** - Application name, purpose, and core features
3. **Auth-RBAC.md** - Authentication and role-based access control requirements
4. **Solution-pages-dashboards.md** - UI pages and dashboard specifications
5. **chat-integration.md** - Chat and voice command integration specs
6. **tools-specification.md** - Tool integration specifications
7. **deployment-specification.md** - AWS deployment configuration
8. **environment-choice.md** - Environment configurations (dev/stage/prod)
9. **Application-configuration.md** - API endpoints and integration configs

## Configuration

**IMPORTANT**: This stage requires a valid Claude API key and will NOT use any mock generation. All content must be generated via Claude API.

```bash
# REQUIRED: Claude API Configuration (for planning AND code generation)
export CLAUDE_API_KEY="your-claude-api-key"  # or ANTHROPIC_API_KEY
# Claude API is REQUIRED for ALL content generation (PRD, Plans, Checklists, and Code)

# Optional: GitHub Configuration
export GITHUB_TOKEN="your-github-token"

# Optional: AWS Configuration (required only for deployment step)
export AWS_ACCOUNT_ID="your-aws-account-id"
export AWS_DEPLOYMENT_ROLE="your-deployment-role"
export AWS_REGION="us-east-1"
```

**Note**: Without Claude API key, both planning and development steps will fail. This ensures all generated content is created using Claude API, with no templates or fallbacks.

## Usage

### Basic Usage

```python
from src.stages.ui_development import UIDevelopmentStage

# Initialize the stage
stage = UIDevelopmentStage(
    journey_id="JRN-001",
    stage_id="ui_development",
    job_id="JOB-12345",
    region_name='us-east-1'
)

# Execute all steps
for step in stage.steps:
    result = stage.execute_step(step['id'], {})
    print(f"Step {step['name']}: {result['status']}")
```

### Test Script Usage

```bash
# Run full UI development workflow
python scripts/test_ui_development_stage.py

# Test only planning phase
python scripts/test_ui_development_stage.py --planning-only

# Show stage information
python scripts/test_ui_development_stage.py --info

# Test with custom specifications
python scripts/test_ui_development_stage.py --custom-spec
```

## Generated Artifacts

### Planning Phase
- **PRD.md** - Product Requirements Document
- **PhasewisePlan.md** - Detailed implementation timeline
- **ImplementationChecklist.md** - Comprehensive checklist with ~135 items

### Development Phase
- **Login.tsx** - Authentication page with MFA support
- **Dashboard.tsx** - Main dashboard with real-time widgets
- **Layout.tsx** - App layout with navigation
- **api.ts** - API client with error handling
- **DEVELOPMENT_REPORT.md** - Phase 1 development summary

### Testing Phase
- **TEST_REPORT.md** - Comprehensive test results including:
  - Unit test coverage
  - Integration test results
  - Linting and type checking results
  - Security scan findings
  - Performance metrics

### Deployment Phase
- **DEPLOYMENT_REPORT.md** - Infrastructure and deployment details
- **ACCESS_GUIDE.md** - How to access the deployed application
- **USER_GUIDE.md** - End-user documentation

## File Structure

```
ui-app/
├── src/
│   ├── components/
│   │   └── Layout.tsx
│   ├── pages/
│   │   ├── Login.tsx
│   │   └── Dashboard.tsx
│   ├── services/
│   │   └── api.ts
│   ├── utils/
│   ├── styles/
│   └── App.tsx
├── public/
├── deployment/
│   ├── DEPLOYMENT_REPORT.md
│   ├── ACCESS_GUIDE.md
│   └── USER_GUIDE.md
├── planning/
│   ├── PRD.md
│   ├── PhasewisePlan.md
│   └── ImplementationChecklist.md
├── package.json
├── vite.config.ts
├── DEVELOPMENT_REPORT.md
├── TEST_REPORT.md
└── README.md
```

## AI API Integration

### Claude API - REQUIRED for ALL Phases
The stage uses Claude API to generate both planning documents and production code:

**Planning Phase:**
- **Uses claude-3-haiku by default** (cheapest at $0.25/1M tokens, fastest)
- Analyzes all 9 specification files comprehensively
- Generates context-aware PRD with actual requirements from specs
- Creates realistic phasewise plans based on project complexity
- Produces detailed checklists with specific tasks from specifications

**Development Phase:**
- Generates production-ready React/TypeScript code
- Creates authentication, dashboard, and layout components
- Implements API integration layers
- Uses modern React patterns and best practices
- Includes proper error handling and accessibility features

**NO FALLBACK**: Fails if API key not configured or API calls fail
- Automatically tries alternative models if Haiku unavailable

### Generated Components

1. **Authentication Module**
   - Login page with form validation
   - Multi-factor authentication support
   - Session management
   - Role-based access control

2. **Dashboard Components**
   - Real-time data widgets
   - Charts and visualizations (using Recharts)
   - Key metrics display
   - Responsive grid layout

3. **Layout & Navigation**
   - App shell with navigation menu
   - Header with user profile
   - Sidebar navigation
   - Breadcrumb support

4. **API Integration**
   - REST API client
   - Authentication handling
   - Error management
   - Request/response interceptors

## AWS Deployment

The deployment phase provisions the following AWS resources:

- **S3 Bucket** - Static website hosting
- **CloudFront Distribution** - CDN for global distribution
- **Route 53** - Domain configuration (if configured)
- **SSL Certificate** - HTTPS support

### Deployment URLs

- S3 URL: `https://<bucket-name>.s3.<region>.amazonaws.com`
- CloudFront URL: `https://<distribution-id>.cloudfront.net`
- Custom Domain: `https://app-<job-id>.example.com`

## Testing

The stage includes comprehensive testing:

### Code Quality
- ESLint for code linting
- TypeScript type checking
- Prettier formatting validation

### Test Coverage
- Unit tests with Jest
- Integration tests
- E2E test structure (Cypress ready)
- Performance benchmarking

### Security
- Dependency vulnerability scanning
- Security header validation
- OWASP compliance checks

## Performance Metrics

The stage tracks and reports:
- Bundle size optimization
- Load time metrics (FCP, LCP, TTI)
- Lighthouse scores
- Code splitting effectiveness
- Caching strategies

## Logging

Detailed logs are created in multiple locations:
- Local file: `logs/ui_development_<job_id>_<timestamp>.log`
- Console output with emojis for clarity
- S3: `s3://transformation-journey-logs/journeys/<journey_id>/stages/ui_development/`

## Error Handling

The stage includes robust error handling:
- Fallback to mock generation when APIs unavailable
- Graceful degradation for missing specifications
- Detailed error reporting
- Automatic cleanup of temporary files

## Best Practices

1. **Specifications** - Keep specifications up-to-date and detailed
2. **API Key** - Configure Claude API key for all content generation
3. **Testing** - Always run tests before deployment
4. **Version Control** - Use meaningful commit messages
5. **Documentation** - Update specifications as requirements change

## Troubleshooting

### Common Issues

1. **Claude API not generating content**
   - Check API key configuration
   - Verify API endpoint is accessible
   - Review API rate limits and model availability

2. **Build failures**
   - Ensure Node.js 18+ is installed
   - Check package dependencies
   - Verify TypeScript configuration

3. **Deployment issues**
   - Verify AWS credentials
   - Check S3 bucket permissions
   - Ensure CloudFront is enabled

4. **Test failures**
   - Update test snapshots
   - Check mock data consistency
   - Verify test environment setup

## Future Enhancements

- Advanced testing with visual regression
- A/B testing infrastructure
- Progressive Web App (PWA) features
- Internationalization (i18n) support
- Micro-frontend architecture
- WebSocket/real-time features
- Advanced state management patterns

## Support

For issues or questions:
- Check the logs in `logs/` directory
- Review generated reports for detailed information
- Ensure all specifications are properly formatted
- Verify environment variables are configured

