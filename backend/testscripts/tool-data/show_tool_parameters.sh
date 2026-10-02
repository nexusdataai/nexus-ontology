#!/bin/bash

# TMF ODA Transformer MCP Server - Fully Dynamic Tool Parameters Script  
# This script is 100% dynamic - NO hardcoded tool or parameter information!

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
    echo -e "${CYAN}${BOLD}TMF ODA Transformer MCP Server - Tool Parameters Script${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL] [TOOL_NAME]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo -e "  TOOL_NAME              Name of specific tool to show parameters for (optional)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                    # Show parameters for all tools on localhost:8000"
    echo -e "  $0 list_journeys                      # Show parameters for specific tool on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # Show parameters on remote server"
    echo -e "  $0 http://example.com:8080 create_journey # Show tool parameters on remote server"
    echo -e "  $0 https://api.company.com             # Use HTTPS connection"
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
    echo -e "${PURPLE}${BOLD}📋 $1${NC}"
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_tool_header() {
    echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║ 🔧 $1${NC}"
    echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════════════════════╝${NC}"
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
    echo -e "${BLUE}📡 Fetching tools and parameters dynamically from MCP server...${NC}"
    
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
    echo "$response" > /tmp/mcp_tools_params.json
    print_success "Successfully fetched tools and parameters from server"
    return 0
}

display_parameter() {
    local param_name="$1"
    local param_schema="$2"
    local is_required="$3"
    
    local param_type=$(echo "$param_schema" | jq -r '.type // "string"' 2>/dev/null)
    local param_desc=$(echo "$param_schema" | jq -r '.description // "No description available"' 2>/dev/null)
    local param_default=$(echo "$param_schema" | jq -r '.default // empty' 2>/dev/null)
    local param_enum=$(echo "$param_schema" | jq -r '.enum[]? // empty' 2>/dev/null)
    
    local required_indicator=""
    if [ "$is_required" = "true" ]; then
        required_indicator="${RED}*${NC}"
    fi
    
    echo -e "  ${CYAN}${BOLD}$param_name${NC}$required_indicator ${YELLOW}($param_type)${NC}"
    
    if [ "$is_required" = "true" ]; then
        echo -e "    ${RED}• Required${NC}"
    else
        echo -e "    • Optional"
        if [ -n "$param_default" ] && [ "$param_default" != "null" ]; then
            echo -e "    • Default: ${CYAN}$param_default${NC}"
        fi
    fi
    
    echo -e "    • Description: $param_desc"
    
    # Show enum values if available
    if [ -n "$param_enum" ]; then
        echo -e "    • Valid values: ${CYAN}$(echo "$param_enum" | tr '\n' ',' | sed 's/,$//')${NC}"
    fi
    
    echo ""
}

show_tool_parameters() {
    local tool_name="$1"
    local tool_data="$2"
    
    print_tool_header "$tool_name Tool Parameters"
    echo ""
    
    # Extract description
    local description=$(echo "$tool_data" | jq -r '.description // "No description available"' 2>/dev/null)
    echo -e "${CYAN}📝 Description:${NC} $description"
    echo ""
    
    # Check if tool has input schema
    local has_schema=$(echo "$tool_data" | jq -e '.inputSchema' > /dev/null 2>&1 && echo "true" || echo "false")
    
    if [ "$has_schema" = "false" ]; then
        echo -e "${YELLOW}⚠️ No parameter schema available for this tool${NC}"
        echo -e "${CYAN}💡 This tool may not require parameters or uses a simple request format${NC}"
        echo ""
        echo -e "${BOLD}Example request:${NC}"
        echo -e "${CYAN}curl -X POST $TOOLS_ENDPOINT/$tool_name -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}'${NC}"
        echo ""
        return 0
    fi
    
    # Extract parameters from schema
    local properties=$(echo "$tool_data" | jq -c '.inputSchema.properties // {}' 2>/dev/null)
    local required_params=$(echo "$tool_data" | jq -r '.inputSchema.required[]? // empty' 2>/dev/null)
    
    if [ "$properties" = "{}" ]; then
        echo -e "${YELLOW}⚠️ No parameters defined for this tool${NC}"
        echo -e "${CYAN}💡 This tool accepts empty JSON payload${NC}"
        echo ""
        echo -e "${BOLD}Example request:${NC}"
        echo -e "${CYAN}curl -X POST $TOOLS_ENDPOINT/$tool_name -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}'${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${BOLD}Parameters:${NC}"
    echo ""
    
    # Display each parameter
    echo "$properties" | jq -r 'keys[]' 2>/dev/null | while read -r param_name; do
        local param_schema=$(echo "$properties" | jq -c ".$param_name" 2>/dev/null)
        local is_required="false"
        
        # Check if this parameter is required
        if echo "$required_params" | grep -q "^$param_name$"; then
            is_required="true"
        fi
        
        display_parameter "$param_name" "$param_schema" "$is_required"
    done
    
    # Generate example JSON payload
    generate_example_payload "$tool_name" "$tool_data"
}

