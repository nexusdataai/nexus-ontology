# TMF ODA Transformer UI Deployment

This directory contains everything needed to deploy your React UI application to AWS with the architecture:

**Route53 → AWS WAF → CloudFront (CDN) → S3**

## 🚀 Quick Start

### Prerequisites

1. **AWS CLI** installed and configured
   ```bash
   # Install AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Configure AWS CLI
   aws configure
   ```

2. **Node.js and npm** installed
   ```bash
   # Check if installed
   node --version
   npm --version
   ```

3. **Domain registered** and **Route53 Hosted Zone** created

4. **For External Role Access**: `jq` installed for JSON parsing
   ```bash
   # Install jq (if not already installed)
   sudo apt-get install jq  # Ubuntu/Debian
   # or
   brew install jq  # macOS
   ```

### Configuration

1. **Copy and modify the configuration file:**
   ```bash
   cp deploy/config.sh deploy/my-config.sh
   ```

2. **Edit `deploy/my-config.sh`:**
   ```bash
   # Required - Update these values
   export DOMAIN_NAME="myapp.yourdomain.com"
   export HOSTED_ZONE_ID="Z1D633PJN98FT9"  # Get from Route53 console
   ```

3. **Load your configuration:**
   ```bash
   source deploy/my-config.sh
   ```

### Deployment

1. **Make the script executable:**
   ```bash
   chmod +x deploy/deploy.sh
   ```

2. **Deploy everything:**
   ```bash
   ./deploy/deploy.sh
   ```

That's it! 🎉

### External Role Configuration (Optional)

If you need to deploy from an external machine using IAM role assumption:

1. **Configure the role in the deployment script:**
   ```bash
   # Edit deploy/deploy.sh and update these variables:
   ROLE_ARN="arn:aws:iam::764119721991:role/AssumableExternalAccessRole"
   EXTERNAL_PROFILE="external-access"
   ```

2. **Ensure the assume role script exists:**
   ```bash
   # The script deploy/assume-role-to-profile.sh should exist
   # A sample script is provided in the deployment package
   chmod +x deploy/assume-role-to-profile.sh
   ```

3. **Deploy with external role:**
   ```bash
   ./deploy/deploy.sh external-aws
   ```

## 📋 Deployment Options

The deployment script supports several modes:

### Standard Deployment (Direct AWS Access)

```bash
# Full deployment (recommended)
./deploy/deploy.sh

# Build application only
./deploy/deploy.sh build-only

# Deploy to existing infrastructure only
./deploy/deploy.sh deploy-only

# Deploy infrastructure only
./deploy/deploy.sh infrastructure-only
```

### External Role Deployment (Cross-Account Access)

For deployments from external machines that need to assume an AWS IAM role:

```bash
# Full deployment with external role assumption
./deploy/deploy.sh external-aws

# Build application only with external role
./deploy/deploy.sh external-aws-build-only

# Deploy to existing infrastructure only with external role
./deploy/deploy.sh external-aws-deploy-only

# Deploy infrastructure only with external role
./deploy/deploy.sh external-aws-infrastructure-only
```

The external role options will:
1. Assume the configured IAM role using the `assume-role-to-profile.sh` script
2. Set up the AWS profile for the session
3. Proceed with the deployment using the assumed role credentials

## 🏗️ Architecture Components

The CloudFormation template creates:

- **S3 Bucket**: Static website hosting
- **CloudFront Distribution**: Global CDN with custom domain
- **Route53 Record**: DNS routing to CloudFront
- **AWS WAF**: Web application firewall with managed rules
- **SSL Certificate**: Free SSL/TLS certificate from AWS Certificate Manager
- **Security**: Origin Access Control for secure S3 access

## 🔧 Troubleshooting

### Common Issues

1. **Domain/Hosted Zone not found**
   - Verify your domain is registered
   - Ensure Route53 hosted zone exists
   - Check the Hosted Zone ID is correct

2. **SSL Certificate validation stuck**
   - Ensure DNS records are properly configured
   - Wait 5-15 minutes for DNS propagation
   - Check Certificate Manager console

3. **AWS CLI not configured**
   ```bash
   aws configure
   aws sts get-caller-identity  # Verify configuration
   ```

4. **Build fails**
   ```bash
   npm install
   npm run build
   ```

### Checking Deployment Status

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name tmf-oda-ui-stack

# Check certificate validation
aws acm list-certificates --region us-east-1

# Check CloudFront distribution
aws cloudfront list-distributions
```

## 🛡️ Security Features

The deployment includes:

- **AWS WAF** with managed rule sets:
  - Common Rule Set (OWASP Top 10)
  - Known Bad Inputs Rule Set
- **HTTPS-only** access with redirect
- **Origin Access Control** for secure S3 access
- **Security headers** via CloudFront

## 💰 Cost Estimation

Approximate monthly costs for moderate traffic:

- **Route53**: $0.50/month (hosted zone)
- **CloudFront**: $0.085/GB + $0.0125/10k requests
- **S3**: $0.023/GB storage + $0.0004/1k requests
- **WAF**: $1.00/month + $0.60/million requests
- **Certificate Manager**: Free

**Total**: ~$2-10/month depending on traffic

## 🔄 Updates and Redeployment

To update your application:

```bash
# Make changes to your React app
# Then redeploy
./deploy/deploy.sh deploy-only
```

To update infrastructure:

```bash
# Modify cloudformation-template.yaml
# Then redeploy
./deploy/deploy.sh infrastructure-only
```

## 🗑️ Cleanup

To remove all resources:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name tmf-oda-ui-stack

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name tmf-oda-ui-stack
```

## 📞 Support

If you encounter issues:

1. Check the AWS CloudFormation console for stack events
2. Review CloudWatch logs for Lambda functions (if any)
3. Verify your AWS permissions include:
   - CloudFormation full access
   - S3 full access
   - CloudFront full access
   - Route53 full access
   - Certificate Manager full access
   - WAF full access 