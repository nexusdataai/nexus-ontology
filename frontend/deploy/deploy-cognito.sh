#!/bin/bash

# Nexus Telco QA Dashboard - Cognito Stack Deployment Script
# This script deploys the AWS Cognito User Pool with RBAC groups

set -e  # Exit on any error

# Configuration
STACK_NAME="nexus-cognito"
TEMPLATE_FILE="cognito-stack.yaml"
REGION="us-east-1"
TARGET_ACCOUNT_ID="764119721991"
EXTERNAL_ROLE_ARN="arn:aws:iam::${TARGET_ACCOUNT_ID}:role/AssumableExternalAccessRole"
PROFILE_NAME="external-access"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to check if AWS CLI is available
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        echo "Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        exit 1
    fi
}

# Function to setup AWS access
setup_aws_access() {
    print_status "Setting up AWS access for account $TARGET_ACCOUNT_ID..."
    
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

# Function to check AWS credentials
check_aws_credentials() {
    # Setup AWS access first
    if ! setup_aws_access; then
        print_error "Failed to setup AWS access to target account $TARGET_ACCOUNT_ID"
        echo ""
        echo "Troubleshooting:"
        echo "1. Ensure assume-role-to-profile.sh is in current directory"
        echo "2. Verify your current credentials can assume the external role"
        echo "3. Check that the external role exists and has proper trust policy"
        echo ""
        exit 1
    fi
    
    print_success "AWS credentials verified for account $TARGET_ACCOUNT_ID"
    echo "  Account ID: $ACCOUNT_ID"
    echo "  User/Role: $USER_ARN"
    echo "  AWS Profile: ${AWS_PROFILE:-default}"
}

# Function to check required permissions
check_permissions() {
    print_status "Checking required permissions..."
    
    # Try to describe CloudFormation stacks to test permissions
    if ! aws cloudformation describe-stacks --region $REGION &> /dev/null; then
        print_warning "Limited CloudFormation permissions detected"
        echo "You may need CloudFormationFullAccess or custom permissions"
    fi
    
    # Check Cognito permissions
    if ! aws cognito-idp describe-user-pools-limit --region $REGION &> /dev/null; then
        print_warning "Limited Cognito permissions detected"
        echo "You may need AmazonCognitoPowerUser or custom permissions"
    fi
}

# Function to get deployment parameters
get_parameters() {
    echo ""
    print_status "Deployment Configuration"
    
    # Environment
    read -p "Environment (dev/staging/prod) [dev]: " ENV
    ENV=${ENV:-dev}
    
    # App name
    read -p "Application name [nexus-qa-dashboard]: " APP_NAME
    APP_NAME=${APP_NAME:-nexus-qa-dashboard}
    
    # Callback URL
    if [ "$ENV" == "prod" ]; then
        DEFAULT_CALLBACK="https://your-domain.com/auth/callback"
        DEFAULT_LOGOUT="https://your-domain.com/login"
    else
        DEFAULT_CALLBACK="http://localhost:5173/auth/callback"
        DEFAULT_LOGOUT="http://localhost:5173/login"
    fi
    
    read -p "Callback URL [$DEFAULT_CALLBACK]: " CALLBACK_URL
    CALLBACK_URL=${CALLBACK_URL:-$DEFAULT_CALLBACK}
    
    read -p "Logout URL [$DEFAULT_LOGOUT]: " LOGOUT_URL
    LOGOUT_URL=${LOGOUT_URL:-$DEFAULT_LOGOUT}
    
    # Region
    read -p "AWS Region [$REGION]: " INPUT_REGION
    REGION=${INPUT_REGION:-$REGION}
    
    echo ""
    print_status "Configuration Summary:"
    echo "  Stack Name: $STACK_NAME-$ENV"
    echo "  App Name: $APP_NAME"
    echo "  Environment: $ENV"
    echo "  Callback URL: $CALLBACK_URL"
    echo "  Logout URL: $LOGOUT_URL"
    echo "  Region: $REGION"
    echo ""
}

# Function to validate template
validate_template() {
    print_status "Validating CloudFormation template..."
    
    if aws cloudformation validate-template \
        --template-body file://$TEMPLATE_FILE \
        --region $REGION > /dev/null; then
        print_success "Template validation passed"
    else
        print_error "Template validation failed"
        exit 1
    fi
}

# Function to check if stack exists
stack_exists() {
    aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME-$ENV" \
        --region $REGION &> /dev/null
}

# Function to deploy stack
deploy_stack() {
    local action="create"
    
    if stack_exists; then
        print_warning "Stack $STACK_NAME-$ENV already exists"
        read -p "Do you want to update it? (y/N): " UPDATE_STACK
        if [[ $UPDATE_STACK =~ ^[Yy]$ ]]; then
            action="update"
        else
            print_status "Deployment cancelled"
            return 0
        fi
    fi
    
    print_status "${action^}ing CloudFormation stack..."
    
    # Prepare parameters
    PARAMETERS="ParameterKey=AppName,ParameterValue=$APP_NAME"
    PARAMETERS="$PARAMETERS ParameterKey=Environment,ParameterValue=$ENV"
    PARAMETERS="$PARAMETERS ParameterKey=CallbackURL,ParameterValue=$CALLBACK_URL"
    PARAMETERS="$PARAMETERS ParameterKey=LogoutURL,ParameterValue=$LOGOUT_URL"
    
    # Execute CloudFormation command
    if [ "$action" == "create" ]; then
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME-$ENV" \
            --template-body file://$TEMPLATE_FILE \
            --parameters $PARAMETERS \
            --capabilities CAPABILITY_IAM \
            --region $REGION
    else
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME-$ENV" \
            --template-body file://$TEMPLATE_FILE \
            --parameters $PARAMETERS \
            --capabilities CAPABILITY_IAM \
            --region $REGION
    fi
    
    print_status "Stack deployment initiated. Waiting for completion..."
    
    # Wait for stack to complete
    aws cloudformation wait stack-${action}-complete \
        --stack-name "$STACK_NAME-$ENV" \
        --region $REGION
    
    if [ $? -eq 0 ]; then
        print_success "Stack deployment completed successfully!"
    else
        print_error "Stack deployment failed!"
        exit 1
    fi
}

# Function to set temporary passwords for test users
setup_test_users() {
    if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
        return 0
    fi
    
    print_status "Setting up test user passwords..."
    
    # Test users to create
    declare -A TEST_USERS
    TEST_USERS[executive@nexus.totogicore.com]="Nexus Telco Executive"
    TEST_USERS[salesmanager@nexus.totogicore.com]="Nexus Telco Sales Manager"
    TEST_USERS[rep@nexus.totogicore.com]="Nexus Telco Sales Rep"
    
    for email in "${!TEST_USERS[@]}"; do
        name="${TEST_USERS[$email]}"
        print_status "Setting password for $email..."
        
        # Set temporary password
        if aws cognito-idp admin-set-user-password \
            --user-pool-id "$USER_POOL_ID" \
            --username "$email" \
            --password "TempPassword123!" \
            --temporary \
            --region $REGION &> /dev/null; then
            print_success "Password set for $email"
        else
            print_warning "Failed to set password for $email (user may not exist yet)"
        fi
    done
}

# Function to get stack outputs
get_outputs() {
    print_status "Retrieving stack outputs..."
    
    OUTPUTS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME-$ENV" \
        --region $REGION \
        --query 'Stacks[0].Outputs')
    
    if [ "$OUTPUTS" != "null" ]; then
        echo ""
        print_success "Stack Outputs:"
        echo "$OUTPUTS" | jq -r '.[] | "  \(.OutputKey): \(.OutputValue)"'
        
        # Extract key values for .env file
        USER_POOL_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolId") | .OutputValue')
        CLIENT_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolClientId") | .OutputValue')
        DOMAIN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="UserPoolDomain") | .OutputValue')
        
        # Set up test users with passwords
        setup_test_users
        
        echo ""
        print_success "Environment Variables for your .env.local file:"
        echo "VITE_AWS_REGION=$REGION"
        echo "VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID"
        echo "VITE_COGNITO_CLIENT_ID=$CLIENT_ID"
        echo "VITE_COGNITO_DOMAIN=$DOMAIN"
        echo "VITE_OAUTH_REDIRECT_SIGNIN=$CALLBACK_URL"
        echo "VITE_OAUTH_REDIRECT_SIGNOUT=$LOGOUT_URL"
        echo "NODE_ENV=$ENV"
    fi
}

