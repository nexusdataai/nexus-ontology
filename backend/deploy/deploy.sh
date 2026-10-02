#!/bin/bash

# Alert Engine MCP Server ECS Deployment Script
# Architecture: Route53 -> ALB -> ECS Fargate -> S3 + Cognito
# Supports multiple environments: dev, stage, prod

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values - will be overridden by environment config
ENVIRONMENT=""
PROJECT_NAME=""
AWS_REGION=""
DEPLOYMENT_REGION=""
BASE_DOMAIN=""
SUBDOMAIN=""
HOSTED_ZONE_ID=""

# Stack names
MAIN_STACK_NAME=""
NETWORK_STACK_NAME=""
STORAGE_STACK_NAME=""
BACKEND_STACK_NAME=""
DOMAIN_STACK_NAME=""

# CloudFormation templates
CLOUDFORMATION_TEMPLATES_DIR=""
MAIN_TEMPLATE=""
NETWORK_TEMPLATE=""
STORAGE_TEMPLATE=""
BACKEND_TEMPLATE=""
DOMAIN_TEMPLATE=""

# External role configuration
ROLE_ARN=""
EXTERNAL_PROFILE=""

# Script path configuration
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
ASSUME_ROLE_SCRIPT="./assume-role-to-profile.sh"

# Available environments
AVAILABLE_ENVIRONMENTS=("dev" "stage" "prod")

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

# Function to load environment configuration
load_config() {
    local env="$1"
    local config_file="$SCRIPT_DIR/config/${env}.conf"
    
    if [ ! -f "$config_file" ]; then
        print_error "Configuration file not found: $config_file"
        print_error "Available environments: ${AVAILABLE_ENVIRONMENTS[*]}"
        exit 1
    fi
    
    print_status "Loading configuration for environment: $env"
    
    # Source the configuration file
    # shellcheck source=/dev/null
    source "$config_file"
    
    # Validate required configuration variables
    if [ -z "$PROJECT_NAME" ] || [ -z "$BASE_DOMAIN" ] || [ -z "$SUBDOMAIN" ] || [ -z "$AWS_REGION" ]; then
        print_error "Missing required configuration in $config_file"
        print_error "Required: PROJECT_NAME, BASE_DOMAIN, SUBDOMAIN, AWS_REGION"
        exit 1
    fi
    
    # Set deployment region to AWS region if not specified
    if [ -z "$DEPLOYMENT_REGION" ]; then
        DEPLOYMENT_REGION="$AWS_REGION"
    fi
    
    # Auto-generate stack names if not specified
    if [ -z "$MAIN_STACK_NAME" ]; then
        MAIN_STACK_NAME="${PROJECT_NAME}-main-${ENVIRONMENT}"
    fi
    if [ -z "$NETWORK_STACK_NAME" ]; then
        NETWORK_STACK_NAME="${PROJECT_NAME}-network-${ENVIRONMENT}"
    fi
    if [ -z "$STORAGE_STACK_NAME" ]; then
        STORAGE_STACK_NAME="${PROJECT_NAME}-storage-${ENVIRONMENT}"
    fi
    if [ -z "$BACKEND_STACK_NAME" ]; then
        BACKEND_STACK_NAME="${PROJECT_NAME}-backend-${ENVIRONMENT}"
    fi
    if [ -z "$DOMAIN_STACK_NAME" ]; then
        DOMAIN_STACK_NAME="${PROJECT_NAME}-domain-${ENVIRONMENT}"
    fi
    
    print_success "Configuration loaded successfully"
    print_status "Environment: $ENVIRONMENT"
    print_status "Project: $PROJECT_NAME"
    print_status "Domain: ${SUBDOMAIN}.${BASE_DOMAIN}"
    print_status "Region: $AWS_REGION"
    print_status "Main Stack: $MAIN_STACK_NAME"
    print_status "Network Stack: $NETWORK_STACK_NAME"
    print_status "Storage Stack: $STORAGE_STACK_NAME"
    print_status "Backend Stack: $BACKEND_STACK_NAME"
    print_status "Domain Stack: $DOMAIN_STACK_NAME"
    
    # Validate required VPC configuration
    if [ -z "$EXISTING_VPC_ID" ] || [ -z "$EXISTING_PUBLIC_SUBNET_1" ] || [ -z "$EXISTING_PUBLIC_SUBNET_2" ]; then
        print_error "Missing required VPC configuration!"
        print_error "This deployment requires existing VPC and subnets."
        print_error "Please set in $config_file:"
        print_error "  - EXISTING_VPC_ID"
        print_error "  - EXISTING_PUBLIC_SUBNET_1"
        print_error "  - EXISTING_PUBLIC_SUBNET_2"
        exit 1
    fi
    
    print_success "VPC Configuration validated"
    print_status "Using VPC: $EXISTING_VPC_ID"
    print_status "Public Subnets: $EXISTING_PUBLIC_SUBNET_1, $EXISTING_PUBLIC_SUBNET_2"
    if [ -n "$EXISTING_PRIVATE_SUBNET_1" ]; then
        print_status "Private Subnets: $EXISTING_PRIVATE_SUBNET_1, $EXISTING_PRIVATE_SUBNET_2"
    fi
}

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
    
    # Verify the assumed role
    print_status "Verifying assumed role..."
    if ! aws sts get-caller-identity; then
        print_error "Failed to verify assumed role"
        exit 1
    fi
    
    print_success "External role assumed and verified"
}

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    print_status "Checking AWS CLI..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to check Docker installation
check_docker() {
    print_status "Checking Docker..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "Docker is available"
}

