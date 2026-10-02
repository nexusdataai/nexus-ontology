#!/bin/bash

# Update S3 Bucket Policy Script
# This script updates the S3 bucket policy after CloudFormation deployment
# to grant CloudFront access without circular dependencies

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
STACK_NAME="tmf-oda-ui-stack"
AWS_REGION="us-east-1"

# External AWS Role Configuration
ROLE_ARN="arn:aws:iam::764119721991:role/AssumableExternalAccessRole"
EXTERNAL_PROFILE="external-access"
ASSUME_ROLE_SCRIPT="./deploy/assume-role-to-profile.sh"

# Function to assume external AWS role
assume_external_role() {
    print_status "Assuming external AWS role..."
    
    # Check if assume role script exists
    if [ ! -f "$ASSUME_ROLE_SCRIPT" ]; then
        print_error "Assume role script not found: $ASSUME_ROLE_SCRIPT"
        exit 1
    fi
    
    # Make the script executable
    chmod +x "$ASSUME_ROLE_SCRIPT"
    
    # Assume the role
    print_status "Running: $ASSUME_ROLE_SCRIPT $ROLE_ARN $EXTERNAL_PROFILE"
    if ! "$ASSUME_ROLE_SCRIPT" "$ROLE_ARN" "$EXTERNAL_PROFILE"; then
        print_error "Failed to assume external role"
        exit 1
    fi
    
    # Export the profile
    export AWS_PROFILE="$EXTERNAL_PROFILE"
    print_success "Successfully assumed role with profile: $AWS_PROFILE"
}

print_status "Updating S3 bucket policy for CloudFront access..."

# Check if we should use external role (check command line argument)
if [ "$1" = "external-aws" ]; then
    assume_external_role
fi

# Get stack outputs
print_status "Getting CloudFormation stack outputs..."
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' --output text)

if [ -z "$BUCKET_NAME" ] || [ -z "$DISTRIBUTION_ID" ]; then
    print_error "Could not retrieve bucket name or distribution ID from CloudFormation stack"
    exit 1
fi

print_status "Bucket Name: $BUCKET_NAME"
print_status "Distribution ID: $DISTRIBUTION_ID"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)

# Create bucket policy JSON
BUCKET_POLICY=$(cat <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::${BUCKET_NAME}/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::${ACCOUNT_ID}:distribution/${DISTRIBUTION_ID}"
                }
            }
        }
    ]
}
EOF
)

print_status "Applying bucket policy..."

# Apply the bucket policy
aws s3api put-bucket-policy \
    --bucket "$BUCKET_NAME" \
    --policy "$BUCKET_POLICY" \
    --region "$AWS_REGION"

print_success "Bucket policy updated successfully!"

# Invalidate CloudFront cache to ensure changes take effect
print_status "Invalidating CloudFront cache..."
INVALIDATION_ID=$(aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query 'Invalidation.Id' \
    --output text)

print_status "Invalidation created with ID: $INVALIDATION_ID"
print_status "Waiting for invalidation to complete..."

aws cloudfront wait invalidation-completed \
    --distribution-id "$DISTRIBUTION_ID" \
    --id "$INVALIDATION_ID"

print_success "CloudFront cache invalidated!"
print_success "S3 bucket policy update completed. Your site should now be accessible!"

echo ""
echo "🔗 Your website should now be available at:"
echo "   https://mtn.totogicore.com"
echo ""
echo "⏱️  Note: It may take 2-3 minutes for the changes to propagate globally."
echo ""
echo "💡 Usage:"
echo "   For standard AWS access: ./deploy/update-bucket-policy.sh"
echo "   For external role access: ./deploy/update-bucket-policy.sh external-aws" 