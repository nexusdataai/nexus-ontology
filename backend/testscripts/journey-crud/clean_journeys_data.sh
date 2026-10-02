#!/bin/bash

# =============================================================================
# TMF ODA Transformer MCP Server - Journey Data Cleanup Script
# =============================================================================
# This script safely removes ALL journey data from the system
# Usage: ./clean_journeys_data.sh [URL] [--force]
# Default URL: http://localhost:8000
#
# Examples:
#   ./clean_journeys_data.sh --force                          # Use default URL with force mode
#   ./clean_journeys_data.sh http://localhost:8080 --force    # Use custom URL with force mode
#   ./clean_journeys_data.sh http://localhost:8080            # Use custom URL, prompt for confirmation
# 
# SAFETY FEATURES:
# - Lists all journeys before deletion for review
# - Requires user confirmation unless --force flag is used
# - Provides detailed progress reporting
# - Logs all operations for audit trail
# - Handles errors gracefully
# 
# WHAT IT CLEANS:
# - All journey metadata from DynamoDB
# - All associated stages for each journey
# - All related DynamoDB items (PK = JOURNEY#*)
# 
# WARNING: This operation is IRREVERSIBLE!
# =============================================================================

set -e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
API_KEY="super-secret"
FORCE_MODE=false
TIMEOUT=30

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
    echo -e "TMF ODA Transformer MCP Server - Journey Data Cleanup Script"
    echo ""
    echo -e "Usage: $0 [URL] [--force]"
    echo ""
    echo -e "Arguments:"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo -e "  --force                Skip confirmation prompts"
    echo ""
    echo -e "Examples:"
    echo -e "  $0                                    # Clean on localhost:8000 with confirmation"
    echo -e "  $0 --force                            # Clean on localhost:8000 without confirmation"
    echo -e "  $0 http://192.168.1.100:8000          # Clean on remote server with confirmation"
    echo -e "  $0 http://192.168.1.100:8000 --force  # Clean on remote server without confirmation"
    echo -e "  $0 https://api.company.com --force    # Clean on HTTPS server without confirmation"
    echo ""
    echo -e "Description:"
    echo -e "  Safely removes ALL journey data from the system."
    echo -e "  WARNING: This operation is IRREVERSIBLE!"
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
            --force)
                FORCE_MODE=true
                shift
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
                echo -e "💡 Use URL format: $0 http://host:port [--force]"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Parse command line arguments first
parse_arguments "$@"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Logging configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/clean_journeys_$(date +%Y-%m-%d_%H-%M-%S).log"
EXECUTION_ID="CLEAN_$(date +%s)"

# Initialize logging
setup_logging() {
    echo "=== Journey Data Cleanup Log - $(date) ===" > "$LOG_FILE"
    echo "Execution ID: $EXECUTION_ID" >> "$LOG_FILE"
    echo "Server URL: $SERVER_URL" >> "$LOG_FILE"
    echo "Force Mode: $FORCE_MODE" >> "$LOG_FILE"
    echo "Log File: $LOG_FILE" >> "$LOG_FILE"
    echo "=========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# Enhanced logging functions
log_to_file() {
    local level="$1"
    local message="$2"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $level | $message" >> "$LOG_FILE"
}

# Logging functions
log_info() {
    local message="$1"
    echo -e "${BLUE}ℹ️  $message${NC}"
    log_to_file "INFO" "$message"
}

log_success() {
    local message="$1"
    echo -e "${GREEN}✅ $message${NC}"
    log_to_file "SUCCESS" "$message"
}

log_error() {
    local message="$1"
    echo -e "${RED}❌ $message${NC}"
    log_to_file "ERROR" "$message"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}⚠️  $message${NC}"
    log_to_file "WARNING" "$message"
}

log_step() {
    local message="$1"
    echo -e "${PURPLE}🔄 $message${NC}"
    log_to_file "STEP" "$message"
}

log_debug() {
    local message="$1"
    log_to_file "DEBUG" "$message"
}

# Initialize logging
setup_logging

# Counters
TOTAL_JOURNEYS=0
DELETED_JOURNEYS=0
FAILED_DELETIONS=0

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Function to log to both console and file
log_message() {
    local message="$1"
    local no_color_message=$(echo -e "$message" | sed 's/\x1b\[[0-9;]*m//g')
    echo -e "$message" >&2  # Send to stderr to avoid contaminating stdout
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $no_color_message" >> "$LOG_FILE"
    sync
}

