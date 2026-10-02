#!/bin/bash

# Alert Engine MCP Server - Stack Cleanup Script
# Safely removes CloudFormation stacks in reverse dependency order

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script path configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

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

# Function to check if stack exists
stack_exists() {
    local stack_name="$1"
    aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" &> /dev/null
}

# Function to delete a stack
delete_stack() {
    local stack_name="$1"
    
    if stack_exists "$stack_name"; then
        print_status "Deleting stack: $stack_name"
        aws cloudformation delete-stack --stack-name "$stack_name" --region "$AWS_REGION"
        print_status "Waiting for stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name "$stack_name" --region "$AWS_REGION"
        print_success "Stack deleted: $stack_name"
    else
        print_warning "Stack does not exist: $stack_name"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <environment>"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment"
    echo "  stage - Staging environment"
    echo "  prod  - Production environment"
    echo ""
    echo "Examples:"
    echo "  $0 dev    # Delete all dev environment stacks"
    echo "  $0 stage  # Delete all stage environment stacks"
    echo ""
    echo "⚠️  WARNING: This will permanently delete all resources!"
}

# Validate arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

ENVIRONMENT="$1"

# Validate environment
case "$ENVIRONMENT" in
    "dev"|"stage"|"prod")
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT"
        show_usage
        exit 1
        ;;
esac

# Load configuration
CONFIG_FILE="$SCRIPT_DIR/config/${ENVIRONMENT}.conf"
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Source the configuration file
source "$CONFIG_FILE"

print_warning "⚠️  WARNING: This will delete ALL stacks for environment: $ENVIRONMENT"
print_warning "This action cannot be undone!"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    print_status "Operation cancelled"
    exit 0
fi

print_status "Starting cleanup of $ENVIRONMENT environment stacks..."

# Delete stacks in reverse dependency order
if [ "$ENABLE_DOMAIN_SETUP" = "true" ]; then
    delete_stack "$DOMAIN_STACK_NAME"
fi

delete_stack "$BACKEND_STACK_NAME"

if [ "$ENABLE_AUTHENTICATION" = "true" ]; then
    delete_stack "$AUTH_STACK_NAME"
fi

delete_stack "$STORAGE_STACK_NAME"
delete_stack "$NETWORK_STACK_NAME"

print_success "All stacks for environment '$ENVIRONMENT' have been deleted"

