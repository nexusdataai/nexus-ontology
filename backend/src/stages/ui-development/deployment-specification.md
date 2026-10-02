# Deployment Specification

## AWS Account Configuration

### Account Structure
```yaml
organization:
  master_account: "123456789012"
  
  accounts:
    production:
      id: "111111111111"
      name: "prod-alert-engine"
      region: "us-east-1"
      backup_region: "us-west-2"
    
    staging:
      id: "222222222222"
      name: "stage-alert-engine"
      region: "us-east-1"
    
    development:
      id: "333333333333"
      name: "dev-alert-engine"
      region: "us-east-1"
    
    shared_services:
      id: "444444444444"
      name: "shared-services"
      purpose: "DNS, Certificates, Logs"

  cross_account_roles:
    deployment_role: "arn:aws:iam::*:role/DeploymentRole"
    read_only_role: "arn:aws:iam::*:role/ReadOnlyRole"
```

## Domain Configuration

### DNS Setup
```typescript
interface DomainConfig {
  zones: {
    production: {
      domain: "alertengine.com";
      hostedZoneId: "Z1234567890ABC";
      certificateArn: "arn:aws:acm:us-east-1:111111111111:certificate/abc-123";
    };
    
    staging: {
      domain: "stage.alertengine.com";
      hostedZoneId: "Z0987654321XYZ";
      certificateArn: "arn:aws:acm:us-east-1:222222222222:certificate/def-456";
    };
    
    development: {
      domain: "dev.alertengine.com";
      hostedZoneId: "Z1111111111DEV";
      certificateArn: "arn:aws:acm:us-east-1:333333333333:certificate/ghi-789";
    };
  };
  
  subdomains: {
    app: "";                    // alertengine.com
    api: "api";                 // api.alertengine.com
    admin: "admin";             // admin.alertengine.com
    docs: "docs";               // docs.alertengine.com
    status: "status";           // status.alertengine.com
  };
}
```

### SSL Certificates
```yaml
certificates:
  wildcard:
    domains:
      - "*.alertengine.com"
      - "alertengine.com"
    validation: "DNS"
    provider: "AWS Certificate Manager"
    auto_renewal: true
  
  specific:
    - domain: "api.alertengine.com"
      type: "EV SSL"  # Extended Validation
      provider: "DigiCert"
    
    - domain: "admin.alertengine.com"
      type: "OV SSL"  # Organization Validation
      provider: "AWS Certificate Manager"
```

## CDN Configuration

### CloudFront Distribution
```typescript
interface CloudFrontConfig {
  distribution: {
    origins: {
      s3: {
        domainName: "alert-engine-ui-prod.s3.amazonaws.com";
        originPath: "";
        s3OriginConfig: {
          originAccessIdentity: "origin-access-identity/cloudfront/ABCDEFG";
        };
      };
      
      api: {
        domainName: "api.alertengine.com";
        customOriginConfig: {
          HTTPPort: 80;
          HTTPSPort: 443;
          originProtocolPolicy: "https-only";
        };
      };
    };
    
    behaviors: {
      default: {
        targetOriginId: "s3";
        viewerProtocolPolicy: "redirect-to-https";
        allowedMethods: ["GET", "HEAD", "OPTIONS"];
        compress: true;
        cachePolicyId: "Managed-CachingOptimized";
      };
      
      api: {
        pathPattern: "/api/*";
        targetOriginId: "api";
        viewerProtocolPolicy: "https-only";
        allowedMethods: ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"];
        cachePolicyId: "Managed-CachingDisabled";
      };
    };
    
    customErrorResponses: [
      {
        errorCode: 404,
        responseCode: 200,
        responsePagePath: "/index.html",
        errorCachingMinTTL: 300
      },
      {
        errorCode: 403,
        responseCode: 200,
        responsePagePath: "/index.html",
        errorCachingMinTTL: 300
      }
    ];
  };
}
```

## S3 Bucket Configuration

