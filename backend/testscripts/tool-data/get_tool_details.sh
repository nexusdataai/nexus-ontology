#!/bin/bash

# TMF ODA Transformer MCP Server - Fully Dynamic Tool Details Script
# This script is 100% dynamic - NO hardcoded tool information!

set -e

# Default configuration
DEFAULT_URL="http://localhost:8000"
SERVER_URL="$DEFAULT_URL"
TOOLS_ENDPOINT="$SERVER_URL/tools"

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
    
    TOOLS_ENDPOINT="$SERVER_URL/tools"
}

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${CYAN}${BOLD}TMF ODA Transformer MCP Server - Tool Details Script${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL] [TOOL_NAME]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo -e "  TOOL_NAME              Name of specific tool to get details for (optional)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                    # List all tools on localhost:8000"
    echo -e "  $0 list_journeys                      # Get details for specific tool on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # List all tools on remote server"
    echo -e "  $0 http://example.com:8080 create_journey # Get tool details on remote server"
    echo -e "  $0 https://api.company.com journeys   # Use HTTPS connection"
    echo ""
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help)
                show_usage
                exit 0
                ;;
            http://*|https://*)
                parse_url "$1"
                shift
                ;;
            -*)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format instead: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
            *)
                # This is the tool name
                TOOL_NAME="$1"
                shift
                ;;
        esac
    done
}