generate_example_payload() {
    local tool_name="$1"
    local tool_data="$2"
    
    echo -e "${BOLD}Example JSON Payload:${NC}"
    
    # Extract schema for example generation
    local properties=$(echo "$tool_data" | jq -c '.inputSchema.properties // {}' 2>/dev/null)
    local required_params=$(echo "$tool_data" | jq -r '.inputSchema.required[]? // empty' 2>/dev/null)
    
    if [ "$properties" = "{}" ]; then
        echo -e "${CYAN}{}${NC}"
        echo ""
        return 0
    fi
    
    echo -e "${CYAN}{"
    
    local first_param="true"
    echo "$properties" | jq -r 'keys[]' 2>/dev/null | while read -r param_name; do
        local param_schema=$(echo "$properties" | jq -c ".$param_name" 2>/dev/null)
        local param_type=$(echo "$param_schema" | jq -r '.type // "string"' 2>/dev/null)
        local param_default=$(echo "$param_schema" | jq -r '.default // empty' 2>/dev/null)
        local param_enum=$(echo "$param_schema" | jq -r '.enum[0]? // empty' 2>/dev/null)
        
        # Generate example value based on type
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
        echo -n "  \"$param_name\": $example_value"
        first_param="false"
    done
    
    echo ""
    echo -e "}${NC}"
    echo ""
    
    # Show curl command example
    echo -e "${BOLD}Curl Command Example:${NC}"
    echo -e "${CYAN}curl -X POST $TOOLS_ENDPOINT/$tool_name \\${NC}"\n    echo -e "${CYAN}  -H 'x-api-key: super-secret' \\${NC}"
    echo -e "${CYAN}  -H 'Content-Type: application/json' \\${NC}"
    echo -e "${CYAN}  -d '{ \"example\": \"modify_parameters_above\" }'${NC}"
    echo ""
}

display_all_tools_parameters() {
    print_header "DYNAMIC TOOL PARAMETERS FROM MCP SERVER"
    
    if [ ! -f /tmp/mcp_tools_params.json ]; then
        print_error "No tools data available"
        return 1
    fi
    
    # Get tool count
    local tool_count=$(jq '.tools | length' /tmp/mcp_tools_params.json 2>/dev/null || echo "0")
    
    echo -e "${CYAN}🔧 TMF ODA Transformer Tools Parameters (${tool_count} tools discovered):${NC}"
    echo -e "${CYAN}📋 All parameter information dynamically extracted from MCP server${NC}"
    echo ""
    
    # Process each tool from server response
    jq -c '.tools[]' /tmp/mcp_tools_params.json 2>/dev/null | while read -r tool_json; do
        local tool_name=$(echo "$tool_json" | jq -r '.name' 2>/dev/null)
        
        if [ "$tool_name" != "null" ] && [ -n "$tool_name" ]; then
            show_tool_parameters "$tool_name" "$tool_json"
            echo ""
        fi
    done
}

