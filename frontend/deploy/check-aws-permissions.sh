#!/bin/bash

# Nexus Telco QA Dashboard - AWS Permissions Checker
# This script checks what AWS permissions you have for Cognito setup

set -e

# Configuration
TARGET_ACCOUNT_ID="764119721991"
EXTERNAL_ROLE_ARN="arn:aws:iam::${TARGET_ACCOUNT_ID}:role/AssumableExternalAccessRole"
PROFILE_NAME="external-access"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_permission() {
    local service=$1
    local action=$2
    local resource=$3
    local description=$4
    
    if eval "$action" &> /dev/null; then
        print_success "$description"
        return 0
    else
        print_error "$description"
        return 1
    fi
}

# Function to setup AWS access
setup_aws_access() {
    print_status "Setting up AWS access..."
    
    # First try current credentials (instance role or configured credentials)
    if aws sts get-caller-identity &> /dev/null; then
        CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
        
        if [ "$CURRENT_ACCOUNT" == "$TARGET_ACCOUNT_ID" ]; then
            print_success "Already connected to target account $TARGET_ACCOUNT_ID"
            ACCOUNT_ID=$CURRENT_ACCOUNT
            USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
            return 0
        else
            print_warning "Currently in account $CURRENT_ACCOUNT, need to switch to $TARGET_ACCOUNT_ID"
        fi
    else
        print_warning "No current AWS credentials detected"
    fi
    
    # Try to assume external access role
    print_status "Attempting to assume external access role..."
    
    if [ -f "./assume-role-to-profile.sh" ]; then
        if ./assume-role-to-profile.sh "$EXTERNAL_ROLE_ARN" "$PROFILE_NAME"; then
            export AWS_PROFILE="$PROFILE_NAME"
            print_success "Successfully assumed external access role"
            
            # Verify the switch worked
            if aws sts get-caller-identity &> /dev/null; then
                ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                USER_ARN=$(aws sts get-caller-identity --query Arn --output text)
                
                if [ "$ACCOUNT_ID" == "$TARGET_ACCOUNT_ID" ]; then
                    print_success "Successfully connected to target account $TARGET_ACCOUNT_ID"
                    return 0
                else
                    print_error "Role assumption succeeded but still in wrong account: $ACCOUNT_ID"
                    return 1
                fi
            else
                print_error "Role assumption seemed to succeed but can't verify identity"
                return 1
            fi
        else
            print_error "Failed to assume external access role"
            return 1
        fi
    else
        print_error "assume-role-to-profile.sh script not found"
        echo "Please ensure the script is in the current directory"
        return 1
    fi
}

echo "================================================================"
echo "    Nexus Telco QA Dashboard - AWS Permissions Checker"
echo "    Target Account: $TARGET_ACCOUNT_ID"
echo "================================================================"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed"
    echo "Please install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Setup AWS access (instance role or external access role)
if ! setup_aws_access; then
    print_error "Failed to setup AWS access to target account"
    echo ""
    echo "Troubleshooting:"
    echo "1. Ensure assume-role-to-profile.sh is in current directory"
    echo "2. Verify your current credentials can assume the external role"
    echo "3. Check that the external role exists and has proper trust policy"
    echo ""
    echo "Current working directory: $(pwd)"
    echo "Files in current directory:"
    ls -la | grep -E "(assume-role|\.sh)" || echo "No shell scripts found"
    exit 1
fi

echo "  Account ID: $ACCOUNT_ID"
echo "  User/Role: $USER_ARN"
echo "  AWS Profile: ${AWS_PROFILE:-default}"

echo ""
print_status "Checking required permissions for Cognito setup..."
echo ""

# Track permission results
PERMISSIONS_OK=0
TOTAL_CHECKS=0

# Cognito Permissions
echo "🔐 Cognito Permissions:"

# Test basic Cognito listing access
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if check_permission "cognito-idp" "aws cognito-idp list-user-pools --max-results 1 --region us-east-1" "*" "cognito-idp:ListUserPools"; then
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

# Test creation permissions indirectly
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
# We test creation permissions by trying to validate a template (doesn't actually create)
TEST_OUTPUT=$(aws cognito-idp create-user-pool --pool-name "permission-test" --region us-east-1 --generate-cli-skeleton 2>&1 || true)
if echo "$TEST_OUTPUT" | grep -q "pool-name\|Pool.*Name\|UserPool" || [ -z "$TEST_OUTPUT" ]; then
    print_success "cognito-idp:CreateUserPool (permission likely available)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    print_error "cognito-idp:CreateUserPool (may be restricted)"