print_header() {
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}🔍 $1${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_dependencies() {
    echo -e "${BLUE}🔧 Checking dependencies...${NC}"
    
    if ! command -v jq >/dev/null 2>&1; then
        print_error "jq is required but not installed"
        echo -e "${YELLOW}Install with: sudo apt-get install jq${NC}"
        exit 1
    fi
    
    if ! command -v curl >/dev/null 2>&1; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    print_success "All dependencies available"
}

check_server_health() {
    echo -e "${BLUE}🔍 Checking MCP server health...${NC}"
    
    if curl -s --connect-timeout 3 --max-time 5 "$SERVER_URL" > /dev/null 2>&1; then
        print_success "MCP server is running at $SERVER_URL"
        return 0
    else
        print_error "MCP server is not accessible at $SERVER_URL"
        echo -e "${YELLOW}💡 Start server with: python -m awslabs.tmf_oda_transformer_mcp_server.mcp_http_server${NC}"
        return 1
    fi
}

fetch_tools_from_server() {
    echo -e "${BLUE}📡 Fetching tools dynamically from MCP server...${NC}"
    
    # Get tools with reasonable timeout
    local response=$(curl -s --connect-timeout 5 --max-time 10 "$TOOLS_ENDPOINT" -H "x-api-key: super-secret" 2>/dev/null)
    
    if [ -z "$response" ]; then
        print_error "No response from server"
        return 1
    fi
    
    # Validate JSON
    if ! echo "$response" | jq empty 2>/dev/null; then
        print_error "Invalid JSON response from server"
        echo "Response: ${response:0:200}..."
        return 1
    fi
    
    # Check for tools array
    if ! echo "$response" | jq -e '.tools' > /dev/null 2>&1; then
        print_error "No tools array found in server response"
        echo "Available keys: $(echo "$response" | jq -r 'keys[]' 2>/dev/null | tr '\n' ' ')"
        return 1
    fi
    
    # Store response for processing
    echo "$response" > /tmp/mcp_tool_details.json
    print_success "Successfully fetched tools from server"
    return 0
}

show_dynamic_usage() {
    echo -e "${CYAN}Usage: $0 [tool-name]${NC}"
    echo ""
    
    if [ -f /tmp/mcp_tool_details.json ]; then
        echo -e "${BOLD}Available tools (dynamically discovered):${NC}"
        jq -r '.tools[].name' /tmp/mcp_tool_details.json 2>/dev/null | while read -r tool_name; do
            if [ -n "$tool_name" ]; then
                local description=$(jq -r ".tools[] | select(.name == \"$tool_name\") | .description" /tmp/mcp_tool_details.json 2>/dev/null)
                echo -e "  • ${CYAN}$tool_name${NC} - $description"
            fi
        done
        echo -e "  • ${CYAN}all${NC} - Show details for all discovered tools"
    else
        echo -e "${YELLOW}⚠️ Run without arguments to discover available tools from server${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    if [ -f /tmp/mcp_tool_details.json ]; then
        local first_tool=$(jq -r '.tools[0].name' /tmp/mcp_tool_details.json 2>/dev/null)
        if [ "$first_tool" != "null" ] && [ -n "$first_tool" ]; then
            echo -e "  $0 $first_tool"
        fi
    fi
    echo -e "  $0 all"
}

test_tool_endpoint() {
    local tool_name="$1"
    local endpoint_url="$TOOLS_ENDPOINT/$tool_name"
    
    echo -e "${BLUE}🧪 Testing $tool_name endpoint...${NC}"
    
    # Test with OPTIONS method to check if endpoint exists
    local response=$(timeout 10 curl -s -X OPTIONS "$endpoint_url" \
        --connect-timeout 5 \
        --max-time 10 \
        -w "%{http_code}" \
        2>/dev/null || echo "000")
    
    if [[ "$response" =~ [0-9]{3}$ ]]; then
        local http_code="${response: -3}"
        if [ "$http_code" != "000" ] && [ "$http_code" != "404" ]; then
            print_success "Endpoint is accessible (HTTP $http_code)"
        else
            print_warning "Endpoint not found or not accessible (HTTP $http_code)"
        fi
    else
        print_warning "Unable to test endpoint connectivity"
    fi
    echo ""
}

generate_parameter_details() {
    local tool_name="$1"
    local tool_data="$2"
    
    # Check if tool has input schema
    local has_schema=$(echo "$tool_data" | jq -e '.inputSchema' > /dev/null 2>&1 && echo "true" || echo "false")
    
    if [ "$has_schema" = "false" ]; then
        echo -e "${BOLD}Parameters:${NC}"
        echo -e "  ${YELLOW}⚠️ No parameter schema available${NC}"
        echo -e "  ${CYAN}💡 This tool may accept empty JSON or has simple request format${NC}"
        echo ""
        return 0
    fi
    
    # Extract parameters from schema
    local properties=$(echo "$tool_data" | jq -c '.inputSchema.properties // {}' 2>/dev/null)
    local required_params=$(echo "$tool_data" | jq -r '.inputSchema.required[]? // empty' 2>/dev/null)
    
    if [ "$properties" = "{}" ]; then
        echo -e "${BOLD}Parameters:${NC}"
        echo -e "  ${YELLOW}⚠️ No parameters defined${NC}"
        echo -e "  ${CYAN}💡 This tool accepts empty JSON payload${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${BOLD}Parameters:${NC}"
    
    # Display each parameter
    echo "$properties" | jq -r 'keys[]' 2>/dev/null | while read -r param_name; do
        local param_schema=$(echo "$properties" | jq -c ".$param_name" 2>/dev/null)
        local param_type=$(echo "$param_schema" | jq -r '.type // "string"' 2>/dev/null)
        local param_desc=$(echo "$param_schema" | jq -r '.description // "No description available"' 2>/dev/null)
        local param_default=$(echo "$param_schema" | jq -r '.default // empty' 2>/dev/null)
        local param_enum=$(echo "$param_schema" | jq -r '.enum[]? // empty' 2>/dev/null | tr '\n' ',' | sed 's/,$//')
        
        local is_required="false"
        if echo "$required_params" | grep -q "^$param_name$"; then
            is_required="true"
        fi
        
        local required_indicator=""
        if [ "$is_required" = "true" ]; then
            required_indicator=" ${RED}(required)${NC}"
        else
            required_indicator=" ${YELLOW}(optional)${NC}"
        fi
        
        echo -e "  • ${CYAN}$param_name${NC}$required_indicator: $param_desc"
        
        if [ -n "$param_default" ] && [ "$param_default" != "null" ]; then
            echo -e "    ${CYAN}Default:${NC} $param_default"
        fi
        
        if [ -n "$param_enum" ]; then
            echo -e "    ${CYAN}Valid values:${NC} $param_enum"
        fi
        
        echo -e "    ${CYAN}Type:${NC} $param_type"
        echo ""
    done
}

generate_example_request() {
    local tool_name="$1"
    local tool_data="$2"
    
    echo -e "${BOLD}Example Request:${NC}"
    echo -e "${CYAN}curl -X POST $TOOLS_ENDPOINT/$tool_name \\${NC}"
    echo -e "${CYAN}  -H 'Content-Type: application/json' \\${NC}"
    echo -e "${CYAN}  -H 'x-api-key: super-secret' \\${NC}"
    
    # Check if tool has parameters
    local has_schema=$(echo "$tool_data" | jq -e '.inputSchema.properties' > /dev/null 2>&1 && echo "true" || echo "false")
    
    if [ "$has_schema" = "false" ]; then
        echo -e "${CYAN}  -d '{}'${NC}"
        echo ""
        return 0
    fi
    
    # Generate example JSON
    local properties=$(echo "$tool_data" | jq -c '.inputSchema.properties // {}' 2>/dev/null)
    
    if [ "$properties" = "{}" ]; then
        echo -e "${CYAN}  -d '{}'${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${CYAN}  -d '{${NC}"
    
    local first_param="true"
    echo "$properties" | jq -r 'keys[]' 2>/dev/null | while read -r param_name; do
        local param_schema=$(echo "$properties" | jq -c ".$param_name" 2>/dev/null)
        local param_type=$(echo "$param_schema" | jq -r '.type // "string"' 2>/dev/null)
        local param_default=$(echo "$param_schema" | jq -r '.default // empty' 2>/dev/null)
        local param_enum=$(echo "$param_schema" | jq -r '.enum[0]? // empty' 2>/dev/null)
        
        # Generate example value based on type and context
        local example_value=""
        case "$param_type" in
            "string")
                if [ -n "$param_enum" ]; then
                    example_value="\"$param_enum\""
                elif [ -n "$param_default" ] && [ "$param_default" != "null" ]; then
                    example_value="\"$param_default\""
                else
                    case "$param_name" in
                        *journey_id*|*journey-id*) example_value="\"JRN-SAMPLE-001\"" ;;
                        *job_id*|*job-id*) example_value="\"JOB-12345\"" ;;
                        *stage_id*|*stage-id*) example_value="\"raw_analysis\"" ;;
                        *action*) example_value="\"read\"" ;;
                        *name*) example_value="\"Sample Name\"" ;;
                        *description*) example_value="\"Sample description\"" ;;
                        *) example_value="\"example_value\"" ;;
                    esac
                fi
                ;;
            "boolean")
                example_value="${param_default:-false}"
                ;;
            "integer"|"number")
                example_value="${param_default:-100}"
                ;;
            "object")
                example_value="{}"
                ;;
            "array")
                example_value="[]"
                ;;
            *)
                example_value="\"example_value\""
                ;;
        esac
        
        # Add comma for all but first parameter
        if [ "$first_param" != "true" ]; then
            echo ","
        fi
        echo -n "    \"$param_name\": $example_value"
        first_param="false"
    done
    
    echo ""
    echo -e "${CYAN}  }'${NC}"
    echo ""
}

