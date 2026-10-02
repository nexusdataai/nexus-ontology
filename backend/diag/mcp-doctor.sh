#!/bin/bash
# MCP Doctor - Quick diagnostics and fixes for MCP issues
# Usage: ./mcp-doctor.sh [quick|full|fix|cleanup|help]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Project root (parent directory since we're in diag/)
DIAG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DIAG_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo -e "${BLUE}🐍 Using virtual environment: .venv${NC}"
elif command -v uv &> /dev/null; then
    echo -e "${BLUE}🐍 Using uv virtual environment${NC}"
    # uv will handle the virtual environment automatically
else
    echo -e "${YELLOW}⚠️ No virtual environment found, using system Python${NC}"
fi

print_header() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                          MCP DOCTOR                          ║"
    echo "║              Diagnose & Fix MCP Issues Quickly              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./mcp-doctor.sh [command]"
    echo ""
    echo -e "${BOLD}Commands:${NC}"
    echo -e "  ${GREEN}quick${NC}    - Quick health check (default)"
    echo -e "  ${GREEN}full${NC}     - Full comprehensive diagnostics"
    echo -e "  ${GREEN}fix${NC}      - Run diagnostics and auto-fix issues"
    echo -e "  ${GREEN}cleanup${NC}  - Kill stuck MCP processes"
    echo -e "  ${GREEN}install${NC}  - Install missing dependencies"
    echo -e "  ${GREEN}test${NC}     - Test MCP tools only"
    echo -e "  ${GREEN}cursor${NC}   - Show what tools Cursor will see"
    echo -e "  ${GREEN}help${NC}     - Show this help"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./mcp-doctor.sh              # Quick check"
    echo "  ./mcp-doctor.sh fix          # Fix common issues"
    echo "  ./mcp-doctor.sh full         # Comprehensive check"
    echo "  ./mcp-doctor.sh cursor       # Show Cursor tool view"
}

check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        return 1
    fi
    
    # Check required Python packages
    local missing_packages=()
    
    if ! python3 -c "import psutil" 2>/dev/null; then
        missing_packages+=("psutil")
    fi
    
    if ! python3 -c "import boto3" 2>/dev/null; then
        missing_packages+=("boto3")
    fi
    
    if ! python3 -c "import loguru" 2>/dev/null; then
        missing_packages+=("loguru")
    fi
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Missing packages: ${missing_packages[*]}${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ All dependencies available${NC}"
    return 0
}

install_dependencies() {
    echo -e "${YELLOW}📦 Installing missing dependencies...${NC}"
    
    # Use uv if available (recommended)
    if command -v uv &> /dev/null; then
        echo -e "${BLUE}Using uv to install dependencies...${NC}"
        uv add psutil boto3 loguru
    # Try pip in virtual environment
    elif [ -f ".venv/bin/pip" ]; then
        echo -e "${BLUE}Using virtual environment pip...${NC}"
        .venv/bin/pip install psutil boto3 loguru
    elif command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}Using system pip3...${NC}"
        pip3 install --user psutil boto3 loguru
    elif command -v pip &> /dev/null; then
        echo -e "${YELLOW}Using system pip...${NC}"
        pip install --user psutil boto3 loguru
    else
        echo -e "${RED}❌ No package manager found, please install manually:${NC}"
        echo "  uv add psutil boto3 loguru"
        echo "  # or"
        echo "  pip install psutil boto3 loguru"
        return 1
    fi
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
}

quick_check() {
    echo -e "${BLUE}🚀 Running quick MCP health check...${NC}"
    
    # Check if MCP server file exists
    if [ ! -f "mcp_stdio_server.py" ]; then
        echo -e "${RED}❌ mcp_stdio_server.py not found${NC}"
        return 1
    fi
    
    # Check if config exists
    if [ ! -f "mcp-config.json" ]; then
        echo -e "${RED}❌ mcp-config.json not found${NC}"
        return 1
    fi
    
    # Check for running processes
    local mcp_processes=$(pgrep -f "mcp_stdio_server.py" | wc -l)
    if [ "$mcp_processes" -gt 0 ]; then
        echo -e "${GREEN}✅ MCP processes running: $mcp_processes${NC}"
    else
        echo -e "${YELLOW}⚠️ No MCP processes found${NC}"
    fi
    
    # Quick stdio test
    echo -e "${BLUE}🔍 Testing MCP communication...${NC}"
    local test_result
    if test_result=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | timeout 10 python3 mcp_stdio_server.py 2>/dev/null | tail -1); then
        if echo "$test_result" | jq -e '.result.tools' &>/dev/null; then
            local tool_count=$(echo "$test_result" | jq '.result.tools | length')
            echo -e "${GREEN}✅ MCP communication working: $tool_count tools found${NC}"
        else
            echo -e "${RED}❌ MCP communication failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ MCP server not responding${NC}"
        return 1
    fi
    
    echo -e "${GREEN}🎉 Quick check passed!${NC}"
}

