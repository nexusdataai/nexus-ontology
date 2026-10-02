#!/bin/bash

# alert-engine MCP Server - Build, Push, and Deploy Script
set -e

# Check if environment parameter is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <environment> [command]"
    echo ""
    echo "Environments:"
    echo "  dev   - Development environment"
    echo "  stage - Staging environment"
    echo "  prod  - Production environment"
    echo ""
    echo "Commands (optional):"
    echo "  build-only       - Only build and push container"
    echo "  deploy-only      - Only deploy CloudFormation"
    echo "  (no command)     - Build, push, and deploy"
    exit 1
fi

ENVIRONMENT=$1
COMMAND=${2:-""}

# Load configuration
if [ -f "config/${ENVIRONMENT}.conf" ]; then
    source config/${ENVIRONMENT}.conf
else
    echo "❌ Configuration file config/${ENVIRONMENT}.conf not found"
    exit 1
fi

# Extract ECR details from DOCKER_IMAGE_URI
ECR_REGISTRY=$(echo $DOCKER_IMAGE_URI | cut -d'/' -f1)
ECR_REPOSITORY=$(echo $DOCKER_IMAGE_URI | cut -d'/' -f2 | cut -d':' -f1)
IMAGE_TAG=$(echo $DOCKER_IMAGE_URI | cut -d':' -f2)

echo "🚀 alert-engine MCP Server - Build, Push, and Deploy"
echo "   Environment: $ENVIRONMENT"
echo "   Registry: $ECR_REGISTRY"
echo "   Repository: $ECR_REPOSITORY"
echo "   Tag: $IMAGE_TAG"
echo "   Command: ${COMMAND:-'full deployment'}"
echo ""

# Skip build steps if deploy-only
if [ "$COMMAND" != "deploy-only" ]; then
    # Step 1: Check if ECR repository exists
    echo "🔍 Checking ECR repository..."
    if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION >/dev/null 2>&1; then
        echo "📦 Creating ECR repository: $ECR_REPOSITORY"
        aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    else
        echo "✅ ECR repository exists"
    fi

    # Step 2: Login to ECR
    echo "🔐 Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

    # Step 3: Build Docker image
    echo "🔨 Building Docker image..."
    cd ..
    docker build -t $ECR_REPOSITORY:$IMAGE_TAG .
    docker tag $ECR_REPOSITORY:$IMAGE_TAG $DOCKER_IMAGE_URI

    # Step 4: Push to ECR
    echo "📤 Pushing image to ECR..."
    docker push $DOCKER_IMAGE_URI

    echo "✅ Container image pushed successfully!"
    echo "   Image URI: $DOCKER_IMAGE_URI"
    
    # Return to deploy directory
    cd deploy
fi

# Handle different commands
if [ "$COMMAND" = "build-only" ]; then
    echo ""
    echo "🎉 Build and push completed successfully!"
    echo "   Container: $DOCKER_IMAGE_URI"
    exit 0
elif [ "$COMMAND" = "deploy-only" ]; then
    echo "⏭️  Skipping build (deploy-only mode)"
fi

# Step 5: Deploy CloudFormation
echo ""
echo "🚀 Deploying CloudFormation stack..."
./deploy.sh $ENVIRONMENT

echo ""
echo "🎉 Build and deployment completed successfully!"
echo "   Environment: $ENVIRONMENT"
echo "   Container: $DOCKER_IMAGE_URI"
echo "   Stack: $MAIN_STACK_NAME"