generate_response_format() {
    local tool_name="$1"
    
    echo -e "${BOLD}Response Format:${NC}"
    echo -e "  ${CYAN}💡 Response format depends on the specific tool implementation${NC}"
    echo -e "  ${CYAN}📋 Common response fields may include:${NC}"
    echo -e "    • ${CYAN}status${NC}: Operation status (success/error)"
    echo -e "    • ${CYAN}message${NC}: Status or result message"
    echo -e "    • ${CYAN}data${NC}: Tool-specific response data"
    echo -e "    • ${CYAN}timestamp${NC}: Operation timestamp"
    echo ""
}

show_dynamic_tool_details() {
    local tool_name="$1"
    
    if [ ! -f /tmp/mcp_tool_details.json ]; then
        print_error "No tools data available"
        return 1
    fi
    
    # Find tool in server response
    local tool_data=$(jq -c ".tools[] | select(.name == \"$tool_name\")" /tmp/mcp_tool_details.json 2>/dev/null)
    
    if [ -z "$tool_data" ] || [ "$tool_data" = "null" ]; then
        print_error "Tool '$tool_name' not found in server response"
        echo ""
        echo -e "${CYAN}Available tools:${NC}"
        jq -r '.tools[].name' /tmp/mcp_tool_details.json 2>/dev/null | while read -r available_tool; do
            if [ -n "$available_tool" ]; then
                echo -e "  • ${CYAN}$available_tool${NC}"
            fi
        done
        return 1
    fi
    
    # Extract tool information
    local tool_desc=$(echo "$tool_data" | jq -r '.description // "No description available"' 2>/dev/null)
    
    echo -e "${BOLD}🔧 $tool_name Tool${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${BOLD}Description:${NC}"
    echo -e "  $tool_desc"
    echo ""
    echo -e "${BOLD}Endpoint:${NC} ${CYAN}$TOOLS_ENDPOINT/$tool_name${NC}"
    echo ""
    
    # Generate parameter details
    generate_parameter_details "$tool_name" "$tool_data"
    
    # Generate example request
    generate_example_request "$tool_name" "$tool_data"
    
    # Show response format
    generate_response_format "$tool_name"
    
    # Test endpoint
    test_tool_endpoint "$tool_name"
}

