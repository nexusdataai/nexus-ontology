# alert-engine MCP Server - CloudFormation Deployment

This directory contains pure CloudFormation-based deployment automation for the alert-engine MCP Server running on AWS ECS with Fargate. It provides a complete, production-ready infrastructure deployment without CDK dependencies.

## 🏗️ Architecture Overview

The deployment creates a modern, scalable architecture:

```
Route53 → Application Load Balancer → ECS Fargate Tasks → S3
```

### Components

- **Main Stack**: Orchestrates all other stacks and manages dependencies
- **Global Stack**: Region-specific resources like SSL certificates
- **Network Stack**: VPC, subnets, ECS cluster, security groups
- **Storage Stack**: S3 bucket with lifecycle policies and encryption
- **Backend Stack**: ECS Fargate service with Application Load Balancer
- **Domain Stack**: Route53 records and SSL certificates (optional)

## 📁 Directory Structure

```
deploy/
├── cloudformation-main-template.yaml     # Main orchestrator stack
├── cloudformation-global-template.yaml   # Global/region-specific resources
├── cloudformation-network-template.yaml  # VPC, ECS Cluster, Security Groups
├── cloudformation-storage-template.yaml  # S3 Bucket for data storage
├── cloudformation-backend-template.yaml  # ECS Fargate service + ALB
├── cloudformation-domain-template.yaml   # Route53 records + SSL certs
├── config/
│   ├── dev.conf                          # Development environment config
│   ├── stage.conf                        # Staging environment config
│   └── prod.conf                         # Production environment config
├── deploy.sh                             # Main deployment script
├── cleanup-stacks.sh                     # Stack deletion script
├── verify-deployment.sh                  # Deployment verification
├── assume-role-to-profile.sh             # AWS role assumption helper
└── README.md                             # This file
```

## 🚀 Quick Start

### Prerequisites

- AWS CLI v2 configured with appropriate credentials
- bash shell
- curl (for health checks)
- jq (for JSON parsing in verification script)

### Basic Deployment

1. **Deploy to Development**:
   ```bash
   ./deploy.sh dev
   ```

2. **Deploy to Staging**:
   ```bash
   ./deploy.sh stage
   ```

3. **Deploy to Production**:
   ```bash
   ./deploy.sh prod
   ```

### With External AWS Role

If you need to assume an external role for deployment:

```bash
./deploy.sh dev external-aws
./deploy.sh prod external-aws
```

## ⚙️ Configuration

Each environment has its own configuration file in the `config/` directory. Key settings include:

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PROJECT_NAME` | Name of the project | `ecommerce-mcp` |
| `BASE_DOMAIN` | Your base domain | `promodeagro.com` |
| `SUBDOMAIN` | Environment subdomain | `api-dev` |
| `AWS_REGION` | AWS region for deployment | `us-east-1` |
| `DOCKER_IMAGE_URI` | ECR image URI | `851725323791.dkr.ecr.us-east-1.amazonaws.com/ecommerce-mcp-server-dev:latest` |
| `HOSTED_ZONE_ID` | Route53 hosted zone ID | `Z00062013820EO6BYULDB` |

### ECS Configuration

| Variable | Description | Dev | Stage | Prod |
|----------|-------------|-----|-------|------|
| `ECS_TASK_CPU` | CPU units (256-4096) | 512 | 1024 | 1024 |
| `ECS_TASK_MEMORY` | Memory in MiB | 1024 | 2048 | 2048 |
| `ECS_DESIRED_COUNT` | Number of tasks | 1 | 1 | 2 |
| `ENABLE_AUTO_SCALING` | Enable auto-scaling | false | true | true |

### Network Configuration

| Variable | Description | Dev | Stage | Prod |
|----------|-------------|-----|-------|------|
| `VPC_NAT_GATEWAYS` | Number of NAT gateways | 0 | 0 | 2 |
| `VPC_MAX_AZS` | Max availability zones | 2 | 2 | 2 |
| `ENABLE_DOMAIN_SETUP` | Enable Route53 domain | true | true | true |
| `CREATE_SSL_CERTIFICATE` | Create new SSL cert | false | false | false |

## 🛠️ Available Commands

### Main Deployment Script

```bash
# Full deployment (infrastructure + application)
./deploy.sh <environment>

# Infrastructure only (no Docker build/push)
./deploy.sh <environment> infrastructure-only

# Application only (Docker build/push + ECS update)
./deploy.sh <environment> application-only

# Cleanup stacks and exports
./deploy.sh <environment> cleanup-only

# Force cleanup (removes stuck stacks)
./deploy.sh <environment> force-cleanup

# With external AWS role
./deploy.sh <environment> external-aws