# Function to upload CloudFormation templates to S3
upload_templates_to_s3() {
    print_status "Uploading CloudFormation templates to S3..."
    
    # Create S3 bucket for templates if it doesn't exist
    local templates_bucket="${PROJECT_NAME}-cf-templates-${ENVIRONMENT}-${AWS_REGION}"
    
    # Check if bucket exists, create if it doesn't
    if ! aws s3 ls "s3://$templates_bucket" &> /dev/null; then
        print_status "Creating S3 bucket for templates: $templates_bucket"
        if [ "$AWS_REGION" = "us-east-1" ]; then
            aws s3 mb "s3://$templates_bucket"
        else
            aws s3 mb "s3://$templates_bucket" --region "$AWS_REGION"
        fi
    else
        print_status "S3 bucket already exists: $templates_bucket (proceeding with upload)"
    fi
    
    # Upload all template files
    local templates=(
        "cloudformation-iam-roles-template.yaml"
        "cloudformation-global-template.yaml"
        "cloudformation-network-existing-vpc-template.yaml"
        "cloudformation-storage-template.yaml"
        "cloudformation-backend-template.yaml"
        "cloudformation-domain-template.yaml"
    )
    
    for template in "${templates[@]}"; do
        if [ -f "$template" ]; then
            print_status "Uploading $template to S3..."
            aws s3 cp "$template" "s3://$templates_bucket/$template"
        else
            print_error "Template file not found: $template"
            return 1
        fi
    done
    
    print_success "All templates uploaded to S3"
    export S3_TEMPLATES_BUCKET="$templates_bucket"
}