# Function to log JSON data with proper formatting
log_json_response() {
    local json_data="$1"
    local label="$2"
    
    if [ -n "$label" ]; then
        log_message "${YELLOW}$label:${NC}"
    fi
    
    # Format JSON if jq is available, otherwise just log as-is
    if command -v jq >/dev/null 2>&1; then
        local formatted_json=$(echo "$json_data" | jq . 2>/dev/null || echo "$json_data")
        log_message "$formatted_json"
    else
        log_message "$json_data"
    fi
    
    # Also log raw JSON to file for debugging (but don't mix with console output)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] RAW_JSON: $json_data" >> "$LOG_FILE"
}

print_header() {
    local header_msg="\n${CYAN}${BOLD}================================${NC}\n${CYAN}${BOLD}$1${NC}\n${CYAN}${BOLD}================================${NC}"
    log_message "$header_msg"
}

print_success() {
    log_message "${GREEN}✅ SUCCESS: $1${NC}"
}

print_error() {
    log_message "${RED}❌ ERROR: $1${NC}"
}

print_warning() {
    log_message "${YELLOW}⚠️  WARNING: $1${NC}"
}

print_info() {
    log_message "${PURPLE}ℹ️  INFO: $1${NC}"
}

# Function to check server health
check_server_health() {
    log_message "${BLUE}Checking server health...${NC}"
    local health_response=$(curl -s -X GET "$SERVER_URL/health" --connect-timeout $TIMEOUT --max-time $TIMEOUT 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_message "${GREEN}✅ Server is healthy${NC}"
        return 0
    else
        print_error "Server health check failed: $health_response"
        return 1
    fi
}

# Function to verify journeys tool is available
check_journeys_tool() {
    log_message "${BLUE}Checking if journeys tool is available...${NC}"
    local tools_response=$(curl -s -X GET "$SERVER_URL/tools" \
        -H "x-api-key: $API_KEY" \
        --connect-timeout $TIMEOUT --max-time $TIMEOUT 2>&1)
    
    if [[ $? -eq 0 ]]; then
        local journeys_available=$(echo "$tools_response" | jq -r '.tools[] | select(.name == "journeys_tool") | .name' 2>/dev/null)
        if [[ "$journeys_available" == "journeys_tool" ]]; then
            log_message "${GREEN}✅ Journeys tool is available${NC}"
            return 0
        else
            print_error "Journeys tool not found in server tools"
            return 1
        fi
    else
        print_error "Failed to get tools list: $tools_response"
        return 1
    fi
}

# Function to get all journeys (including comprehensive data)
get_all_journeys() {
    log_message "${BLUE}Retrieving all journeys from system...${NC}"
    
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d '{"arguments": {"action": "list"}}' \
        --connect-timeout $TIMEOUT \
        --max-time $TIMEOUT 2>&1)
    
    if [[ $? -eq 0 ]]; then
        # Log to file only to avoid contamination
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] LIST_RESPONSE: $response" >> "$LOG_FILE"
        
        # Extract MCP wrapped response (.content[0].text) and parse inner JSON
        local inner_response=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
        if [[ -z "$inner_response" ]]; then
            # Fallback to direct response if not MCP format
            inner_response="$response"
        fi
        
        local status=$(echo "$inner_response" | jq -r '.status // "unknown"' 2>/dev/null)
        if [[ "$status" == "success" ]]; then
            # Extract journey IDs from inner response - journeys are in 'data' field
            local journey_ids=$(echo "$inner_response" | jq -r '.data[]?.journeyId // .data[]?.journey_id // .journeys[]?.journeyId // .journeys[]?.journey_id // empty' 2>/dev/null)
            
            # Clean journey IDs - remove any whitespace and ensure they start with JRN-
            local clean_journey_ids=""
            while IFS= read -r journey_id; do
                # Trim whitespace and validate format
                journey_id=$(echo "$journey_id" | tr -d '\n\r\t ' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                if [[ -n "$journey_id" ]] && [[ "$journey_id" =~ ^JRN- ]]; then
                    if [[ -n "$clean_journey_ids" ]]; then
                        clean_journey_ids="$clean_journey_ids\n$journey_id"
                    else
                        clean_journey_ids="$journey_id"
                    fi
                fi
            done <<< "$journey_ids"
            
            if [[ -n "$clean_journey_ids" ]]; then
                log_message "${GREEN}✅ Found journeys in system${NC}"
                echo -e "$clean_journey_ids"
                return 0
            else
                log_message "${YELLOW}⚠️  No journeys found in system${NC}"
                return 1
            fi
        else
            local error_msg=$(echo "$inner_response" | jq -r '.message // "Unknown error"' 2>/dev/null)
            print_error "Failed to list journeys: $error_msg"
            return 1
        fi
    else
        print_error "Failed to connect to server: $response"
        return 1
    fi
}

