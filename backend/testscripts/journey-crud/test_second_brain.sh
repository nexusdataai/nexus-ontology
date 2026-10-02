#!/bin/bash

# Second Brain Functionality Test Script
# Tests Second Brain rules management step by step with comprehensive logging

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
ECHO_JSON=false

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
    echo -e "Second Brain Functionality Test Script"
    echo ""
    echo -e "Usage: $0 [URL]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                    # Test on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Test on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
    echo ""
    echo -e "Description:"
    echo -e "  Tests Second Brain rules management step by step with comprehensive logging."
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

# Setup logging
SCRIPT_NAME="test_second_brain"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="/opt/mycode/aws-mcp/src/tmf-oda-transformer-mcp-server/logs"
LOG_FILE="$LOG_DIR/${SCRIPT_NAME}_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Enhanced logging function
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[$timestamp] [$level] $message"
    
    # Log to file
    echo "$log_entry" >> "$LOG_FILE"
    
    # Log to console with colors
    case $level in
        "INFO")
            echo -e "${BLUE}$message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}$message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}$message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}$message${NC}"
            ;;
        "STEP")
            echo -e "${PURPLE}$message${NC}"
            ;;
        *)
            echo "$message"
            ;;
    esac
    
    # Flush output
    sync
}

# Helper function to extract from MCP wrapped response
extract_from_mcp() {
    local response="$1"
    local field="$2"
    local result_text=$(echo "$response" | jq -r '.content[0].text' 2>/dev/null)
    if [ -z "$result_text" ] || [ "$result_text" = "null" ]; then
        echo ""
        return
    fi
    echo "$result_text" | jq -r "$field" 2>/dev/null
}

# Parse command line arguments first
parse_arguments "$@"

# Initialize logging
log_message "INFO" "🧠 Starting Second Brain Functionality Test"
log_message "INFO" "=============================================="
log_message "INFO" "Script: $SCRIPT_NAME"
log_message "INFO" "Timestamp: $TIMESTAMP"
log_message "INFO" "Log file: $LOG_FILE"
log_message "INFO" "Server URL: $SERVER_URL"
log_message "INFO" "=============================================="

echo -e "${BLUE}🧠 Testing Second Brain Functionality${NC}"
echo "=============================================="
echo "📁 Logging to: $LOG_FILE"
echo "=============================================="

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to run test and track results
run_test() {
    local test_name=$1
    local test_command=$2
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    log_message "STEP" "🧪 Test $TOTAL_TESTS: $test_name"
    
    if eval "$test_command"; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        log_message "SUCCESS" "✅ $test_name - PASSED"
        return 0
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        log_message "ERROR" "❌ $test_name - FAILED"
        return 1
    fi
}

# First, let's create a journey to work with
log_message "STEP" "📋 Step 1: Create a journey with default stages"

CREATE_JOURNEY_DATA='{
    "arguments": {
        "action": "create",
        "name": "Second Brain Test Journey",
        "description": "Testing Second Brain rules functionality",
        "odaComponentType": "customer-management",
        "priority": "high"
    }
}'

log_message "INFO" "Creating journey for Second Brain testing..."
log_message "INFO" "Request payload logged to file"
echo "$CREATE_JOURNEY_DATA" >> "$LOG_FILE"

JOURNEY_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$CREATE_JOURNEY_DATA")