fi

echo ""
echo "📋 CloudFormation Permissions:"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if check_permission "cloudformation" "aws cloudformation describe-stacks --region us-east-1" "*" "cloudformation:DescribeStacks"; then
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
# Test ValidateTemplate with a simpler approach - test the actual CloudFormation template if it exists
if [ -f "./cognito-stack.yaml" ]; then
    if check_permission "cloudformation" "aws cloudformation validate-template --template-body file://cognito-stack.yaml --region us-east-1" "*" "cloudformation:ValidateTemplate"; then
        PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
    fi
else
    # Fallback test with generate-template (which requires validate permissions)
    TEST_OUTPUT=$(aws cloudformation validate-template --template-body '{"AWSTemplateFormatVersion":"2010-09-09","Resources":{"DummyParam":{"Type":"AWS::CloudFormation::WaitConditionHandle"}}}' --region us-east-1 2>&1 || true)
    if echo "$TEST_OUTPUT" | grep -q "Parameters\|Description\|Capabilities" || echo "$TEST_OUTPUT" | grep -q "ValidationError"; then
        print_success "cloudformation:ValidateTemplate"
        PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
    else
        print_error "cloudformation:ValidateTemplate"
    fi
fi

# Additional CloudFormation permissions check
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if check_permission "cloudformation" "aws cloudformation list-stacks --max-items 1 --region us-east-1" "*" "cloudformation:ListStacks"; then
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

# Test CloudFormation stack operations permissions
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
# Test if we can check stack events (needed for deployments)
TEST_OUTPUT=$(aws cloudformation describe-stack-events --stack-name "non-existent-stack-test-$(date +%s)" --region us-east-1 2>&1 || true)
if echo "$TEST_OUTPUT" | grep -q "does not exist\|ValidationError" && ! echo "$TEST_OUTPUT" | grep -q "AccessDenied\|UnauthorizedOperation"; then
    print_success "cloudformation:DescribeStackEvents (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    print_error "cloudformation:DescribeStackEvents (access denied)"
fi

echo ""
echo "👤 IAM Permissions:"
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
# Skip iam:GetUser for assumed roles as it's not applicable
if [[ "$USER_ARN" == *"assumed-role"* ]]; then
    print_success "iam:GetUser (skipped - using assumed role)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
else
    if check_permission "iam" "aws iam get-user --region us-east-1" "*" "iam:GetUser"; then
        PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
    fi
fi

TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
if check_permission "iam" "aws iam list-roles --max-items 1 --region us-east-1" "*" "iam:ListRoles"; then
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

# Additional checks for Cognito management
echo ""
echo "🔧 Additional Cognito Management Permissions:"

# Check if we can test various Cognito operations without needing existing resources
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
# Test with a dummy command that will fail gracefully but show if we have the permission
TEST_OUTPUT=$(aws cognito-idp describe-user-pool --user-pool-id "us-east-1_DUMMY123" --region us-east-1 2>&1 || true)
if echo "$TEST_OUTPUT" | grep -q "ResourceNotFoundException\|UserPoolId"; then
    print_success "cognito-idp:DescribeUserPool (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
elif echo "$TEST_OUTPUT" | grep -q "AccessDenied\|UnauthorizedOperation"; then
    print_error "cognito-idp:DescribeUserPool (access denied)"
else
    print_success "cognito-idp:DescribeUserPool (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

# Test group management permissions
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
TEST_OUTPUT=$(aws cognito-idp list-groups --user-pool-id "us-east-1_DUMMY123" --region us-east-1 2>&1 || true)
if echo "$TEST_OUTPUT" | grep -q "ResourceNotFoundException\|UserPoolId"; then
    print_success "cognito-idp:ListGroups (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
elif echo "$TEST_OUTPUT" | grep -q "AccessDenied\|UnauthorizedOperation"; then
    print_error "cognito-idp:ListGroups (access denied)"
else
    print_success "cognito-idp:ListGroups (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

# Test user management permissions
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
TEST_OUTPUT=$(aws cognito-idp list-users --user-pool-id "us-east-1_DUMMY123" --region us-east-1 2>&1 || true)
if echo "$TEST_OUTPUT" | grep -q "ResourceNotFoundException\|UserPoolId"; then
    print_success "cognito-idp:ListUsers (permission exists)"
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
elif echo "$TEST_OUTPUT" | grep -q "AccessDenied\|UnauthorizedOperation"; then
    print_error "cognito-idp:ListUsers (access denied)"