# Function to delete a single journey
delete_journey() {
    local journey_id="$1"
    log_message "${BLUE}Deleting journey: $journey_id${NC}"
    
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d "{\"arguments\": {\"action\": \"delete\", \"journey_id\": \"$journey_id\", \"confirm\": true}}" \
        --connect-timeout $TIMEOUT \
        --max-time $TIMEOUT 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_json_response "$response" "Delete Response for $journey_id"
        
        # Extract MCP wrapped response (.content[0].text) and parse inner JSON
        local inner_response=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
        if [[ -z "$inner_response" ]]; then
            inner_response="$response"
        fi
        
        local status=$(echo "$inner_response" | jq -r '.status // "unknown"' 2>/dev/null)
        if [[ "$status" == "success" ]]; then
            print_success "Deleted journey: $journey_id"
            DELETED_JOURNEYS=$((DELETED_JOURNEYS + 1))
            return 0
        else
            local error_msg=$(echo "$inner_response" | jq -r '.message // .error // "Unknown error"' 2>/dev/null)
            # Also log the full response for debugging
            echo "[DEBUG] Full delete response: $inner_response" >> "$LOG_FILE"
            print_error "Failed to delete journey $journey_id: $error_msg"
            FAILED_DELETIONS=$((FAILED_DELETIONS + 1))
            return 1
        fi
    else
        print_error "Failed to connect to server for journey $journey_id: $response"
        FAILED_DELETIONS=$((FAILED_DELETIONS + 1))
        return 1
    fi
}

# Function to display journey summary
display_journey_summary() {
    local journey_ids="$1"
    
    log_message "\n${CYAN}${BOLD}JOURNEYS TO BE DELETED:${NC}"
    log_message "${CYAN}========================${NC}"
    
    local count=0
    while IFS= read -r journey_id; do
        if [[ -n "$journey_id" ]]; then
            count=$((count + 1))
            log_message "${YELLOW}$count. $journey_id${NC}"
        fi
    done <<< "$journey_ids"
    
    TOTAL_JOURNEYS=$count
    log_message "${CYAN}========================${NC}"
    log_message "${BOLD}Total journeys to delete: $TOTAL_JOURNEYS${NC}"
}

# Function to ask for confirmation
ask_confirmation() {
    if [[ "$FORCE_MODE" == "true" ]]; then
        log_message "${YELLOW}Force mode enabled - skipping confirmation${NC}"
        return 0
    fi
    
    echo >&2
    echo -e "${RED}${BOLD}⚠️  WARNING: This will permanently delete ALL journey data!${NC}" >&2
    echo -e "${RED}This operation cannot be undone!${NC}" >&2
    echo >&2
    echo -e "${YELLOW}This includes:${NC}" >&2
    echo -e "${YELLOW}- All journey metadata${NC}" >&2
    echo -e "${YELLOW}- All associated stages${NC}" >&2
    echo -e "${YELLOW}- All related DynamoDB records${NC}" >&2
    echo >&2
    echo -n "Are you sure you want to proceed? (type 'DELETE ALL' to confirm): " >&2
    read confirmation
    
    if [[ "$confirmation" == "DELETE ALL" ]]; then
        log_message "${GREEN}✅ User confirmed deletion${NC}"
        return 0
    else
        log_message "${YELLOW}❌ Operation cancelled by user${NC}"
        return 1
    fi
}