# Function to clean up existing stacks and exports
cleanup_existing_stacks() {
    print_status "Checking for existing stacks and cleaning up exports..."
    
    # List of stack names to check and potentially delete
    local stacks_to_check=(
        "$MAIN_STACK_NAME"
        "$NETWORK_STACK_NAME"
        "$STORAGE_STACK_NAME"
        "$BACKEND_STACK_NAME"
        "$DOMAIN_STACK_NAME"
    )
    
    # First, try to delete the main stack (which will delete nested stacks)
    if aws cloudformation describe-stacks --stack-name "$MAIN_STACK_NAME" &> /dev/null; then
        print_status "Found main stack: $MAIN_STACK_NAME"
        print_status "Deleting main stack (this will delete all nested stacks): $MAIN_STACK_NAME"
        aws cloudformation delete-stack --stack-name "$MAIN_STACK_NAME"
        
        # Wait for main stack deletion to complete
        print_status "Waiting for main stack deletion to complete: $MAIN_STACK_NAME"
        aws cloudformation wait stack-delete-complete --stack-name "$MAIN_STACK_NAME" || true
        print_success "Main stack deleted: $MAIN_STACK_NAME"
    fi
    
    # Then check for any remaining individual stacks
    for stack_name in "${stacks_to_check[@]}"; do
        if [ "$stack_name" != "$MAIN_STACK_NAME" ]; then
            if aws cloudformation describe-stacks --stack-name "$stack_name" &> /dev/null; then
                print_status "Found remaining stack: $stack_name"
                print_status "Deleting remaining stack: $stack_name"
                aws cloudformation delete-stack --stack-name "$stack_name"
                
                # Wait for deletion to complete
                print_status "Waiting for stack deletion to complete: $stack_name"
                aws cloudformation wait stack-delete-complete --stack-name "$stack_name" || true
                print_success "Stack deleted: $stack_name"
            fi
        fi
    done
    
    # Wait longer for exports to be cleaned up
    print_status "Waiting for CloudFormation exports to be cleaned up..."
    sleep 30
    
    # Check if exports still exist and warn
    local exports_to_check=(
        "${PROJECT_NAME}-vpc-id-${ENVIRONMENT}"
        "${PROJECT_NAME}-bucket-name-${ENVIRONMENT}"
        "${PROJECT_NAME}-cluster-name-${ENVIRONMENT}"
    )
    
    for export_name in "${exports_to_check[@]}"; do
        if aws cloudformation list-exports --query "Exports[?Name=='$export_name'].Name" --output text | grep -q "$export_name"; then
            print_status "Warning: Export $export_name still exists (may be from another stack)"
        fi
    done
    
    print_success "Cleanup completed"
}