### Bucket Structure
```yaml
buckets:
  ui_hosting:
    production:
      name: "alert-engine-ui-prod"
      region: "us-east-1"
      versioning: true
      encryption: "AES256"
      lifecycle:
        - rule: "delete-old-versions"
          days: 30
      replication:
        destination: "alert-engine-ui-prod-backup"
        region: "us-west-2"
    
    staging:
      name: "alert-engine-ui-stage"
      region: "us-east-1"
      versioning: true
      encryption: "AES256"
      lifecycle:
        - rule: "delete-old-versions"
          days: 7
    
    development:
      name: "alert-engine-ui-dev"
      region: "us-east-1"
      versioning: false
      encryption: "AES256"
  
  assets:
    name: "alert-engine-assets"
    public_read: true
    cors_enabled: true
    
  logs:
    name: "alert-engine-logs"
    lifecycle:
      - rule: "archive-to-glacier"
        days: 90
      - rule: "delete-old-logs"
        days: 365
```

## Infrastructure as Code

### CloudFormation Templates
```yaml
templates:
  main:
    file: "infrastructure/cloudformation/main.yaml"
    parameters:
      Environment: !Ref Environment
      DomainName: !Ref DomainName
      CertificateArn: !Ref CertificateArn
    
    resources:
      - S3Bucket
      - CloudFrontDistribution
      - Route53RecordSet
      - WAFWebACL
      - Lambda@Edge Functions
  
  cognito:
    file: "infrastructure/cloudformation/cognito.yaml"
    parameters:
      UserPoolName: !Sub "${Environment}-alert-engine-users"
      
  monitoring:
    file: "infrastructure/cloudformation/monitoring.yaml"
    resources:
      - CloudWatchDashboard
      - SNSTopic
      - CloudWatchAlarms
```

### Terraform Alternative
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket = "alert-engine-terraform-state"
    key    = "ui/terraform.tfstate"
    region = "us-east-1"
  }
}

module "cdn" {
  source = "./modules/cdn"
  
  domain_name     = var.domain_name
  certificate_arn = var.certificate_arn
  s3_bucket_name  = var.s3_bucket_name
}

module "monitoring" {
  source = "./modules/monitoring"
  
  cloudfront_id = module.cdn.distribution_id
  alert_email   = var.ops_email
}
```

## Deployment Pipeline

### GitHub Actions Workflow
```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test
      
      - name: Build application
        run: npm run build
        env:
          VITE_API_BASE_URL: ${{ secrets.PROD_API_URL }}
          VITE_APP_ENV: production
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: dist
          path: dist/
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOYMENT_ROLE }}
          aws-region: us-east-1
      
      - name: Deploy to S3
        run: |
          aws s3 sync dist/ s3://${{ secrets.S3_BUCKET_NAME }} --delete
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.CLOUDFRONT_ID }} \
            --paths "/*"
```

## Security Configuration

### WAF Rules
```typescript
interface WAFConfiguration {
  webACL: {
    rules: [
      {
        name: "RateLimitRule";
        priority: 1;
        statement: {
          rateBasedStatement: {
            limit: 2000;
            aggregateKeyType: "IP";
          };
        };
        action: "BLOCK";
      },
      {
        name: "GeoBlockingRule";
        priority: 2;
        statement: {
          geoMatchStatement: {
            countryCodes: ["CN", "RU", "KP"];
          };
        };
        action: "BLOCK";
      },
      {
        name: "SQLiRule";
        priority: 3;
        managedRuleGroup: "AWSManagedRulesSQLiRuleSet";
        action: "BLOCK";
      }
    ];
  };
}
```

### Security Headers
```javascript
// Lambda@Edge function for security headers
exports.handler = async (event) => {
  const response = event.Records[0].cf.response;
  const headers = response.headers;
  
  headers['strict-transport-security'] = [{
    key: 'Strict-Transport-Security',
    value: 'max-age=31536000; includeSubDomains; preload'
  }];
  
  headers['x-content-type-options'] = [{
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  }];
  
  headers['x-frame-options'] = [{
    key: 'X-Frame-Options',
    value: 'DENY'
  }];
  
  headers['x-xss-protection'] = [{
    key: 'X-XSS-Protection',
    value: '1; mode=block'
  }];
  
  headers['referrer-policy'] = [{
    key: 'Referrer-Policy',
    value: 'strict-origin-when-cross-origin'
  }];
  
  headers['content-security-policy'] = [{
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline';"
  }];
  
  return response;
};
```

## Monitoring & Alerting

### CloudWatch Configuration
```yaml
dashboards:
  main:
    name: "AlertEngine-Production"
    widgets:
      - type: "metric"
        title: "CloudFront Requests"
        metric: "AWS/CloudFront/Requests"
      
      - type: "metric"
        title: "4xx/5xx Errors"
        metrics:
          - "AWS/CloudFront/4xxErrorRate"
          - "AWS/CloudFront/5xxErrorRate"
      
      - type: "metric"
        title: "Origin Latency"
        metric: "AWS/CloudFront/OriginLatency"
      
      - type: "log"
        title: "Recent Errors"
        query: "fields @timestamp, status | filter status >= 400"