# Function to create env file
create_env_file() {
    read -p "Create .env.local file automatically? (y/N): " CREATE_ENV
    if [[ $CREATE_ENV =~ ^[Yy]$ ]]; then
        ENV_FILE="../.env.local"
        
        cat > $ENV_FILE << EOF
# Nexus Telco QA Dashboard - AWS Cognito Configuration
# Generated automatically by deploy-cognito.sh

# AWS Cognito Configuration
VITE_AWS_REGION=$REGION
VITE_COGNITO_USER_POOL_ID=$USER_POOL_ID
VITE_COGNITO_CLIENT_ID=$CLIENT_ID
VITE_COGNITO_DOMAIN=$DOMAIN

# OAuth Redirect URLs
VITE_OAUTH_REDIRECT_SIGNIN=$CALLBACK_URL
VITE_OAUTH_REDIRECT_SIGNOUT=$LOGOUT_URL

# Security Configuration
VITE_COOKIE_DOMAIN=localhost

# Environment
NODE_ENV=$ENV

# ADFS Configuration (optional - configure if using ADFS)
# VITE_ADFS_METADATA_URL=https://your-adfs-server.company.com/FederationMetadata/2007-06/FederationMetadata.xml
EOF
        
        print_success ".env.local file created successfully!"
        print_warning "Remember to add .env.local to your .gitignore file"
    fi
}

