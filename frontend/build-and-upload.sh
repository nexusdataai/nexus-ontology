#!/bin/bash

# Simple Build and Upload Script for Nexus Telco UI
# Usage: ./build-and-upload.sh <s3-bucket> [s3-path]
# Example: ./build-and-upload.sh my-bucket
# Example: ./build-and-upload.sh my-bucket nexus-ui/builds

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# AWS Profile configuration
AWS_PROFILE="${AWS_PROFILE:-external-access}"

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <s3-bucket> [s3-path]"
    echo "Examples:"
    echo "  $0 my-bucket                    # Upload to bucket root"
    echo "  $0 my-bucket nexus-ui/builds  # Upload to specific path"
    exit 1
fi

S3_BUCKET=$1
S3_PATH=${2:-""}

# Get project root (directory where this script lives)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

echo -e "${GREEN}Starting build process...${NC}"

# Step 1: Clean
echo "Cleaning previous build..."
npm run clean

# Step 2: Build
echo "Building application..."
npm run build

# Step 3: Ensure public folder contents are included in dist
# Vite should copy these automatically, but we ensure critical folders exist
echo "Ensuring public folder contents are in dist..."
if [ -d "public/results" ]; then
    cp -r public/results dist/
    echo "  ✓ Copied results folder"
fi
if [ -d "public/transcripts" ]; then
    cp -r public/transcripts dist/
    echo "  ✓ Copied transcripts folder"
fi
if [ -d "public/recordings" ]; then
    cp -r public/recordings dist/
    echo "  ✓ Copied recordings folder"
fi

# Step 4: Get version from package.json
VERSION=$(node -p "require('./package.json').version")
ZIP_NAME="nexus-ui-${VERSION}.zip"

# Step 5: Create zip
echo "Creating ${ZIP_NAME}..."
cd dist
zip -r "../${ZIP_NAME}" . -q
cd ..

# Step 6: Upload to S3
echo "Uploading to S3 (profile: $AWS_PROFILE)..."
if [ -z "$S3_PATH" ]; then
    # Upload to bucket root
    aws s3 cp "${ZIP_NAME}" "s3://${S3_BUCKET}/${ZIP_NAME}" --profile "$AWS_PROFILE"
    UPLOAD_PATH="s3://${S3_BUCKET}/${ZIP_NAME}"
else
    # Upload to specific path
    aws s3 cp "${ZIP_NAME}" "s3://${S3_BUCKET}/${S3_PATH}/${ZIP_NAME}" --profile "$AWS_PROFILE"
    UPLOAD_PATH="s3://${S3_BUCKET}/${S3_PATH}/${ZIP_NAME}"
fi

# Step 7: Clean up local zip
rm "${ZIP_NAME}"

echo -e "${GREEN}✓ Complete!${NC}"
echo "Uploaded: ${UPLOAD_PATH}"