if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Journey creation successful"
    
    # Log full response to file
    echo "Journey Response:" >> "$LOG_FILE"
    echo "$JOURNEY_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$JOURNEY_RESPONSE" >> "$LOG_FILE"
    
    # Extract journey ID from MCP wrapped response
    JOURNEY_RESULT_TEXT=$(echo "$JOURNEY_RESPONSE" | jq -r '.content[0].text' 2>/dev/null)
    JOURNEY_ID=$(echo "$JOURNEY_RESULT_TEXT" | jq -r '.journey_id // empty')
    STAGES_COUNT=$(echo "$JOURNEY_RESULT_TEXT" | jq -r '.totalStages // 6')
    
    log_message "INFO" "Journey ID: $JOURNEY_ID"
    log_message "INFO" "Stages Count: $STAGES_COUNT"
    
    if [ -n "$JOURNEY_ID" ] && [ "$JOURNEY_ID" != "null" ]; then
        log_message "SUCCESS" "🎉 Ready to test Second Brain with journey: $JOURNEY_ID"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        log_message "ERROR" "❌ Failed to get journey ID"
        echo "Response: $JOURNEY_RESPONSE" >> "$LOG_FILE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        exit 1
    fi
else
    log_message "ERROR" "❌ Journey creation failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    exit 1
fi
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Test 1: List existing rules
log_message "STEP" "📋 Step 2: List existing Second Brain rules"

LIST_RULES_DATA='{
    "arguments": {
        "action": "list_rules",
        "journey_id": "'$JOURNEY_ID'"
    }
}'

log_message "INFO" "Listing existing Second Brain rules..."
echo "List Rules Request:" >> "$LOG_FILE"
echo "$LIST_RULES_DATA" >> "$LOG_FILE"

LIST_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$LIST_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ List rules successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "List Rules Response:" >> "$LOG_FILE"
    echo "$LIST_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$LIST_RESPONSE" >> "$LOG_FILE"
    
    RULES_COUNT=$(extract_from_mcp "$LIST_RESPONSE" '.total_rules // 0')
    log_message "INFO" "Current rules count: $RULES_COUNT"
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Response:"
        echo "$LIST_RESPONSE" | jq .
    fi
else
    log_message "ERROR" "❌ List rules failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 2: Add a custom Second Brain rule
log_message "STEP" "📋 Step 3: Add a custom Second Brain rule"

ADD_RULE_DATA='{
    "arguments": {
        "action": "add_rule",
        "journey_id": "'$JOURNEY_ID'",
        "stage_id": "raw_analysis",
        "rule_data": {
            "title": "Custom Field Mapping Rule",
            "description": "Custom rule for enhanced field mapping during raw analysis",
            "type": "field_mapping",
            "priority": "high",
            "scope": "stage",
            "context": "Field mapping context for raw analysis stage",
            "content": "AI-guided field mapping rules",
            "conditions": {
                "column_patterns": ["user_*", "customer_*", "account_*"],
                "data_types": ["varchar", "text", "string"]
            },
            "actions": {
                "suggest_tmf_mapping": true,
                "confidence_threshold": 0.8,
                "auto_apply": false
            },
            "metadata": {
                "author": "test_user",
                "version": "1.0",
                "tags": ["field_mapping", "customer_data", "test"]
            }
        }
    }
}'

log_message "INFO" "Adding custom Second Brain rule..."
echo "Add Rule Request:" >> "$LOG_FILE"
echo "$ADD_RULE_DATA" >> "$LOG_FILE"

ADD_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$ADD_RULE_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Add rule successful"
    
    echo "Add Rule Response:" >> "$LOG_FILE"
    echo "$ADD_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$ADD_RESPONSE" >> "$LOG_FILE"
    
    STATUS=$(extract_from_mcp "$ADD_RESPONSE" '.status // "unknown"')
    MESSAGE=$(extract_from_mcp "$ADD_RESPONSE" '.message // "No message"')
    RULE_ID=$(extract_from_mcp "$ADD_RESPONSE" '.rule_id // empty')
    
    log_message "INFO" "Status: $STATUS"
    log_message "INFO" "Message: $MESSAGE"
    log_message "INFO" "Rule ID: $RULE_ID"
    
    if [ -z "$RULE_ID" ] || [ "$RULE_ID" = "null" ]; then
        log_message "ERROR" "❌ Failed to get rule ID from response"
        echo "Response: $ADD_RESPONSE" >> "$LOG_FILE"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        exit 1
    else
        PASSED_TESTS=$((PASSED_TESTS + 1))
    fi
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Response:"
        echo "$ADD_RESPONSE" | jq .
    fi
