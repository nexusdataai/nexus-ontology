#!/bin/bash
# CloudFront + S3 Environment Configuration
# Source this file to load environment variables

export S3_BUCKET_NAME="ai-engine-test-reports"
export CLOUDFRONT_DOMAIN="d37vwg02pj6oqg.cloudfront.net"
export S3_REGION="us-east-1"
export UPLOAD_TO_S3="true"

echo "✅ CloudFront environment loaded"
echo "   Bucket: $S3_BUCKET_NAME"
echo "   Domain: $CLOUDFRONT_DOMAIN"
echo "   Region: $S3_REGION"
echo
echo "Ready to upload reports:"
echo "   ./tests/run_tests.sh unit"