# External role + infrastructure only
./deploy.sh <environment> external-aws-infrastructure-only
```

### Verification Script

```bash
# Verify deployment health
./verify-deployment.sh <environment>
```

### Cleanup Script

```bash
# Delete all stacks for environment (⚠️ DESTRUCTIVE)
./cleanup-stacks.sh <environment>
```

## 📋 Deployment Process

The deployment follows this sequence:

1. **Validation**: Checks AWS CLI, configuration, and templates
2. **Main Stack**: Orchestrates all other stacks in dependency order
3. **Global Stack**: Creates region-specific resources like SSL certificates
4. **Network Stack**: Creates VPC, subnets, ECS cluster, security groups
5. **Storage Stack**: Creates S3 bucket with proper policies and lifecycle rules
6. **Backend Stack**: Deploys ECS service with load balancer
7. **Domain Stack**: Sets up Route53 records and SSL certificates (if enabled)
8. **Verification**: Displays deployment information and service URLs

## 🔧 Customization

### Environment-Specific Settings

Edit the configuration files in `config/` to customize:

- Resource sizing (CPU, memory, instance counts)
- Feature flags (authentication, domain setup, monitoring)
- Cost optimization settings (NAT gateways, auto-scaling)

### Template Modifications

The CloudFormation templates are modular and can be modified independently:

- **Main**: Adjust orchestration and dependencies
- **Global**: Modify region-specific resources and SSL certificates
- **Network**: Adjust VPC CIDR, subnet configuration
- **Storage**: Modify S3 lifecycle rules, encryption settings
- **Backend**: Change ECS configuration, health check settings
- **Domain**: Update SSL certificate settings, Route53 configuration

## 🔍 Monitoring and Troubleshooting

### Health Checks

Each deployment includes health endpoints:

- **Load Balancer**: `https://<alb-dns>/health`
- **Domain**: `https://<subdomain>.<domain>/health`
- **MCP Tools**: `https://<subdomain>.<domain>/tools`

Example for dev environment:
- Health: `https://api-dev.promodeagro.com/health`
- Tools: `https://api-dev.promodeagro.com/tools`

### CloudWatch Logs

Application logs are automatically sent to CloudWatch:
- Log Group: `/aws/ecs/<project-name>-<environment>`
- Retention: Configurable per environment (7-30 days)

### Verification

Use the verification script to check deployment health:

```bash
./verify-deployment.sh dev
```

This checks:
- ✅ CloudFormation stack status
- ✅ ECS service health
- ✅ Load balancer target health
- ✅ Application health endpoints

## 🛡️ Security Features

- **Network Security**: VPC with private/public subnets, security groups
- **Data Encryption**: S3 server-side encryption, ECS task secrets
- **Access Control**: IAM roles with least privilege principles
- **SSL/TLS**: Optional SSL certificates for HTTPS endpoints
- **Multi-Region**: Global template handles region-specific resources

## 💰 Cost Optimization

### By Environment

- **Development**: Single AZ, smaller instances, minimal logging
- **Staging**: No NAT gateways (public subnets only), moderate resources
- **Production**: Full high-availability, optimized for performance

### Cost Control Features

- Configurable NAT gateway count (major cost factor - dev uses 0 NAT gateways)
- ECS auto-scaling to match demand (disabled in dev for cost savings)
- S3 lifecycle rules for long-term storage costs
- CloudWatch log retention policies
- Single task in dev, multiple tasks with auto-scaling in production

## 🔄 Updates and Maintenance

### Updating the Application

1. Build and push new Docker image to ECR
2. Update `DOCKER_IMAGE_URI` in environment config
3. Run deployment: `./deploy.sh <environment>`

The deployment uses blue-green deployment strategy with circuit breaker for safe updates.

### Updating Infrastructure

1. Modify the appropriate CloudFormation template
2. Run deployment: `./deploy.sh <environment>`

CloudFormation will detect changes and update only affected resources.

## 🆘 Common Issues

### Deployment Failures

1. **Stack already exists errors**: Use update commands or check for naming conflicts
2. **Certificate validation timeouts**: Ensure DNS is properly configured
3. **ECS task failures**: Check CloudWatch logs for application errors

### Permission Issues

1. **Insufficient IAM permissions**: Ensure deployment role has necessary CloudFormation and service permissions
2. **Cross-account access**: Use external role assumption scripts

### Network Issues

1. **Health check failures**: Verify security group rules allow traffic on port 8000
2. **DNS resolution**: Check Route53 configuration and certificate validation

## 📞 Support

For issues or questions:

1. Check CloudWatch logs: `/aws/ecs/<project-name>-<environment>`
2. Verify stack status in CloudFormation console
3. Run verification script: `./verify-deployment.sh <environment>`
4. Check ECS service events in AWS console

---

**Note**: This deployment uses a main orchestrator stack that manages all component stacks. The architecture is region-agnostic and supports multi-region deployments with global resources managed separately.