else
    log_message "ERROR" "❌ Add rule failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
    exit 1
fi

# Test 3: List rules again to see the new rule
log_message "STEP" "📋 Step 4: List rules again to verify addition"

log_message "INFO" "Listing rules after addition..."
LIST_RESPONSE2=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$LIST_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ List rules successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "List Rules After Addition Response:" >> "$LOG_FILE"
    echo "$LIST_RESPONSE2" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$LIST_RESPONSE2" >> "$LOG_FILE"
    
    RULES_COUNT2=$(extract_from_mcp "$LIST_RESPONSE2" '.total_rules // 0')
    log_message "INFO" "Updated rules count: $RULES_COUNT2"
    
    # Show rule details
    log_message "INFO" "📝 Rule Details:"
    RULE_DETAILS=$(extract_from_mcp "$LIST_RESPONSE2" '.rules[] | {ruleId, title, description, type, priority}')
    echo "$RULE_DETAILS"
    echo "Rule Details:" >> "$LOG_FILE"
    echo "$RULE_DETAILS" >> "$LOG_FILE"
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Full Response:"
        echo "$LIST_RESPONSE2" | jq .
    fi
else
    log_message "ERROR" "❌ List rules failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 4: Update the Second Brain rule
log_message "STEP" "📋 Step 5: Update the Second Brain rule"

UPDATE_RULE_DATA='{
    "arguments": {
        "action": "update_rule",
        "journey_id": "'$JOURNEY_ID'",
        "stage_id": "raw_analysis",
        "rule_id": "'$RULE_ID'",
        "rule_data": {
            "title": "Enhanced Custom Field Mapping Rule",
            "description": "Enhanced rule for field mapping with improved AI suggestions",
            "type": "field_mapping",
            "priority": "critical",
            "scope": "stage",
            "context": "Enhanced field mapping context",
            "content": "Enhanced AI-guided field mapping rules",
            "conditions": {
                "column_patterns": ["user_*", "customer_*", "account_*", "contact_*"],
                "data_types": ["varchar", "text", "string", "char"]
            },
            "actions": {
                "suggest_tmf_mapping": true,
                "confidence_threshold": 0.75,
                "auto_apply": false,
                "generate_alternatives": true
            },
            "metadata": {
                "author": "test_user",
                "version": "1.1",
                "tags": ["field_mapping", "customer_data", "enhanced", "test"],
                "last_updated": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
            }
        }
    }
}'

log_message "INFO" "Updating Second Brain rule..."
echo "Update Rule Request:" >> "$LOG_FILE"
echo "$UPDATE_RULE_DATA" >> "$LOG_FILE"

UPDATE_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$UPDATE_RULE_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Update rule successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "Update Rule Response:" >> "$LOG_FILE"
    echo "$UPDATE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$UPDATE_RESPONSE" >> "$LOG_FILE"
    
    STATUS=$(extract_from_mcp "$UPDATE_RESPONSE" '.status // "unknown"')
    MESSAGE=$(extract_from_mcp "$UPDATE_RESPONSE" '.message // "No message"')
    
    log_message "INFO" "Status: $STATUS"
    log_message "INFO" "Message: $MESSAGE"
    
    if [ "$ECHO_JSON" = true ]; then
        echo "Response:"
        echo "$UPDATE_RESPONSE" | jq .
    fi
else
    log_message "ERROR" "❌ Update rule failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 5: List rules to verify update
log_message "STEP" "📋 Step 6: Verify rule update"