alarms:
  high_error_rate:
    metric: "4xxErrorRate"
    threshold: 5
    comparison: "GreaterThanThreshold"
    period: 300
    evaluationPeriods: 2
    
  high_latency:
    metric: "OriginLatency"
    threshold: 1000
    comparison: "GreaterThanThreshold"
    period: 300
    evaluationPeriods: 3
```

## Deployment Scripts

### Deployment Script
```bash
#!/bin/bash
# deploy.sh

ENVIRONMENT=$1
AWS_PROFILE=$2

# Load configuration
source ./deploy/config/${ENVIRONMENT}.conf

echo "🚀 Deploying to ${ENVIRONMENT}..."

# Build application
echo "📦 Building application..."
npm run build:${ENVIRONMENT}

# Deploy to S3
echo "☁️ Uploading to S3..."
aws s3 sync dist/ s3://${S3_BUCKET} --delete --profile ${AWS_PROFILE}

# Invalidate CloudFront
echo "🔄 Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id ${CLOUDFRONT_ID} \
  --paths "/*" \
  --profile ${AWS_PROFILE}

# Update Route53 if needed
if [ "$UPDATE_DNS" = "true" ]; then
  echo "🌐 Updating DNS records..."
  aws route53 change-resource-record-sets \
    --hosted-zone-id ${HOSTED_ZONE_ID} \
    --change-batch file://dns-update.json \
    --profile ${AWS_PROFILE}
fi

echo "✅ Deployment complete!"
```

## ✅ Deployment Checklist

### Pre-Deployment
- [ ] AWS accounts created and configured
- [ ] IAM roles and policies defined
- [ ] Domain registered and DNS configured
- [ ] SSL certificates obtained and validated
- [ ] S3 buckets created with proper permissions
- [ ] CloudFront distribution configured
- [ ] WAF rules configured

### Infrastructure Setup
- [ ] CloudFormation/Terraform templates tested
- [ ] VPC and networking configured
- [ ] Security groups and NACLs defined
- [ ] Monitoring dashboards created
- [ ] Alarms and notifications configured
- [ ] Backup strategy implemented

### CI/CD Pipeline
- [ ] GitHub Actions workflow configured
- [ ] Secrets and environment variables set
- [ ] Build process optimized
- [ ] Test automation integrated
- [ ] Deployment scripts tested
- [ ] Rollback procedure documented

### Security
- [ ] WAF rules active
- [ ] Security headers configured
- [ ] CSP policy defined
- [ ] SSL/TLS properly configured
- [ ] Secrets management in place
- [ ] Audit logging enabled

### Post-Deployment
- [ ] Smoke tests passing
- [ ] Performance benchmarks met
- [ ] Monitoring confirmed working
- [ ] DNS propagation complete
- [ ] CDN cache primed
- [ ] Documentation updated

## 📝 Important Notes

1. **Zero Downtime**: Use blue-green deployments for production
2. **Rollback Plan**: Always test rollback procedure before deployment
3. **Cost Optimization**: Use CloudFront caching aggressively
4. **Security First**: Never expose S3 buckets directly
5. **Monitoring**: Set up alerts before issues occur
6. **Documentation**: Keep runbooks updated

---

*This specification defines the complete deployment architecture and process. Coordinate with DevOps team for implementation and with Security team for compliance review.*