show_all_tools_details() {
    if [ ! -f /tmp/mcp_tool_details.json ]; then
        print_error "No tools data available"
        return 1
    fi
    
    local tool_count=$(jq '.tools | length' /tmp/mcp_tool_details.json 2>/dev/null || echo "0")
    
    echo -e "${CYAN}📊 Showing details for all $tool_count discovered tools:${NC}"
    echo ""
    
    jq -r '.tools[].name' /tmp/mcp_tool_details.json 2>/dev/null | while read -r tool_name; do
        if [ -n "$tool_name" ]; then
            show_dynamic_tool_details "$tool_name"
            echo ""
        fi
    done
}

cleanup() {
    rm -f /tmp/mcp_tool_details.json 2>/dev/null || true
}

main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    local tool_name="${TOOL_NAME:-}"
    
    print_header "100% DYNAMIC TOOL DETAILS DISCOVERY"
    
    echo -e "${BLUE}🚀 Fully Dynamic TMF ODA Transformer Tool Details${NC}"
    echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
    echo -e "${BLUE}Started: $(date)${NC}"
    echo -e "${BLUE}Mode: 100% Dynamic (no hardcoded tool data)${NC}"
    echo ""
    
    # Check dependencies
    check_dependencies
    echo ""
    
    # Check server connectivity
    if ! check_server_health; then
        print_error "Cannot proceed without server connection"
        cleanup
        exit 1
    fi
    echo ""
    
    # Fetch tools from server
    if ! fetch_tools_from_server; then
        print_error "Failed to fetch tools from server"
        cleanup
        exit 1
    fi
    echo ""
    
    # Show usage if no tool specified
    if [ -z "$tool_name" ]; then
        print_header "USAGE"
        show_dynamic_usage
        cleanup
        exit 1
    fi
    
    print_header "TOOL DETAILS (EXTRACTED FROM SERVER)"
    
    echo -e "${BLUE}🔍 Tool Details for: ${BOLD}$tool_name${NC}"
    echo -e "${BLUE}All information dynamically extracted from MCP server${NC}"
    echo ""
    
    # Show tool details
    if [ "$tool_name" = "all" ]; then
        show_all_tools_details
    else
        show_dynamic_tool_details "$tool_name"
    fi
    
    if [ "$tool_name" != "all" ]; then
        echo ""
        print_header "ADDITIONAL INFORMATION"
        
        echo -e "${CYAN}📚 Related Scripts:${NC}"
        echo -e "  • ${CYAN}./list_all_tools.sh${NC} - List all available tools"
        echo -e "  • ${CYAN}./show_tool_parameters.sh${NC} - Show parameter details for all tools"
        echo -e "  • ${CYAN}./test_tool_availability.sh${NC} - Test tool accessibility"
        echo ""
        
        echo -e "${YELLOW}💡 Quick Test Command:${NC}"
        echo -e "  ${CYAN}curl -X POST $TOOLS_ENDPOINT/$tool_name -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}'${NC}"
        echo ""
        
        echo -e "${GREEN}✅ All information above was dynamically generated from the MCP server${NC}"
    fi
    
    # Cleanup
    cleanup
}

# Set cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 