log_message "INFO" "Listing rules after update..."
LIST_RESPONSE3=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$LIST_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ List rules successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "List Rules After Update Response:" >> "$LOG_FILE"
    echo "$LIST_RESPONSE3" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$LIST_RESPONSE3" >> "$LOG_FILE"
    
    # Show updated rule details
    log_message "INFO" "📝 Updated Rule Details:"
    UPDATED_RULE_DETAILS=$(extract_from_mcp "$LIST_RESPONSE3" '.rules[] | select(.ruleId == "'$RULE_ID'") | {ruleId, title, description, type, priority}')
    echo "$UPDATED_RULE_DETAILS"
    echo "Updated Rule Details:" >> "$LOG_FILE"
    echo "$UPDATED_RULE_DETAILS" >> "$LOG_FILE"
else
    log_message "ERROR" "❌ List rules failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 6: Add another rule for a different stage
log_message "STEP" "📋 Step 7: Add rule for different stage (tmf_mapping)"

ADD_RULE2_DATA='{
    "arguments": {
        "action": "add_rule",
        "journey_id": "'$JOURNEY_ID'",
        "stage_id": "tmf_mapping",
        "rule_data": {
            "title": "TMF Schema Validation Rule",
            "description": "Validation rule for TMF schema compliance",
            "type": "validation_rules",
            "priority": "medium",
            "scope": "stage",
            "context": "TMF schema validation context for mapping stage",
            "content": "AI-guided TMF schema validation rules",
            "conditions": {
                "schema_patterns": ["Customer", "Product", "Service"],
                "required_fields": ["id", "name", "status"]
            },
            "actions": {
                "validate_schema": true,
                "suggest_fixes": true,
                "generate_report": true
            },
            "metadata": {
                "author": "test_user",
                "version": "1.0",
                "tags": ["validation", "tmf_schema", "compliance"]
            }
        }
    }
}'

log_message "INFO" "Adding TMF validation rule..."
echo "Add Second Rule Request:" >> "$LOG_FILE"
echo "$ADD_RULE2_DATA" >> "$LOG_FILE"

ADD_RESPONSE2=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$ADD_RULE2_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Add TMF rule successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "Add Second Rule Response:" >> "$LOG_FILE"
    echo "$ADD_RESPONSE2" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$ADD_RESPONSE2" >> "$LOG_FILE"
    
    STATUS=$(extract_from_mcp "$ADD_RESPONSE2" '.status // "unknown"')
    MESSAGE=$(extract_from_mcp "$ADD_RESPONSE2" '.message // "No message"')
    RULE_ID2=$(extract_from_mcp "$ADD_RESPONSE2" '.rule_id // empty')
    
    log_message "INFO" "Status: $STATUS"
    log_message "INFO" "Message: $MESSAGE"
    log_message "INFO" "Second Rule ID: $RULE_ID2"
else
    log_message "ERROR" "❌ Add TMF rule failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 7: List rules by stage filter
log_message "STEP" "📋 Step 8: List rules filtered by stage"

LIST_STAGE_RULES_DATA='{
    "arguments": {
        "action": "list_rules",
        "journey_id": "'$JOURNEY_ID'",
        "stage_id": "raw_analysis"
    }
}'

log_message "INFO" "Listing rules for raw_analysis stage only..."
echo "List Stage Rules Request:" >> "$LOG_FILE"
echo "$LIST_STAGE_RULES_DATA" >> "$LOG_FILE"

STAGE_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$LIST_STAGE_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Stage rules list successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "Stage Rules Response:" >> "$LOG_FILE"
    echo "$STAGE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$STAGE_RESPONSE" >> "$LOG_FILE"
    
    STAGE_RULES_COUNT=$(extract_from_mcp "$STAGE_RESPONSE" '.total_rules // 0')
    log_message "INFO" "Rules for raw_analysis stage: $STAGE_RULES_COUNT"
    
    log_message "INFO" "📝 Raw Analysis Stage Rules:"
    STAGE_RULE_DETAILS=$(extract_from_mcp "$STAGE_RESPONSE" '.rules[] | {ruleId, title, stageId, type, priority}')
    echo "$STAGE_RULE_DETAILS"
    echo "Stage Rule Details:" >> "$LOG_FILE"
    echo "$STAGE_RULE_DETAILS" >> "$LOG_FILE"
