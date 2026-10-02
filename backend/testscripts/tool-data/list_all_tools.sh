#!/bin/bash

# TMF ODA Transformer MCP Server - Fully Dynamic Tool Listing Script
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
    echo -e "${CYAN}${BOLD}TMF ODA Transformer MCP Server - Tool Listing Script${NC}"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [URL]"
    echo ""
    echo -e "${YELLOW}Arguments:${NC}"
    echo -e "  URL                    MCP server URL (default: $DEFAULT_URL)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  $0                                    # List all tools on localhost:8000"
    echo -e "  $0 http://192.168.1.100:8000          # List all tools on remote server"
    echo -e "  $0 http://example.com:8080            # List tools on remote server"
    echo -e "  $0 https://api.company.com            # Use HTTPS connection"
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
                echo -e "${RED}❌ Unknown argument: $1${NC}"
                echo -e "${YELLOW}💡 Use URL format: $0 http://host:port${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
}

print_header() {
    echo -e "${PURPLE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}${BOLD}📊 $1${NC}"
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
    echo "$response" > /tmp/mcp_tools.json
    print_success "Successfully fetched tools from server"
    return 0
}

display_tools() {
    print_header "DYNAMIC TOOLS DISCOVERY FROM MCP SERVER"
    
    if [ ! -f /tmp/mcp_tools.json ]; then
        print_error "No tools data available"
        return 1
    fi
    
    # Get tool count directly from server response
    local tool_count=$(jq '.tools | length' /tmp/mcp_tools.json 2>/dev/null || echo "0")
    
    echo -e "${CYAN}🔧 TMF ODA Transformer Tools (${tool_count} tools discovered from server):${NC}"
    echo ""
    
    # Process each tool from server response
    jq -c '.tools[]' /tmp/mcp_tools.json 2>/dev/null | while read -r tool_json; do
        local name=$(echo "$tool_json" | jq -r '.name' 2>/dev/null)
        local description=$(echo "$tool_json" | jq -r '.description' 2>/dev/null)
        
        if [ "$name" != "null" ] && [ -n "$name" ]; then
            echo -e "  • ${CYAN}${BOLD}$name${NC}"
            echo -e "    📝 $description"
            echo -e "    🔗 $TOOLS_ENDPOINT/$name"
            echo ""
        fi
    done
    
    print_success "Displayed $tool_count tools (all from MCP server)"
}

list_tool_names() {
    print_header "TOOL NAMES (EXTRACTED FROM SERVER)"
    
    if [ ! -f /tmp/mcp_tools.json ]; then
        print_error "No tools data available"
        return 1
    fi
    
    echo -e "${CYAN}📋 Tool names (dynamically extracted from MCP server):${NC}"
    echo ""
    
    # Extract tool names from server response
    local tool_names=$(jq -r '.tools[].name' /tmp/mcp_tools.json 2>/dev/null)
    
    if [ -z "$tool_names" ]; then
        print_error "No tool names found in server response"
        return 1
    fi
    
    echo -e "${BOLD}Available Tools:${NC}"
    echo "$tool_names" | while read -r name; do
        if [ -n "$name" ]; then
            echo -e "  • ${CYAN}$name${NC}"
        fi
    done
    
    echo ""
    echo -e "${BOLD}Ready-to-use curl commands:${NC}"
    echo "$tool_names" | while read -r name; do
        if [ -n "$name" ]; then
            echo -e "  curl -X POST $TOOLS_ENDPOINT/${CYAN}$name${NC} -H 'Content-Type: application/json' -H 'x-api-key: super-secret' -d '{}'"
        fi
    done
}

test_tool_endpoints() {
    print_header "DYNAMIC ENDPOINT TESTING"
    
    if [ ! -f /tmp/mcp_tools.json ]; then
        print_error "No tools data available for testing"
        return 1
    fi
    
    echo -e "${BLUE}🧪 Testing endpoints for tools discovered from server...${NC}"
    echo ""
    
    # Test each tool endpoint found in server response
    jq -r '.tools[].name' /tmp/mcp_tools.json 2>/dev/null | while read -r tool_name; do
        if [ -n "$tool_name" ]; then
            echo -ne "  Testing ${tool_name}... "
            
            # Quick endpoint availability test
            if timeout 5 curl -s --connect-timeout 2 --max-time 3 "$TOOLS_ENDPOINT/$tool_name" -H "x-api-key: super-secret" > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Available${NC}"
            else
                echo -e "${YELLOW}❓ Unknown${NC}"
            fi
        fi
    done
    
    echo ""
    print_info "For comprehensive testing, use: ./test_tool_availability.sh"
}

show_server_summary() {
    print_header "SERVER SUMMARY"
    
    echo -e "${CYAN}📊 MCP Server Information:${NC}"
    echo -e "  • Server URL: ${CYAN}$SERVER_URL${NC}"
    echo -e "  • Tools Endpoint: ${CYAN}$TOOLS_ENDPOINT${NC}"
    echo -e "  • Discovery Time: ${CYAN}$(date)${NC}"
    
    if [ -f /tmp/mcp_tools.json ]; then
        local total_tools=$(jq '.tools | length' /tmp/mcp_tools.json 2>/dev/null || echo "0")
        echo -e "  • Tools Discovered: ${CYAN}$total_tools${NC}"
        
        # Show actual tool names found
        echo -e "  • Tool Names: ${CYAN}$(jq -r '.tools[].name' /tmp/mcp_tools.json 2>/dev/null | tr '\n' ' ')${NC}"
    fi
    
    echo ""
    echo -e "${YELLOW}💡 Next Steps:${NC}"
    echo -e "  • ${CYAN}./get_tool_details.sh [tool-name]${NC} - Get detailed info for a specific tool"
    echo -e "  • ${CYAN}./show_tool_parameters.sh${NC} - View all tool parameters"
    echo -e "  • ${CYAN}./test_tool_availability.sh${NC} - Run comprehensive tests"
}

show_raw_server_response() {
    print_header "RAW SERVER RESPONSE (DEBUG)"
    
    if [ -f /tmp/mcp_tools.json ]; then
        echo -e "${CYAN}📋 Raw JSON response from MCP server:${NC}"
        echo ""
        jq '.' /tmp/mcp_tools.json 2>/dev/null || cat /tmp/mcp_tools.json
    else
        print_error "No server response data available"
    fi
}

cleanup() {
    rm -f /tmp/mcp_tools.json 2>/dev/null || true
}

main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    print_header "100% DYNAMIC MCP TOOL DISCOVERY"
    
    echo -e "${BLUE}🚀 Fully Dynamic TMF ODA Transformer Tool Discovery${NC}"
    echo -e "${BLUE}Server URL: $SERVER_URL${NC}"
    echo -e "${BLUE}Started: $(date)${NC}"
    echo -e "${BLUE}Mode: 100% Dynamic (no hardcoded data)${NC}"
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
    
    # Display discovered tools
    display_tools
    echo ""
    
    # List tool names
    list_tool_names
    echo ""
    
    # Test endpoints
    test_tool_endpoints
    echo ""
    
    # Show server summary
    show_server_summary
    echo ""
    
    # Show raw response for debugging
    show_raw_server_response
    echo ""
    
    print_header "DYNAMIC DISCOVERY COMPLETED"
    
    echo -e "${GREEN}✅ Successfully discovered tools dynamically from MCP server${NC}"
    echo -e "${GREEN}✅ Zero hardcoded data - everything from live server${NC}"
    
    # Cleanup
    cleanup
}

# Set cleanup trap
trap cleanup EXIT

# Run main function
main "$@" 