# Function to force cleanup all stacks (more aggressive)
force_cleanup_all_stacks() {
    print_status "Force cleaning up all stacks and exports..."
    
    # List all stacks that might be related to our project
    local all_stacks
    all_stacks=$(aws cloudformation list-stacks \
        --query "StackSummaries[?contains(StackName, '${PROJECT_NAME}') && StackStatus != 'DELETE_COMPLETE'].StackName" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$all_stacks" ]; then
        print_status "Found related stacks: $all_stacks"
        
        # Delete all related stacks
        for stack_name in $all_stacks; do
            print_status "Force deleting stack: $stack_name"
            aws cloudformation delete-stack --stack-name "$stack_name" || true
        done
        
        # Wait for all deletions to complete
        for stack_name in $all_stacks; do
            print_status "Waiting for stack deletion: $stack_name"
            aws cloudformation wait stack-delete-complete --stack-name "$stack_name" || true
        done
        
        print_success "All related stacks deleted"
    else
        print_status "No related stacks found"
    fi
    
    # Wait longer for exports to be cleaned up
    print_status "Waiting for CloudFormation exports to be cleaned up..."
    sleep 60
    
    print_success "Force cleanup completed"
}

# Function to deploy a CloudFormation stack
deploy_stack() {
    local stack_name="$1"
    local template_file="$2"
    local parameters="$3"
    
    print_status "Deploying stack: $stack_name"
    print_status "Template: $template_file"
    
    # Check if template file exists
    if [ ! -f "$template_file" ]; then
        print_error "Template file not found: $template_file"
        exit 1
    fi
    
    # Check if stack exists
    local operation
    if aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" &> /dev/null; then
        print_status "Stack exists, updating..."
        operation="update-stack"
    else
        print_status "Stack doesn't exist, creating..."
        operation="create-stack"
    fi
    
    # Deploy the stack
    if [ "$operation" = "update-stack" ]; then
        # Try to update the stack, handle "No updates" case gracefully
        print_status "Attempting to update stack..."
        
        # Capture output and exit code properly
        set +e  # Temporarily disable exit on error
        local output_file="/tmp/${stack_name}_update_output.log"
        aws cloudformation $operation \
            --stack-name "$stack_name" \
            --template-body file://"$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" > "$output_file" 2>&1
        
        local exit_code=$?
        set -e  # Re-enable exit on error
        
        if [ $exit_code -eq 0 ]; then
            # Update succeeded
            print_status "Waiting for stack update to complete..."
            aws cloudformation wait stack-update-complete --stack-name "$stack_name" --region "$AWS_REGION"
            print_success "Stack updated successfully"
        else
            # Update failed - check if it's the "No updates" case
            if grep -q "No updates are to be performed" "$output_file"; then
                print_warning "Stack is already up to date, no updates needed"
                print_success "Stack validation passed"
            else
                print_error "Failed to update stack"
                cat "$output_file"
                exit 1
            fi
        fi
    else
        # Create new stack
        aws cloudformation $operation \
            --stack-name "$stack_name" \
            --template-body file://"$template_file" \
            --parameters $parameters \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION"
        
        # Wait for creation completion
        print_status "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name "$stack_name" --region "$AWS_REGION"
        print_success "Stack created successfully"
    fi
}

# Function to deploy main stack (orchestrates all other stacks)
deploy_main_stack() {
    print_status "Deploying main infrastructure stack..."
    
    local parameters="ParameterKey=ProjectName,ParameterValue=$PROJECT_NAME"
    parameters="$parameters ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
    parameters="$parameters ParameterKey=BaseDomain,ParameterValue=$BASE_DOMAIN"
    parameters="$parameters ParameterKey=Subdomain,ParameterValue=$SUBDOMAIN"
    parameters="$parameters ParameterKey=HostedZoneId,ParameterValue=$HOSTED_ZONE_ID"
    parameters="$parameters ParameterKey=DockerImageUri,ParameterValue=$DOCKER_IMAGE_URI"
    parameters="$parameters ParameterKey=TaskCpu,ParameterValue=$ECS_TASK_CPU"
    parameters="$parameters ParameterKey=TaskMemory,ParameterValue=$ECS_TASK_MEMORY"
    parameters="$parameters ParameterKey=DesiredCount,ParameterValue=$ECS_DESIRED_COUNT"
    parameters="$parameters ParameterKey=MinCapacity,ParameterValue=$ECS_MIN_CAPACITY"
    parameters="$parameters ParameterKey=MaxCapacity,ParameterValue=$ECS_MAX_CAPACITY"
    parameters="$parameters ParameterKey=LogRetentionDays,ParameterValue=$LOG_RETENTION_DAYS"
    
    # Add bucket name if specified
    if [ -n "$S3_BUCKET_NAME" ]; then
        # Generate unique bucket name with timestamp
        local unique_bucket_name="${S3_BUCKET_NAME}-$(date +%s)-$RANDOM"
        parameters="$parameters ParameterKey=BucketName,ParameterValue=$unique_bucket_name"
    fi
    
    parameters="$parameters ParameterKey=SecretsArn,ParameterValue=$SECRETS_ARN"
    parameters="$parameters ParameterKey=LogLevel,ParameterValue=$APP_LOG_LEVEL"
    parameters="$parameters ParameterKey=EnableAutoScaling,ParameterValue=$ENABLE_AUTO_SCALING"
    parameters="$parameters ParameterKey=CreateSSLCertificate,ParameterValue=$CREATE_SSL_CERTIFICATE"
    parameters="$parameters ParameterKey=EnableDomainSetup,ParameterValue=$ENABLE_DOMAIN_SETUP"
    parameters="$parameters ParameterKey=CreateHealthCheck,ParameterValue=${CREATE_HEALTH_CHECK:-false}"
    parameters="$parameters ParameterKey=CreateIAMRoles,ParameterValue=${CREATE_IAM_ROLES:-true}"
    
    # Add SSL certificate ARN if provided
    if [ -n "$SSL_CERTIFICATE_ARN" ]; then
        parameters="$parameters ParameterKey=SSLCertificateArn,ParameterValue=$SSL_CERTIFICATE_ARN"
    fi
    
    # Add existing VPC configuration (now required)
    parameters="$parameters ParameterKey=ExistingVpcId,ParameterValue=$EXISTING_VPC_ID"
    parameters="$parameters ParameterKey=ExistingPublicSubnet1,ParameterValue=$EXISTING_PUBLIC_SUBNET_1"
    parameters="$parameters ParameterKey=ExistingPublicSubnet2,ParameterValue=$EXISTING_PUBLIC_SUBNET_2"
    
    # Add optional private subnets if provided
    if [ -n "$EXISTING_PRIVATE_SUBNET_1" ]; then
        parameters="$parameters ParameterKey=ExistingPrivateSubnet1,ParameterValue=$EXISTING_PRIVATE_SUBNET_1"
    fi
    if [ -n "$EXISTING_PRIVATE_SUBNET_2" ]; then
        parameters="$parameters ParameterKey=ExistingPrivateSubnet2,ParameterValue=$EXISTING_PRIVATE_SUBNET_2"
    fi
    
    parameters="$parameters ParameterKey=S3TemplatesBucket,ParameterValue=$S3_TEMPLATES_BUCKET"
    
    deploy_stack "$MAIN_STACK_NAME" "$CLOUDFORMATION_TEMPLATES_DIR/$MAIN_TEMPLATE" "$parameters"
}

# Function to build and push Docker image to ECR
build_and_push_docker_image() {
    print_status "Building and pushing Docker image to ECR..."
    
    # Get ECR repository URI from backend stack outputs
    local ecr_repo_uri
    ecr_repo_uri=$(aws cloudformation describe-stacks \
        --stack-name "$BACKEND_STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ECRRepositoryUri`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$ecr_repo_uri" ]; then
        print_error "Could not retrieve ECR repository URI from backend stack"
        return 1
    fi
    
    print_status "ECR Repository URI: $ecr_repo_uri"
    
    # Login to ECR
    print_status "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ecr_repo_uri"
    
    # Build Docker image with timestamp tag
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local image_tag="${ecr_repo_uri}:${timestamp}"
    local latest_tag="${ecr_repo_uri}:latest"
    
    print_status "Building Docker image..."
    docker build -t "$image_tag" -t "$latest_tag" .
    
    # Push both tags
    print_status "Pushing Docker image to ECR..."
    docker push "$image_tag"
    docker push "$latest_tag"
    
    print_success "Docker image pushed successfully"
    echo "Image URI: $image_tag"
    echo "Latest URI: $latest_tag"
    
    # Update the DOCKER_IMAGE_URI for the deployment
    export DOCKER_IMAGE_URI="$image_tag"
}

# Function to update ECS service with new image
update_ecs_service() {
    print_status "Updating ECS service with new Docker image..."
    
    # Get ECS cluster and service names from backend stack
    local cluster_name
    local service_name
    
    cluster_name=$(aws cloudformation describe-stacks \
        --stack-name "$BACKEND_STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    service_name=$(aws cloudformation describe-stacks \
        --stack-name "$BACKEND_STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$cluster_name" ] || [ -z "$service_name" ]; then
        print_error "Could not retrieve ECS cluster or service name from backend stack"
        return 1
    fi
    
    print_status "ECS Cluster: $cluster_name"
    print_status "ECS Service: $service_name"
    
    # Force new deployment to pick up the new image
    print_status "Forcing new ECS deployment..."
    aws ecs update-service \
        --cluster "$cluster_name" \
        --service "$service_name" \
        --force-new-deployment \
        --region "$AWS_REGION"
    
    # Wait for deployment to complete
    print_status "Waiting for ECS deployment to complete..."
    aws ecs wait services-stable \
        --cluster "$cluster_name" \
        --services "$service_name" \
        --region "$AWS_REGION"
    
    print_success "ECS service updated successfully"
}

# Function to deploy all infrastructure
deploy_infrastructure() {
    print_status "Starting alert-engine MCP Server infrastructure deployment..."
    
    # Deploy main stack which orchestrates all other stacks
    deploy_main_stack
    
    print_success "All infrastructure deployed successfully"
}

# Function to deploy application (Docker build, push, and update)
deploy_application() {
    print_status "Starting application deployment..."
    
    # Build and push Docker image
    build_and_push_docker_image
    
    # Update ECS service
    update_ecs_service
    
    print_success "Application deployment completed"
}

# Function to get deployment outputs
get_deployment_outputs() {
    print_status "Getting deployment outputs..."
    
    # Get backend URL from main stack
    BACKEND_URL=$(aws cloudformation describe-stacks --stack-name "$MAIN_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`BackendUrl`].OutputValue' --output text 2>/dev/null || echo "")
    ALB_DNS=$(aws cloudformation describe-stacks --stack-name "$MAIN_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDns`].OutputValue' --output text 2>/dev/null || echo "")
    
    # Get domain URL if domain stack is deployed
    if [ "$ENABLE_DOMAIN_SETUP" = "true" ]; then
        API_URL=$(aws cloudformation describe-stacks --stack-name "$MAIN_STACK_NAME" --region "$AWS_REGION" --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text 2>/dev/null || echo "")
    fi
    
    print_success "Retrieved deployment outputs"
}

# Function to display deployment information
show_deployment_info() {
    echo ""
    echo "========================================"
    echo "🚀 ECS DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "========================================"
    echo ""
    echo "📊 Deployment Details:"
    echo "   Project: $PROJECT_NAME"
    echo "   Environment: $ENVIRONMENT"
    echo "   Region: $AWS_REGION"
    echo ""
    echo "🔧 Infrastructure Stacks:"
    echo "   Main Stack: $MAIN_STACK_NAME"
    echo "   Network Stack: $NETWORK_STACK_NAME"
    echo "   Storage Stack: $STORAGE_STACK_NAME"
    echo "   Backend Stack: $BACKEND_STACK_NAME"
    if [ "$ENABLE_DOMAIN_SETUP" = "true" ]; then
        echo "   Domain Stack: $DOMAIN_STACK_NAME"
    fi
    echo ""
    echo "🌐 Service URLs:"
    if [ -n "$ALB_DNS" ]; then
        echo "   Load Balancer: http://$ALB_DNS"
    fi
    if [ -n "$BACKEND_URL" ]; then
        echo "   Backend Service: $BACKEND_URL"
    fi
    if [ -n "$API_URL" ]; then
        echo "   API Endpoint: $API_URL"
    fi
    echo ""
    echo "🔍 Health Check:"
    if [ -n "$ALB_DNS" ]; then
        echo "   Health Endpoint: http://$ALB_DNS/health"
    fi
    echo ""
    echo "⚠️  Note: It may take a few minutes for the service to be fully available."
    echo ""
}

# Main deployment function
main() {
    echo "🚀 Starting Alert Engine MCP Server ECS Deployment"
    echo "=================================================="
    echo "Environment: $ENVIRONMENT"
    echo "=================================================="
    
    # Configuration should already be loaded
    if [ -z "$ENVIRONMENT" ]; then
        print_error "Environment not specified. Use: $0 <environment> [options]"
        exit 1
    fi
    
    # Pre-deployment checks
    check_aws_cli
    check_docker
    
    # Clean up existing stacks and exports
    cleanup_existing_stacks
    
    # Upload templates to S3
    upload_templates_to_s3
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Deploy application (Docker build, push, and update)
    deploy_application
    
    get_deployment_outputs
    
    # Show results
    show_deployment_info
}

# Main deployment function with external role
main_with_external_role() {
    echo "🚀 Starting Alert Engine MCP Server ECS Deployment (External Role)"
    echo "================================================================="
    echo "Environment: $ENVIRONMENT"
    echo "================================================================="
    
    # Configuration should already be loaded
    if [ -z "$ENVIRONMENT" ]; then
        print_error "Environment not specified. Use: $0 <environment> external-aws [options]"
        exit 1
    fi
    
    # Assume external role first
    assume_external_role
    
    # Pre-deployment checks
    check_docker
    
    # Clean up existing stacks and exports
    cleanup_existing_stacks
    
    # Upload templates to S3
    upload_templates_to_s3
    
    # Deploy infrastructure
    deploy_infrastructure
    
    # Deploy application (Docker build, push, and update)
    deploy_application
    
    get_deployment_outputs
    
    # Show results
    show_deployment_info
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <environment> [command]"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment"
    echo "  stage - Staging environment"  
    echo "  prod  - Production environment"
    echo ""
    echo "Commands (optional):"
    echo "  infrastructure-only  - Only deploy/update infrastructure"
    echo "  application-only     - Only deploy application (Docker build, push, update)"
    echo "  cleanup-only        - Only clean up existing stacks and exports"
    echo "  force-cleanup       - Force cleanup all stacks (including stuck ones)"
    echo "  external-aws         - Full deployment with external AWS role"
    echo "  external-aws-infrastructure-only - Only deploy infrastructure with external role"
    echo "  (no command)        - Full deployment"
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Deploy to development environment"
    echo "  $0 stage                  # Deploy to staging environment"
    echo "  $0 prod                   # Deploy to production environment"
    echo "  $0 dev application-only   # Only update application (Docker build/push)"
    echo "  $0 dev cleanup-only       # Only clean up existing stacks"
    echo "  $0 dev force-cleanup      # Force cleanup all stacks"
    echo "  $0 prod external-aws      # Deploy to prod with external AWS role"
}

# Validate and process arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# First argument should be environment
ENVIRONMENT_ARG="$1"
shift

# Validate environment
valid_env=false
for env in "${AVAILABLE_ENVIRONMENTS[@]}"; do
    if [ "$ENVIRONMENT_ARG" = "$env" ]; then
        valid_env=true
        break
    fi
done

if [ "$valid_env" = false ]; then
    print_error "Invalid environment: $ENVIRONMENT_ARG"
    print_error "Available environments: ${AVAILABLE_ENVIRONMENTS[*]}"
    show_usage
    exit 1
fi

# Load environment configuration
ENVIRONMENT="$ENVIRONMENT_ARG"
load_config "$ENVIRONMENT_ARG"

# Handle remaining arguments (commands)
case "${1:-}" in
    "infrastructure-only")
        check_aws_cli
        cleanup_existing_stacks
        upload_templates_to_s3
        deploy_infrastructure
        print_success "Infrastructure deployment completed for $ENVIRONMENT environment"
        ;;
    "application-only")
        check_aws_cli
        check_docker
        deploy_application
        print_success "Application deployment completed for $ENVIRONMENT environment"
        ;;
    "cleanup-only")
        check_aws_cli
        cleanup_existing_stacks
        print_success "Cleanup completed for $ENVIRONMENT environment"
        ;;
    "force-cleanup")
        check_aws_cli
        force_cleanup_all_stacks
        print_success "Force cleanup completed for $ENVIRONMENT environment"
        ;;
    "external-aws")
        main_with_external_role
        ;;
    "external-aws-infrastructure-only")
        assume_external_role
        deploy_infrastructure
        print_success "Infrastructure deployment completed for $ENVIRONMENT environment (with external role)"
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

