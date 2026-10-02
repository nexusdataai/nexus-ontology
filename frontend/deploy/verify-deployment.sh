#!/bin/bash

# Deployment Verification Script
# Tests that the CloudFormation deployment is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STACK_NAME="nexus-ui-stack"
AWS_REGION="us-east-1"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to verify stack exists and is healthy
verify_stack() {
    print_status "Verifying CloudFormation stack..."
    
    local stack_status=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$stack_status" = "NOT_FOUND" ]; then
        print_error "Stack $STACK_NAME not found"
        return 1
    fi
    
    if [ "$stack_status" != "CREATE_COMPLETE" ] && [ "$stack_status" != "UPDATE_COMPLETE" ]; then
        print_error "Stack is in unexpected state: $stack_status"
        return 1
    fi
    
    print_success "Stack is healthy: $stack_status"
}

# Function to get stack outputs
get_stack_outputs() {
    print_status "Getting stack outputs..."
    
    BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
    DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' --output text)
    WEBSITE_URL=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' --output text)
    CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainName`].OutputValue' --output text)
    
    print_success "Retrieved stack outputs"
    echo "  Bucket: $BUCKET_NAME"
    echo "  Distribution: $DISTRIBUTION_ID"
    echo "  Website URL: $WEBSITE_URL"
    echo "  CloudFront Domain: $CLOUDFRONT_DOMAIN"
}

# Function to verify S3 bucket has files
verify_s3_content() {
    print_status "Verifying S3 bucket content..."
    
    local file_count=$(aws s3 ls "s3://$BUCKET_NAME/" --region "$AWS_REGION" | wc -l)
    
    if [ "$file_count" -eq 0 ]; then
        print_error "S3 bucket is empty - no files deployed"
        return 1
    fi
    
    # Check for essential files
    if ! aws s3 ls "s3://$BUCKET_NAME/index.html" --region "$AWS_REGION" > /dev/null 2>&1; then
        print_error "index.html not found in S3 bucket"
        return 1
    fi
    
    print_success "S3 bucket has content ($file_count items)"
}

# Function to verify bucket policy exists
verify_bucket_policy() {
    print_status "Verifying S3 bucket policy..."
    
    if ! aws s3api get-bucket-policy --bucket "$BUCKET_NAME" --region "$AWS_REGION" > /dev/null 2>&1; then
        print_error "S3 bucket policy not found"
        return 1
    fi
    
    print_success "S3 bucket policy exists"
}

# Function to verify CloudFront distribution
verify_cloudfront() {
    print_status "Verifying CloudFront distribution..."
    
    local distribution_status=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.Status' --output text)
    
    if [ "$distribution_status" != "Deployed" ]; then
        print_warning "CloudFront distribution not fully deployed: $distribution_status"
        print_warning "This may take 10-15 minutes after stack creation"
    else
        print_success "CloudFront distribution is deployed"
    fi
}

# Function to test website accessibility
test_website() {
    print_status "Testing website accessibility..."
    
    # Test CloudFront domain first
    local cf_response=$(curl -s -o /dev/null -w "%{http_code}" "https://$CLOUDFRONT_DOMAIN" || echo "000")
    
    if [ "$cf_response" = "200" ]; then
        print_success "CloudFront domain accessible: https://$CLOUDFRONT_DOMAIN"
    else
        print_error "CloudFront domain not accessible (HTTP $cf_response): https://$CLOUDFRONT_DOMAIN"
    fi
    
    # Test custom domain
    local custom_response=$(curl -s -o /dev/null -w "%{http_code}" "$WEBSITE_URL" || echo "000")
    
    if [ "$custom_response" = "200" ]; then
        print_success "Custom domain accessible: $WEBSITE_URL"
    else
        print_error "Custom domain not accessible (HTTP $custom_response): $WEBSITE_URL"
        print_warning "If this is a new deployment, DNS propagation may take a few minutes"
    fi
}

# Main verification function
main() {
    echo "🔍 Verifying Deployment"
    echo "======================="
    
    verify_stack || exit 1
    get_stack_outputs || exit 1
    verify_s3_content || exit 1
    verify_bucket_policy || exit 1
    verify_cloudfront || exit 1
    test_website
    
    echo ""
    echo "✅ Verification completed!"
    echo ""
    echo "🔗 Your application:"
    echo "   Primary URL: $WEBSITE_URL"
    echo "   CloudFront URL: https://$CLOUDFRONT_DOMAIN"
    echo ""
}

# Run verification
main "$@"