# Function to perform comprehensive cleanup (all data at once)
perform_comprehensive_cleanup() {
    log_message "${BLUE}Performing comprehensive cleanup of ALL journey data...${NC}"
    
    # Use longer timeout for comprehensive cleanup (5 minutes)
    local CLEANUP_TIMEOUT=300
    
    local response=$(curl -s -X POST "$SERVER_URL/tools/journeys_tool" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $API_KEY" \
        -d '{"arguments": {"action": "clean_all", "confirm": true}}' \
        --connect-timeout $TIMEOUT \
        --max-time $CLEANUP_TIMEOUT 2>&1)
    
    if [[ $? -eq 0 ]] && [[ -n "$response" ]]; then
        log_json_response "$response" "Comprehensive Cleanup Response"
        
        # Extract MCP wrapped response (.content[0].text) and parse inner JSON
        local inner_response=$(echo "$response" | jq -r '.content[0].text // empty' 2>/dev/null)
        if [[ -z "$inner_response" ]]; then
            inner_response="$response"
        fi
        
        # Debug: log the inner response
        echo "[DEBUG] Inner response: $inner_response" >> "$LOG_FILE"
        
        local status=$(echo "$inner_response" | jq -r '.status // "unknown"' 2>/dev/null)
        if [[ "$status" == "success" ]]; then
            # Try both metadata fields and direct fields
            local cleaned_journeys=$(echo "$inner_response" | jq -r '.metadata.cleaned_journeys // .cleaned_journeys // 0' 2>/dev/null)
            local total_items=$(echo "$inner_response" | jq -r '.metadata.total_items_deleted // .total_items_deleted // 0' 2>/dev/null)
            
            print_success "Comprehensive cleanup completed: $cleaned_journeys journeys, $total_items total items deleted"
            
            # Update counters
            DELETED_JOURNEYS=$cleaned_journeys
            TOTAL_JOURNEYS=$cleaned_journeys
            
            return 0
        else
            local error_msg=$(echo "$inner_response" | jq -r '.message // .error // "Unknown error"' 2>/dev/null)
            print_error "Comprehensive cleanup failed: $error_msg"
            echo "[DEBUG] Full inner response on error: $inner_response" >> "$LOG_FILE"
            return 1
        fi
    else
        print_error "Failed to connect to server or empty response for comprehensive cleanup"
        echo "[DEBUG] Raw response: $response" >> "$LOG_FILE"
        return 1
    fi
}

# Function to perform cleanup verification
verify_cleanup() {
    log_message "${BLUE}Verifying cleanup was successful...${NC}"
    
    local remaining_journeys=$(get_all_journeys 2>/dev/null)
    if [[ $? -eq 1 ]] || [[ -z "$remaining_journeys" ]]; then
        print_success "✅ All journeys successfully removed from system"
        return 0
    else
        print_warning "⚠️  Some journeys may still remain in system:"
        echo "$remaining_journeys" | head -5 >&2
        return 1
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

# Initialize logging with our enhanced system
log_info "Starting Journey Data Cleanup"
log_info "Execution ID: $EXECUTION_ID"
log_info "Server URL: $SERVER_URL"
log_info "Force mode: $FORCE_MODE"

print_header "TMF ODA TRANSFORMER - JOURNEY DATA CLEANUP"

log_message "${PURPLE}📋 Cleanup log will be saved to: $LOG_FILE${NC}"
log_message "${PURPLE}🔗 Server URL: $SERVER_URL${NC}"
log_message "${PURPLE}⚡ Force mode: $FORCE_MODE${NC}"

# Step 1: Check server health
print_header "HEALTH CHECKS"
if ! check_server_health; then
    print_error "Cannot proceed - server is not healthy"
    exit 1
fi

# Step 2: Verify journeys tool is available
if ! check_journeys_tool; then
    print_error "Cannot proceed - journeys tool is not available"
    exit 1
fi

# Step 3: Get all journeys
print_header "DISCOVERY PHASE"
journey_ids=$(get_all_journeys)
if [[ $? -ne 0 ]]; then
    print_info "No journeys found to delete"
    log_message "\n${GREEN}✨ System is already clean!${NC}"
    log_message "${PURPLE}📋 Cleanup log saved to: $LOG_FILE${NC}"
    exit 0
fi

# Step 4: Display summary
display_journey_summary "$journey_ids"

# Step 5: Ask for confirmation
print_header "CONFIRMATION"
if ! ask_confirmation; then
    print_info "Cleanup operation cancelled"
    log_message "${PURPLE}📋 Cleanup log saved to: $LOG_FILE${NC}"
    exit 0
fi

# Step 6: Perform deletions
print_header "DELETION PHASE"

# Offer comprehensive cleanup vs individual deletion
if [[ $TOTAL_JOURNEYS -gt 10 ]] && [[ "$FORCE_MODE" != "true" ]]; then
    echo >&2
    echo -e "${YELLOW}Two cleanup options available:${NC}" >&2
    echo -e "${YELLOW}1. Comprehensive cleanup (faster, single operation)${NC}" >&2
    echo -e "${YELLOW}2. Individual deletion (slower, journey by journey)${NC}" >&2
    echo >&2
    echo -n "Choose option (1 or 2): " >&2
    read cleanup_option
    
    if [[ "$cleanup_option" == "1" ]]; then
        log_message "${GREEN}Using comprehensive cleanup method${NC}"
        if perform_comprehensive_cleanup; then
            log_message "${GREEN}🎉 Comprehensive cleanup completed successfully!${NC}"
        else
            log_message "${RED}❌ Comprehensive cleanup failed, falling back to individual deletion${NC}"
            cleanup_option="2"
        fi
    else
        cleanup_option="2"
    fi
else
    # Auto-choose based on count or force mode
    if [[ $TOTAL_JOURNEYS -gt 10 ]]; then
        log_message "${BLUE}Auto-selecting comprehensive cleanup for ${TOTAL_JOURNEYS} journeys${NC}"
        cleanup_option="1"
        if perform_comprehensive_cleanup; then
            log_message "${GREEN}🎉 Comprehensive cleanup completed successfully!${NC}"
        else
            log_message "${RED}❌ Comprehensive cleanup failed, falling back to individual deletion${NC}"
            cleanup_option="2"
        fi
    else
        cleanup_option="2"
    fi
fi

# Individual deletion if needed
if [[ "$cleanup_option" == "2" ]]; then
    log_message "${RED}${BOLD}🔥 Starting individual deletion of $TOTAL_JOURNEYS journeys...${NC}"
    
    while IFS= read -r journey_id; do
        if [[ -n "$journey_id" ]]; then
            delete_journey "$journey_id"
            
            # Brief pause to avoid overwhelming the server
            sleep 0.1
        fi
    done <<< "$journey_ids"
fi

# Step 7: Verification
print_header "VERIFICATION PHASE"
verify_cleanup

# Step 8: Final summary
print_header "CLEANUP SUMMARY"

log_message "\n${BLUE}${BOLD}Cleanup Results:${NC}"
log_message "${GREEN}✅ Successfully deleted: $DELETED_JOURNEYS journeys${NC}"
log_message "${RED}❌ Failed deletions: $FAILED_DELETIONS journeys${NC}"
log_message "${YELLOW}📊 Total processed: $TOTAL_JOURNEYS journeys${NC}"

# Calculate success rate
if [[ $TOTAL_JOURNEYS -gt 0 ]]; then
    success_rate=$(( (DELETED_JOURNEYS * 100) / TOTAL_JOURNEYS ))
    log_message "${CYAN}📈 Success rate: $success_rate%${NC}"
fi

# Add final summary to log file
echo "" >> "$LOG_FILE"
echo "=============================================" >> "$LOG_FILE"
echo "Cleanup completed at $(date)" >> "$LOG_FILE"
echo "Final Results:" >> "$LOG_FILE"
echo "- Total journeys: $TOTAL_JOURNEYS" >> "$LOG_FILE"
echo "- Successfully deleted: $DELETED_JOURNEYS" >> "$LOG_FILE"
echo "- Failed deletions: $FAILED_DELETIONS" >> "$LOG_FILE"
echo "=============================================" >> "$LOG_FILE"

# Exit with appropriate code
if [[ $FAILED_DELETIONS -eq 0 ]]; then
    log_message "\n${GREEN}🎉 Cleanup completed successfully!${NC}"
    log_message "${BLUE}✨ All journey data has been removed from the system${NC}"
    log_message "${PURPLE}📋 Full cleanup log saved to: $LOG_FILE${NC}"
    
    # Enhanced logging
    log_success "Journey Data Cleanup Completed Successfully"
    log_info "Total journeys deleted: $DELETED_JOURNEYS"
    log_info "Success rate: $(( (DELETED_JOURNEYS * 100) / TOTAL_JOURNEYS ))%"
    log_info "Cleanup execution completed at: $(date)"
    
    echo ""
    echo -e "${CYAN}📋 Detailed logs saved to: $LOG_FILE${NC}"
    exit 0
else
    log_message "\n${YELLOW}⚠️  Cleanup completed with some failures${NC}"
    log_message "${BLUE}📋 Check the log above for details about failed deletions${NC}"
    log_message "${PURPLE}📋 Full cleanup log saved to: $LOG_FILE${NC}"
    
    # Enhanced logging
    log_warning "Journey Data Cleanup Completed With Failures"
    log_info "Total journeys processed: $TOTAL_JOURNEYS"
    log_info "Successfully deleted: $DELETED_JOURNEYS"
    log_error "Failed deletions: $FAILED_DELETIONS"
    log_info "Cleanup execution completed at: $(date)"
    
    echo ""
    echo -e "${CYAN}📋 Detailed logs saved to: $LOG_FILE${NC}"
    exit 1
fi 