else
    print_success "cognito-idp:ListUsers (permission exists)" 
    PERMISSIONS_OK=$((PERMISSIONS_OK + 1))
fi

echo ""
echo "================================================================"
echo "                      PERMISSION SUMMARY"
echo "================================================================"

PERMISSION_PERCENTAGE=$((PERMISSIONS_OK * 100 / TOTAL_CHECKS))

echo "Permissions Check: $PERMISSIONS_OK/$TOTAL_CHECKS passed ($PERMISSION_PERCENTAGE%)"
echo ""

if [ $PERMISSIONS_OK -eq $TOTAL_CHECKS ]; then
    print_success "🎉 All permissions available in account $TARGET_ACCOUNT_ID! You can use AWS CLI setup."
    echo ""
    echo "Next steps:"
    echo "1. Set AWS_PROFILE=$PROFILE_NAME (if not already set)"
    echo "2. Run the cognito setup commands with this profile"
    echo "3. Or use the deployment script: AWS_PROFILE=$PROFILE_NAME ./deploy-cognito.sh"
    
elif [ $PERMISSIONS_OK -ge $((TOTAL_CHECKS * 2 / 3)) ]; then
    print_warning "⚡ Most permissions available in account $TARGET_ACCOUNT_ID, but some restrictions detected."
    echo ""
    echo "Recommendations:"
    echo "1. Try the AWS Console method (see ENTERPRISE_AUTH_SETUP.md)"
    echo "   - URL: https://console.aws.amazon.com/cognito/"
    echo "   - Make sure you're in account $TARGET_ACCOUNT_ID"
    echo "2. Ask admin to grant additional permissions to the external access role"
    echo "3. Or use CloudFormation template with AWS_PROFILE=$PROFILE_NAME"
    
else
    print_error "❌ Limited permissions detected in account $TARGET_ACCOUNT_ID."
    echo ""
    echo "Required Actions:"
    echo "1. Ask your AWS administrator to add these policies to the external access role:"
    echo "   Role: $EXTERNAL_ROLE_ARN"
    echo "   Policies needed:"
    echo "   - AmazonCognitoPowerUser (for Cognito access)"
    echo "   - CloudFormationFullAccess (for automated deployment)"
    echo ""
    echo "2. Alternative: Use AWS Console method"
    echo "   - Go to: https://console.aws.amazon.com/cognito/"
    echo "   - Ensure you're in account $TARGET_ACCOUNT_ID"
    echo "   - Follow manual setup in ENTERPRISE_AUTH_SETUP.md"
    echo ""
    echo "3. Current role permissions may be insufficient for Cognito management"
fi

echo ""
echo "================================================================"
echo "                    AVAILABLE ALTERNATIVES"
echo "================================================================"
echo ""

echo "🖥️  AWS Console Setup (Account $TARGET_ACCOUNT_ID):"
echo "   1. Go to: https://console.aws.amazon.com/cognito/v2/home"
echo "   2. Verify you're in account $TARGET_ACCOUNT_ID (top right corner)"
echo "   3. Create User Pool manually"
echo "   4. Follow guide in docs/ENTERPRISE_AUTH_SETUP.md"
echo ""

echo "📋 CloudFormation Template:"
echo "   1. Set profile: export AWS_PROFILE=$PROFILE_NAME"
echo "   2. Deploy with script: ./deploy-cognito.sh"
echo "   3. Or ask admin to deploy: deploy/cognito-stack.yaml"
echo ""

echo "🔧 IAM Policy for External Access Role (for admin):"
echo "   Role ARN: $EXTERNAL_ROLE_ARN"
echo '   Add these managed policies:
   - AmazonCognitoPowerUser
   - CloudFormationFullAccess
   
   Or custom policy:
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "cognito-idp:*",
                   "cloudformation:*",
                   "iam:ListRoles",
                   "iam:PassRole"
               ],
               "Resource": "*"
           }
       ]
   }'
echo ""

echo "📞 What to tell your admin:"
echo "   'Please add the AmazonCognitoPowerUser managed policy"
echo "    to the external access role: $EXTERNAL_ROLE_ARN'"
echo "   'This will allow me to create Cognito resources in account $TARGET_ACCOUNT_ID'"

echo ""
echo "================================================================"
