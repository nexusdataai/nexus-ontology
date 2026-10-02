#!/bin/bash

# Refresh AWS Credentials Script
# This script logs into AWS and refreshes credentials if needed

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# AWS Profile configuration
AWS_PROFILE="${AWS_PROFILE:-external-access}"

echo "=========================================="
echo "AWS Credentials Refresh Script"
echo "=========================================="
echo "Using AWS Profile: $AWS_PROFILE"
echo ""

# Step 1: Check if AWS CLI is installed
echo "Step 1: Checking AWS CLI installation..."
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    echo ""
    echo "To install AWS CLI:"
    echo "  https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

echo "✅ AWS CLI found: $(aws --version 2>&1 | cut -d' ' -f1)"
echo ""

# Step 2: Check current credentials status
echo "Step 2: Checking current AWS credentials..."
if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
    echo "✅ AWS credentials are currently valid"
    echo ""
    echo "Current identity:"
    aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null | jq -r '. | "   User ID: \(.UserId)\n   Account: \(.Account)\n   ARN: \(.Arn)"' 2>/dev/null || \
        aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null
    echo ""
    
    # Check expiration time if possible
    if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        echo "Credentials are working. They may still expire later."
        echo "If you experience authentication issues, run: aws sso login --profile $AWS_PROFILE"
    fi
else
    echo "⚠️  AWS credentials are expired or not configured"
    echo ""
    echo "Step 3: Attempting to refresh credentials..."
    
    # Check if aws-login.sh script exists
    if [ -f "$SCRIPT_DIR/aws-login.sh" ]; then
        echo "Running aws-login.sh..."
        if bash "$SCRIPT_DIR/aws-login.sh"; then
            echo "✅ Credentials refreshed via aws-login.sh"
        else
            echo "❌ aws-login.sh failed"
            echo ""
            echo "Please log in manually:"
            echo "  aws sso login --profile $AWS_PROFILE"
            exit 1
        fi
    else
        echo "aws-login.sh script not found"
        echo ""
        echo "Please log in manually using one of these methods:"
        echo ""
        echo "For AWS SSO:"
        echo "  aws sso login --profile $AWS_PROFILE"
        echo ""
        echo "For standard credentials:"
        echo "  aws configure --profile $AWS_PROFILE"
        echo ""
        exit 1
    fi
    
    # Verify credentials after refresh attempt
    echo ""
    echo "Verifying credentials after refresh..."
    if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        echo "✅ AWS credentials refreshed successfully"
        echo ""
        echo "Current identity:"
        aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null | jq -r '. | "   User ID: \(.UserId)\n   Account: \(.Account)\n   ARN: \(.Arn)"' 2>/dev/null || \
            aws sts get-caller-identity --profile "$AWS_PROFILE" 2>/dev/null
    else
        echo "❌ Failed to refresh credentials"
        echo ""
        echo "Please log in manually:"
        echo "  aws sso login --profile $AWS_PROFILE"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "Credential check complete!"
echo "=========================================="
echo ""
echo "Notes:"
echo "  • Nexus Telco UI can run without AWS credentials"
echo "  • AWS credentials are only needed for:"
echo "    - Cognito authentication"
echo "    - S3 storage access"
echo "    - Other AWS service integrations"
echo ""
echo "To manually refresh at any time:"
echo "  aws sso login --profile $AWS_PROFILE"
echo ""