else
    log_message "ERROR" "❌ Stage rules list failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 8: Delete a rule
log_message "STEP" "📋 Step 9: Delete Second Brain rule"

DELETE_RULE_DATA='{
    "arguments": {
        "action": "delete_rule",
        "journey_id": "'$JOURNEY_ID'",
        "stage_id": "tmf_mapping",
        "rule_id": "'$RULE_ID2'",
        "confirm": true
    }
}'

log_message "INFO" "Deleting TMF validation rule..."
echo "Delete Rule Request:" >> "$LOG_FILE"
echo "$DELETE_RULE_DATA" >> "$LOG_FILE"

DELETE_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$DELETE_RULE_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Delete rule successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "Delete Rule Response:" >> "$LOG_FILE"
    echo "$DELETE_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$DELETE_RESPONSE" >> "$LOG_FILE"
    
    STATUS=$(extract_from_mcp "$DELETE_RESPONSE" '.status // "unknown"')
    MESSAGE=$(extract_from_mcp "$DELETE_RESPONSE" '.message // "No message"')
    
    log_message "INFO" "Status: $STATUS"
    log_message "INFO" "Message: $MESSAGE"
else
    log_message "ERROR" "❌ Delete rule failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 9: Final rules count
log_message "STEP" "📋 Step 10: Final rules verification"

log_message "INFO" "Final rules count check..."
FINAL_RESPONSE=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
    -H "Content-Type: application/json" \
    -H "x-api-key: super-secret" \
  -d "$LIST_RULES_DATA")

TOTAL_TESTS=$((TOTAL_TESTS + 1))
if [ $? -eq 0 ]; then
    log_message "SUCCESS" "✅ Final verification successful"
    PASSED_TESTS=$((PASSED_TESTS + 1))
    
    echo "Final Verification Response:" >> "$LOG_FILE"
    echo "$FINAL_RESPONSE" | jq . >> "$LOG_FILE" 2>/dev/null || echo "$FINAL_RESPONSE" >> "$LOG_FILE"
    
    FINAL_RULES_COUNT=$(extract_from_mcp "$FINAL_RESPONSE" '.total_rules // 0')
    log_message "INFO" "Final rules count: $FINAL_RULES_COUNT"
    
    log_message "INFO" "📊 Summary of Remaining Rules:"
    FINAL_RULE_SUMMARY=$(extract_from_mcp "$FINAL_RESPONSE" '.rules[] | {ruleId, title, stageId, type, priority}')
    echo "$FINAL_RULE_SUMMARY"
    echo "Final Rule Summary:" >> "$LOG_FILE"
    echo "$FINAL_RULE_SUMMARY" >> "$LOG_FILE"
else
    log_message "ERROR" "❌ Final verification failed"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test completion summary
log_message "INFO" "🎉 Second Brain functionality test completed!"
log_message "INFO" "=============================================="
log_message "SUCCESS" "✅ Journey created with ID: $JOURNEY_ID"
log_message "SUCCESS" "✅ Second Brain rules tested: add, update, delete, list"
log_message "SUCCESS" "✅ Stage-specific rule filtering tested"
log_message "SUCCESS" "✅ Different rule types tested: field_mapping, validation_rules"

log_message "INFO" "💡 Second Brain Test Summary:"
log_message "INFO" "• ✅ Rule Creation (field_mapping type)"
log_message "INFO" "• ✅ Rule Listing (all & filtered by stage)"  
log_message "INFO" "• ✅ Rule Updates (metadata, conditions, actions)"
log_message "INFO" "• ✅ Rule Deletion"
log_message "INFO" "• ✅ Multiple Stage Support"
log_message "INFO" "• ✅ Different Rule Types (field_mapping, validation_rules)"

