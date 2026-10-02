#!/bin/bash

# Refresh AWS Credentials Script
# This script logs into AWS and refreshes the gateway's credentials without restarting it

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

# Step 1: Run aws-login.sh to refresh credentials
echo "Step 1: Running aws-login.sh to refresh AWS credentials..."
echo ""
./aws-login.sh

# Check if login was successful
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ AWS login failed. Please check your credentials and try again."
    exit 1
fi

echo ""
echo "✅ AWS credentials refreshed in credential file"
echo ""

# Step 2: Check if gateway is running
echo "Step 2: Checking if gateway is running..."
if [ ! -f .gateway.pid ]; then
    echo "⚠️  Gateway PID file not found. Gateway may not be running."
    echo ""
    echo "To start the gateway, run: ./gateway.sh start"
    exit 0
fi

GATEWAY_PID=$(cat .gateway.pid)
if ! kill -0 "$GATEWAY_PID" 2>/dev/null; then
    echo "⚠️  Gateway is not running (PID $GATEWAY_PID not found)"
    echo ""
    echo "To start the gateway, run: ./gateway.sh start"
    exit 0
fi

echo "✅ Gateway is running (PID: $GATEWAY_PID)"
echo ""

# Step 3: Trigger credential refresh via API
echo "Step 3: Triggering credential refresh in gateway..."
echo ""

API_KEY=$(grep "API_KEY=" .env 2>/dev/null | cut -d= -f2 || echo "super-secret")
GATEWAY_URL="http://localhost:8000"

RESPONSE=$(curl -s -X POST "$GATEWAY_URL/admin/refresh-aws-credentials" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY")

echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
echo ""

# Check if refresh was successful
if echo "$RESPONSE" | grep -q '"status": *"success"'; then
    echo "✅ Gateway credentials refreshed successfully!"
    echo ""
    echo "The gateway is now using the new AWS credentials."
    echo "No restart required!"
else
    echo "❌ Failed to refresh gateway credentials via API"
    echo ""
    echo "You may need to restart the gateway manually:"
    echo "  ./gateway.sh restart"
    exit 1
fi

echo ""
echo "=========================================="
echo "Credential refresh complete!"
echo "=========================================="