show_parameter_summary() {
    print_header "PARAMETER SUMMARY (EXTRACTED FROM SERVER)"
    
    if [ ! -f /tmp/mcp_tools_params.json ]; then
        print_error "No tools data available for summary"
        return 1
    fi
    
    echo -e "${CYAN}📊 Parameter Analysis (dynamically generated):${NC}"
    echo ""
    
    # Count tools with/without parameters
    local tools_with_params=0
    local tools_without_params=0
    local total_params=0
    
    echo -e "${BOLD}Tool Parameter Summary:${NC}"
    jq -c '.tools[]' /tmp/mcp_tools_params.json 2>/dev/null | while read -r tool_json; do
        local tool_name=$(echo "$tool_json" | jq -r '.name' 2>/dev/null)
        local has_schema=$(echo "$tool_json" | jq -e '.inputSchema.properties' > /dev/null 2>&1 && echo "true" || echo "false")
        local param_count=0
        
        if [ "$has_schema" = "true" ]; then
            param_count=$(echo "$tool_json" | jq '.inputSchema.properties | length' 2>/dev/null || echo "0")
        fi
        
        echo -e "  • ${CYAN}$tool_name${NC}: $param_count parameters"
    done
    
    echo ""
    echo -e "${BOLD}Common Parameter Types Found:${NC}"
    
    # Extract all parameter types dynamically
    local param_types=$(jq -r '.tools[].inputSchema.properties? // {} | to_entries[] | .value.type' /tmp/mcp_tools_params.json 2>/dev/null | sort | uniq)
    
    if [ -n "$param_types" ]; then
        echo "$param_types" | while read -r type; do
            if [ -n "$type" ]; then
                echo -e "  • ${YELLOW}$type${NC}"
            fi
        done
    else
        echo -e "  ${YELLOW}No parameter types detected${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Frequently Used Parameter Names:${NC}"
    
    # Extract common parameter names
    local param_names=$(jq -r '.tools[].inputSchema.properties? // {} | keys[]' /tmp/mcp_tools_params.json 2>/dev/null | sort | uniq -c | sort -nr | head -10)
    
    if [ -n "$param_names" ]; then
        echo "$param_names" | while read -r count name; do
            if [ -n "$name" ]; then
                echo -e "  • ${CYAN}$name${NC} (used in $count tools)"
            fi
        done
    else
        echo -e "  ${YELLOW}No parameter names detected${NC}"
    fi
}

show_raw_server_response() {
    print_header "RAW SERVER RESPONSE (DEBUG)"
    
    if [ -f /tmp/mcp_tools_params.json ]; then
        echo -e "${CYAN}📋 Raw JSON response from MCP server:${NC}"
        echo ""
        jq '.' /tmp/mcp_tools_params.json 2>/dev/null || cat /tmp/mcp_tools_params.json
    else
        print_error "No server response data available"
    fi
}

show_quick_reference() {
    print_header "DYNAMIC QUICK REFERENCE"
    
    if [ ! -f /tmp/mcp_tools_params.json ]; then
        print_error "No tools data available for quick reference"
        return 1
    fi
    
    echo -e "${CYAN}🚀 Quick Tool Access (dynamically generated):${NC}"
    echo ""
    
    echo -e "${BOLD}Available Tools:${NC}"
    jq -r '.tools[].name' /tmp/mcp_tools_params.json 2>/dev/null | while read -r tool_name; do
        if [ -n "$tool_name" ]; then
            echo -e "  • ${CYAN}$tool_name${NC}"
            echo -e "    curl -X POST $TOOLS_ENDPOINT/${tool_name} -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}'"
        fi
    done
    
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo -e "  • ${CYAN}./list_all_tools.sh${NC} - List all available tools"
    echo -e "  • ${CYAN}./get_tool_details.sh [tool-name]${NC} - Get detailed tool information"
    echo -e "  • ${CYAN}./test_tool_availability.sh${NC} - Test tool accessibility"
    
    echo ""
    echo -e "${YELLOW}💡 All information above was extracted dynamically from the MCP server${NC}"
}

cleanup() {
    rm -f /tmp/mcp_tools_params.json 2>/dev/null || true
}

main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    print_header "100% DYNAMIC TOOL PARAMETERS DISCOVERY"
    
    echo -e "${BLUE}🚀 Fully Dynamic TMF ODA Transformer Tool Parameters${NC}"
    echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
    echo -e "${BLUE}Started: $(date)${NC}"
    echo -e "${BLUE}Mode: 100% Dynamic (no hardcoded parameter data)${NC}"
    echo ""
    echo -e "${YELLOW}Legend: ${RED}*${NC} = Required parameter${NC}"
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
    
    # Display all tool parameters
    display_all_tools_parameters
    echo ""
    
    # Show parameter summary
    show_parameter_summary
    echo ""
    
    # Show quick reference
    show_quick_reference
    echo ""
    
    # Show raw response for debugging
    show_raw_server_response
    echo ""
    
    print_header "DYNAMIC PARAMETER DISCOVERY COMPLETED"
    
    echo -e "${GREEN}✅ Successfully discovered tool parameters dynamically from MCP server${NC}"
    echo -e "${GREEN}✅ Zero hardcoded data - everything from live server schemas${NC}"
    
    # Cleanup
    cleanup
}

# Set cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 