cleanup_processes() {
    echo -e "${YELLOW}🧹 Cleaning up MCP processes...${NC}"
    
    local killed=0
    for pid in $(pgrep -f "mcp_stdio_server.py"); do
        if kill "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ Killed process: $pid${NC}"
            killed=$((killed + 1))
        fi
    done
    
    if [ "$killed" -eq 0 ]; then
        echo -e "${BLUE}ℹ️ No MCP processes to clean up${NC}"
    else
        echo -e "${GREEN}✅ Cleaned up $killed processes${NC}"
        sleep 2  # Give processes time to die
    fi
}

run_diagnostics() {
    local mode="$1"
    local args=""
    
    case "$mode" in
        "full")
            args="--verbose"
            ;;
        "fix")
            args="--fix --verbose"
            ;;
        "test")
            args="--verbose"
            ;;
        *)
            args=""
            ;;
    esac
    
    echo -e "${BLUE}🔍 Running comprehensive diagnostics...${NC}"
    
    if ! check_dependencies; then
        echo -e "${YELLOW}Installing missing dependencies...${NC}"
        if ! install_dependencies; then
            echo -e "${RED}❌ Failed to install dependencies${NC}"
            return 1
        fi
    fi
    
    python3 "$DIAG_DIR/mcp_diagnostics.py" $args
}

show_cursor_tools() {
    echo -e "${BLUE}📋 Showing what tools Cursor will see...${NC}"
    
    # Get tools list from MCP server
    local tools_response
    if tools_response=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | timeout 10 python3 mcp_stdio_server.py 2>/dev/null | tail -1); then
        if echo "$tools_response" | jq -e '.result.tools' &>/dev/null; then
            local tools=$(echo "$tools_response" | jq -r '.result.tools')
            local tool_count=$(echo "$tools" | jq 'length')
            
            echo -e "${GREEN}✅ Found $tool_count tools available in Cursor:${NC}"
            echo ""
            
            # Show each tool with details
            for i in $(seq 0 $((tool_count - 1))); do
                local tool=$(echo "$tools" | jq ".[$i]")
                local name=$(echo "$tool" | jq -r '.name')
                local desc=$(echo "$tool" | jq -r '.description // "No description"')
                local params=$(echo "$tool" | jq -r '.inputSchema.properties // {} | keys | length')
                
                echo -e "${BOLD}🔧 Tool $((i + 1)): $name${NC}"
                echo -e "   📝 Description: $desc"
                echo -e "   📊 Parameters: $params"
                
                # Show parameter details
                if [ "$params" -gt 0 ]; then
                    echo "   📋 Parameters:"
                    echo "$tool" | jq -r '.inputSchema.properties | to_entries[] | "     • \(.key): \(.value.type // "unknown") \(if .value.description then "- \(.value.description)" else "" end)"'
                fi
                echo ""
            done
            
            # Test a sample call
            echo -e "${BLUE}🧪 Testing sample tool call (browse-products)...${NC}"
            local sample_call='{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "browse-products", "arguments": {"max_results": 3}}}'
            local sample_response
            if sample_response=$(echo "$sample_call" | timeout 15 python3 mcp_stdio_server.py 2>/dev/null | tail -1); then
                if echo "$sample_response" | jq -e '.result' &>/dev/null; then
                    local content=$(echo "$sample_response" | jq -r '.result.content[0].text' 2>/dev/null)
                    if [ "$content" != "null" ] && [ -n "$content" ]; then
                        local product_count=$(echo "$content" | jq -r '.products | length' 2>/dev/null)
                        if [ "$product_count" != "null" ]; then
                            echo -e "${GREEN}✅ Sample call successful: Found $product_count products${NC}"
                        else
                            echo -e "${GREEN}✅ Sample call successful: Got response data${NC}"
                        fi
                    else
                        echo -e "${YELLOW}⚠️ Sample call returned empty response${NC}"
                    fi
                else
                    echo -e "${RED}❌ Sample call failed${NC}"
                fi
            else
                echo -e "${RED}❌ Sample call timed out${NC}"
            fi
            
        else
            echo -e "${RED}❌ Invalid tools response format${NC}"
        fi
    else
        echo -e "${RED}❌ Failed to get tools list from MCP server${NC}"
    fi
}

# Main execution
main() {
    local command="${1:-quick}"
    
    print_header
    
    case "$command" in
        "quick"|"")
            if ! check_dependencies >/dev/null 2>&1; then
                install_dependencies
            fi
            quick_check
            ;;
        "full")
            run_diagnostics "full"
            ;;
        "fix")
            echo -e "${YELLOW}🔧 Running diagnostics with auto-fix...${NC}"
            run_diagnostics "fix"
            ;;
        "cleanup")
            cleanup_processes
            ;;
        "install")
            install_dependencies
            ;;
        "test")
            run_diagnostics "test"
            ;;
        "cursor"|"show")
            show_cursor_tools
            ;;
        "help"|"-h"|"--help")
            print_usage
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $command${NC}"
            echo ""
            print_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
