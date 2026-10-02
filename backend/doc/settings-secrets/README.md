# Settings & Secrets Management

This directory contains comprehensive documentation for how settings, configurations, and secrets are managed in the Nexus Telco Backend across different deployment environments.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Naming Conventions](naming-conventions.md) | Resource naming patterns and SSM parameter structure |
| [Configuration Sources](configuration-sources.md) | Configuration hierarchy and environment detection |
| [SSM Parameters Reference](ssm-parameters.md) | Complete list of SSM parameters with CLI commands |
| [Secrets Manager Reference](secrets-manager.md) | Secrets structure and loading patterns |
| [AWS Resources](aws-resources.md) | DynamoDB tables and S3 buckets |
| [Code Flow](code-flow.md) | Configuration initialization and code files |
| [Configuration APIs](config-apis.md) | Runtime configuration endpoints |
| [IAM Permissions](iam-permissions.md) | Required IAM policies |
| [Troubleshooting](troubleshooting.md) | Common issues and debugging |

### Deployment Scenarios

| Document | Description |
|----------|-------------|
| [Local with LocalStack](deployment-scenarios/localstack.md) | Development with local AWS emulation |
| [Local with Real AWS](deployment-scenarios/local-aws.md) | Development against real AWS resources |
| [ECS Fargate](deployment-scenarios/ecs-fargate.md) | Production deployment on ECS |
| [EKS (Kubernetes)](deployment-scenarios/eks-kubernetes.md) | Deployment on Amazon EKS |

---

## Quick Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION MANAGEMENT OVERVIEW                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Configuration Sources                           │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │   │
│  │  │ SSM Parameter   │  │ AWS Secrets     │  │ Environment     │     │   │
│  │  │ Store           │  │ Manager         │  │ Variables       │     │   │
│  │  │ (Non-sensitive) │  │ (Sensitive)     │  │ (.env.local)    │     │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘     │   │
│  │           │                    │                    │               │   │
│  │           └────────────────────┼────────────────────┘               │   │
│  │                                │                                    │   │
│  │                                ▼                                    │   │
│  │                    ┌─────────────────────┐                          │   │
│  │                    │   ConfigProvider    │                          │   │
│  │                    │   (Singleton)       │                          │   │
│  │                    └─────────────────────┘                          │   │
│  │                                │                                    │   │
│  │                                ▼                                    │   │
│  │                    ┌─────────────────────┐                          │   │
│  │                    │  Application Code   │                          │   │
│  │                    │  Services/Stages    │                          │   │
│  │                    └─────────────────────┘                          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Configuration Priority (highest to lowest):                               │
│  1. SSM Parameter Store (on ECS/AWS)                                       │
│  2. Environment variables (from .env.local or ECS task definition)         │
│  3. Default values (hardcoded fallbacks)                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Principles

| Principle | Description |
|-----------|-------------|
| **Environment-Aware** | Configuration adapts based on detected environment |
| **Secrets Separation** | Sensitive data stored in Secrets Manager, not SSM |
| **Naming Convention** | All resources follow `call-processing-{env}-{name}` pattern |
| **Caching** | SSM and Secrets are cached with 5-minute TTL |
| **Failover** | Falls back to env vars if AWS services unavailable |

## Configuration Loading Summary

| Environment | Config Source | AWS Services |
|-------------|---------------|--------------|
| LocalStack | `.env.local` | LocalStack (localhost:4566) |
| Local + AWS | `.env.local` | Real AWS (S3, DynamoDB) |
| ECS | SSM + Secrets Manager | Real AWS (all services) |
| EKS (IRSA) | SSM + Secrets Manager | Real AWS (all services) |
| EKS (ConfigMap) | K8s ConfigMap/Secrets | Real AWS (S3, DynamoDB) |

## Environment Variable Summary

| Category | Count | Storage |
|----------|-------|---------|
| AWS Core | 5 | SSM |
| Server | 7 | SSM |
| WXCC Simulator | 6 | SSM |
| Call Processing | 9 | SSM |
| Cognito | 5 | SSM |
| License | 4 | Secrets Manager |
| CloudWatch | 4 | SSM |
| **Total** | ~40 | SSM + Secrets |

---

*Last Updated: January 2026*  
*Document Version: 1.0*