# Function to show next steps
show_next_steps() {
    echo ""
    print_success "🎉 Deployment Complete!"
    echo ""
    echo "Next steps:"
    echo "1. Update your application's .env.local file with the environment variables above"
    echo "2. Install dependencies: npm install"
    echo "3. Start your development server: npm run dev"
    echo "4. Test login with the created test users:"
    
    if [ "$ENV" == "dev" ] || [ "$ENV" == "prod" ]; then
        echo "   - Executive: executive@nexus.totogicore.com / TempPassword123!"
        echo "   - Sales Manager: salesmanager@nexus.totogicore.com / TempPassword123!"
        echo "   - Rep: rep@nexus.totogicore.com / TempPassword123!"
        echo "   (You'll be prompted to change password on first login)"
    fi
    
    echo ""
    echo "5. Configure ADFS integration if needed (see ENTERPRISE_AUTH_SETUP.md)"
    echo "6. Create additional users in AWS Cognito Console"
    echo ""
    print_status "AWS Cognito Console: https://console.aws.amazon.com/cognito/v2/idp/user-pools/$USER_POOL_ID/users"
}

# Main execution
main() {
    echo "================================================================"
    echo "    Nexus Telco QA Dashboard - Cognito Stack Deployment"
    echo "    Target Account: $TARGET_ACCOUNT_ID"
    echo "================================================================"
    echo ""
    
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Check prerequisites
    check_aws_cli
    check_aws_credentials
    check_permissions
    
    # Check if template exists
    if [ ! -f "$TEMPLATE_FILE" ]; then
        print_error "CloudFormation template not found: $TEMPLATE_FILE"
        exit 1
    fi
    
    # Get deployment parameters
    get_parameters
    
    # Confirm deployment
    echo ""
    read -p "Proceed with deployment? (y/N): " CONFIRM
    if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
        print_status "Deployment cancelled"
        exit 0
    fi
    
    # Deploy
    validate_template
    deploy_stack
    get_outputs
    create_env_file
    show_next_steps
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --help, -h    Show this help message"
        echo "  --delete      Delete the stack"
        echo ""
        echo "This script deploys AWS Cognito User Pool for Nexus Telco QA Dashboard"
        exit 0
        ;;
    --delete)
        read -p "Environment to delete (dev/staging/prod): " ENV
        ENV=${ENV:-dev}
        read -p "Are you sure you want to delete stack $STACK_NAME-$ENV? (y/N): " CONFIRM
        if [[ $CONFIRM =~ ^[Yy]$ ]]; then
            print_status "Deleting stack $STACK_NAME-$ENV..."
            aws cloudformation delete-stack \
                --stack-name "$STACK_NAME-$ENV" \
                --region $REGION
            print_success "Stack deletion initiated"
        fi
        exit 0
        ;;
esac

# Run main function
main
