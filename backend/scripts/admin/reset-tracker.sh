#!/bin/bash
# Reset WXCC Task Tracker
# Clears all processed task records to allow reprocessing

set -e

# Configuration
API_BASE="${API_BASE:-https://call-api-dev.totogicore.com}"
PROFILE="${AWS_PROFILE:-external-access}"
REGION="${AWS_REGION:-us-east-1}"
TABLE_NAME="${TABLE_NAME:-call-processing-dev-wxcc-task-tracking}"

usage() {
    echo "Usage: $0 [--api|--dynamodb] [--force]"
    echo ""
    echo "Options:"
    echo "  --api       Use API endpoint (default, requires running backend)"
    echo "  --dynamodb  Use AWS CLI directly (requires AWS credentials)"
    echo "  --force     Skip confirmation prompt"
    echo ""
    echo "Environment variables:"
    echo "  API_BASE    API base URL (default: https://call-api-dev.totogicore.com)"
    echo "  AWS_PROFILE AWS profile (default: external-access)"
    echo "  AWS_REGION  AWS region (default: us-east-1)"
    echo "  TABLE_NAME  DynamoDB table (default: call-processing-dev-wxcc-task-tracking)"
    exit 1
}

# Parse arguments
METHOD="api"
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api) METHOD="api"; shift ;;
        --dynamodb) METHOD="dynamodb"; shift ;;
        --force) FORCE=true; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Confirm unless --force
if [ "$FORCE" != "true" ]; then
    echo "⚠️  WARNING: This will clear ALL processed task records!"
    echo "   All tasks will be reprocessed on the next job run."
    echo ""
    read -p "Type 'RESET' to confirm: " confirm
    if [ "$confirm" != "RESET" ]; then
        echo "❌ Cancelled."
        exit 1
    fi
fi

if [ "$METHOD" = "api" ]; then
    echo "🔄 Resetting via API..."
    response=$(curl -s -X POST "${API_BASE}/api/v1/journeys/admin/reset-task-tracker?confirm=true")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "🔄 Resetting via DynamoDB directly..."
    
    # Count items first
    count=$(aws dynamodb scan \
        --table-name "$TABLE_NAME" \
        --profile "$PROFILE" --region "$REGION" \
        --query 'Count' --output text)
    
    echo "   Found $count items to delete..."
    
    if [ "$count" -gt 0 ]; then
        # Delete all items
        aws dynamodb scan \
            --table-name "$TABLE_NAME" \
            --profile "$PROFILE" --region "$REGION" \
            --projection-expression "task_id" \
            --output json | python3 -c "
import json, sys, subprocess
data = json.load(sys.stdin)
deleted = 0
for item in data.get('Items', []):
    task_id = item.get('task_id', {}).get('S', '')
    if task_id:
        subprocess.run([
            'aws', 'dynamodb', 'delete-item',
            '--table-name', '$TABLE_NAME',
            '--key', json.dumps({'task_id': {'S': task_id}}),
            '--profile', '$PROFILE',
            '--region', '$REGION'
        ], capture_output=True)
        deleted += 1
print(f'   Deleted {deleted} items')
"
    fi
    
    # Verify
    remaining=$(aws dynamodb scan \
        --table-name "$TABLE_NAME" \
        --profile "$PROFILE" --region "$REGION" \
        --query 'Count' --output text)
    
    echo ""
    echo "✅ Task tracker reset complete!"
    echo "   Items remaining: $remaining"
fi

echo ""
echo "💡 You can now start a new job - all tasks will be processed."
