#!/bin/bash

# Script to verify what journeys are in DynamoDB vs what the API returns
set -e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
API_KEY="super-secret"

# Function to parse URL and extract components
parse_url() {
    local url="$1"
    
    # Remove protocol (http:// or https://)
    local url_no_protocol="${url#http://}"
    url_no_protocol="${url_no_protocol#https://}"
    
    # Extract host and port
    if [[ "$url_no_protocol" == *":"* ]]; then
        HOST="${url_no_protocol%:*}"
        PORT="${url_no_protocol#*:}"
        # Remove any path after port
        PORT="${PORT%%/*}"
    else
        HOST="$url_no_protocol"
        # Remove any path after host
        HOST="${HOST%%/*}"
        PORT="8000"  # Default port
    fi
    
    # Reconstruct the URL
    if [[ "$url" == https://* ]]; then
        SERVER_URL="https://$HOST:$PORT"
    else
        SERVER_URL="http://$HOST:$PORT"
    fi
}

# Function to show usage
show_usage() {
    echo -e "Journey DynamoDB Verification Script"
    echo ""
    echo -e "Usage: $0 [URL]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                    # Verify on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Verify on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
    echo ""
    echo -e "Description:"
    echo -e "  Verifies what journeys are in DynamoDB vs what the API returns."
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            http://*|https://*)
                parse_url "$1"
                shift
                ;;
            -*)
                echo -e "❌ Unknown option: $1"
                echo -e "💡 Use URL format instead: $0 http://host:port"
                show_usage
                exit 1
                ;;
            *)
                echo -e "❌ Unknown argument: $1"
                echo -e "💡 Use URL format: $0 http://host:port"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Parse command line arguments first
parse_arguments "$@"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}🔍 Verifying Journey Data Sources${NC}"
echo "================================"

echo -e "\n${YELLOW}1️⃣ Testing API Journey List (via MCP Server)${NC}"
echo "Making request to journeys tool..."

api_response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $API_KEY" \
    -d '{"arguments": {"action": "list"}}')

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ API call successful${NC}"
    
    # Extract MCP wrapped response (.content[0].text) and parse inner JSON
    inner_response=$(echo "$api_response" | jq -r '.content[0].text // empty' 2>/dev/null)
    if [[ -z "$inner_response" ]]; then
        inner_response="$api_response"
    fi
    
    # Check if we got journeys
    journeys_count=$(echo "$inner_response" | jq -r '.total_journeys // 0' 2>/dev/null)
    echo -e "${CYAN}Total journeys from API: $journeys_count${NC}"
    
    if [[ "$journeys_count" -gt 0 ]]; then
        echo -e "\n${BLUE}Sample API Journey IDs:${NC}"
        echo "$inner_response" | jq -r '.journeys[]?.journeyId // empty' 2>/dev/null | head -10 | while read journey_id; do
            echo "  📋 $journey_id"
        done
        
        # Show the expected DynamoDB format
        echo -e "\n${BLUE}Expected DynamoDB PK format for these:${NC}"
        echo "$inner_response" | jq -r '.journeys[]?.journeyId // empty' 2>/dev/null | head -5 | while read journey_id; do
            clean_id="${journey_id#JRN-}"
            echo "  🗄️  JOURNEY#$clean_id"
        done
    else
        echo -e "${YELLOW}⚠️  No journeys returned from API${NC}"
    fi
else
    echo -e "${RED}❌ API call failed${NC}"
fi

echo -e "\n${YELLOW}2️⃣ Checking AWS CLI Access to DynamoDB${NC}"

# Check if AWS CLI is available and can access DynamoDB
if command -v aws >/dev/null 2>&1; then
    echo "Checking DynamoDB table access..."
    
    # Try to scan the table
    scan_result=$(aws dynamodb scan \
        --table-name TransformationSystem \
        --index-name GSI1 \
        --filter-expression "GSI1PK = :pk" \
        --expression-attribute-values '{":pk":{"S":"JOURNEYS"}}' \
        --select "COUNT" \
        --no-cli-pager 2>/dev/null || echo "ERROR")
    
    if [[ "$scan_result" != "ERROR" ]]; then
        dynamodb_count=$(echo "$scan_result" | jq -r '.Count // 0' 2>/dev/null)
        echo -e "${GREEN}✅ DynamoDB accessible${NC}"
        echo -e "${CYAN}Total journeys in DynamoDB: $dynamodb_count${NC}"
        
        # Get actual journey IDs from DynamoDB
        echo -e "\n${BLUE}Sample DynamoDB Journey PKs:${NC}"
        aws dynamodb scan \
            --table-name TransformationSystem \
            --index-name GSI1 \
            --filter-expression "GSI1PK = :pk" \
            --expression-attribute-values '{":pk":{"S":"JOURNEYS"}}' \
            --projection-expression "PK" \
            --max-items 10 \
            --no-cli-pager 2>/dev/null | \
        jq -r '.Items[]?.PK.S // empty' 2>/dev/null | head -10 | while read pk; do
            echo "  🗄️  $pk"
            # Convert to API format
            if [[ "$pk" =~ ^JOURNEY#(.+)$ ]]; then
                api_id="JRN-${BASH_REMATCH[1]}"
                echo "    → API format: $api_id"
            fi
        done
        
        # Check for consistency
        echo -e "\n${YELLOW}3️⃣ Consistency Check${NC}"
        if [[ "$journeys_count" -eq "$dynamodb_count" ]]; then
            echo -e "${GREEN}✅ Journey counts match! ($journeys_count)${NC}"
        else
            echo -e "${RED}❌ Journey count mismatch!${NC}"
            echo -e "   API reports: $journeys_count journeys"
            echo -e "   DynamoDB has: $dynamodb_count journeys"
        fi
        
    else
        echo -e "${RED}❌ Cannot access DynamoDB table${NC}"
        echo -e "${YELLOW}This could be due to:${NC}"
        echo -e "  • AWS credentials not configured"
        echo -e "  • Insufficient permissions"
        echo -e "  • Table doesn't exist"
        echo -e "  • Wrong region"
    fi
else
    echo -e "${YELLOW}⚠️  AWS CLI not available - cannot check DynamoDB directly${NC}"
fi

echo -e "\n${YELLOW}4️⃣ Summary${NC}"
echo "============"
echo -e "${CYAN}This verification helps determine if:${NC}"
echo -e "• The MCP server is reading from the correct DynamoDB table"
echo -e "• Journey IDs are being converted correctly between API and storage"
echo -e "• The cleanup script is working with the right data source"
echo ""
echo -e "${BLUE}If counts don't match, the journeys tool might be:${NC}"
echo -e "• Using a different table"
echo -e "• Using cached/mock data"
echo -e "• Filtering results differently" 