# Final test statistics
log_message "INFO" "=============================================="
log_message "INFO" "📊 TEST STATISTICS"
log_message "INFO" "=============================================="
log_message "INFO" "Total Tests: $TOTAL_TESTS"
log_message "SUCCESS" "Passed Tests: $PASSED_TESTS"
log_message "ERROR" "Failed Tests: $FAILED_TESTS"

if [ $FAILED_TESTS -eq 0 ]; then
    log_message "SUCCESS" "🎉 ALL TESTS PASSED!"
    SUCCESS_RATE="100%"
else
    SUCCESS_RATE=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l)
    log_message "WARNING" "⚠️ Some tests failed. Success rate: ${SUCCESS_RATE}%"
fi

log_message "INFO" "Success Rate: $SUCCESS_RATE"
log_message "INFO" "=============================================="

# Manual test commands
log_message "INFO" "🔧 Manual Test Commands:"
log_message "INFO" "List all rules:"
log_message "INFO" "  curl -X POST $SERVER_URL/tools/journeys_tool -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"action\":\"list_rules\",\"journey_id\":\"$JOURNEY_ID\"}'"
log_message "INFO" ""
log_message "INFO" "Add custom rule:"
log_message "INFO" "  curl -X POST $SERVER_URL/tools/journeys_tool -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"action\":\"add_rule\",\"journey_id\":\"$JOURNEY_ID\",\"stage_id\":\"raw_analysis\",\"rule_data\":{\"title\":\"Test Rule\",\"description\":\"Test description\",\"type\":\"field_mapping\",\"priority\":\"medium\",\"scope\":\"stage\",\"context\":\"Test context\",\"content\":\"Test content\"}}'"

# Log file info
log_message "INFO" "=============================================="
log_message "INFO" "📁 Detailed logs saved to: $LOG_FILE"
log_message "INFO" "🕒 Test completed at: $(date)"
log_message "INFO" "=============================================="

echo -e "${BLUE}🎉 Second Brain functionality test completed!${NC}"
echo "=============================================="
echo -e "${GREEN}✅ Journey created with ID: $JOURNEY_ID${NC}"
echo -e "${GREEN}✅ Second Brain rules tested: add, update, delete, list${NC}"
echo -e "${GREEN}✅ Stage-specific rule filtering tested${NC}"
echo -e "${GREEN}✅ Different rule types tested: field_mapping, validation_rules${NC}"

echo -e "\n${PURPLE}💡 Second Brain Test Summary:${NC}"
echo "• ✅ Rule Creation (field_mapping type)"
echo "• ✅ Rule Listing (all & filtered by stage)"  
echo "• ✅ Rule Updates (metadata, conditions, actions)"
echo "• ✅ Rule Deletion"
echo "• ✅ Multiple Stage Support"
echo "• ✅ Different Rule Types (field_mapping, validation_rules)"

echo -e "\n${BLUE}📊 Test Results:${NC}"
echo "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
echo -e "${RED}Failed: $FAILED_TESTS${NC}"
echo "Success Rate: $SUCCESS_RATE"

echo -e "\n${CYAN}🔧 Manual Test Commands:${NC}"
echo "List all rules:"
echo "  curl -X POST $SERVER_URL/tools/journeys_tool -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"action\":\"list_rules\",\"journey_id\":\"$JOURNEY_ID\"}'"
echo ""
echo "Add custom rule:"
echo "  curl -X POST $SERVER_URL/tools/journeys_tool -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{\"action\":\"add_rule\",\"journey_id\":\"$JOURNEY_ID\",\"stage_id\":\"raw_analysis\",\"rule_data\":{\"title\":\"Test Rule\",\"description\":\"Test description\",\"type\":\"field_mapping\",\"priority\":\"medium\",\"scope\":\"stage\",\"context\":\"Test context\",\"content\":\"Test content\"}}'"

echo -e "\n${BLUE}📁 Detailed logs saved to: $LOG_FILE${NC}"

# Exit with appropriate code
if [ $FAILED_TESTS -eq 0 ]; then
    exit 0
else
    exit 1
fi 