#!/bin/bash

# stop-gateway.sh - Stop the AI Job Engine MCP HTTP Gateway

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_PORT=${GATEWAY_PORT:-8000}
GATEWAY_SCRIPT="mcp_http_gateway.py"
GATEWAY_PID_FILE=".gateway.pid"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Job Engine Gateway Stop Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Function to find gateway processes
find_gateway_processes() {
    # Find processes running the gateway script
    ps aux | grep -E "python.*${GATEWAY_SCRIPT}" | grep -v grep | awk '{print $2}' || true
    
    # Also check for processes on the gateway port
    lsof -ti :${GATEWAY_PORT} 2>/dev/null || true
}

echo -e "\n${BLUE}Stopping AI Job Engine Gateway...${NC}"

# Check if PID file exists
if [ -f "${GATEWAY_PID_FILE}" ]; then
    PID=$(cat "${GATEWAY_PID_FILE}")
    if kill -0 ${PID} 2>/dev/null; then
        print_info "Found gateway process from PID file: ${PID}"
        kill -TERM ${PID} 2>/dev/null || true
        
        # Wait for graceful shutdown
        WAIT_COUNT=0
        while [ ${WAIT_COUNT} -lt 5 ]; do
            if ! kill -0 ${PID} 2>/dev/null; then
                print_status "Gateway stopped gracefully (PID ${PID})"
                rm -f "${GATEWAY_PID_FILE}"
                break
            fi
            sleep 1
            WAIT_COUNT=$((WAIT_COUNT + 1))
        done
        
        # Force kill if still running
        if kill -0 ${PID} 2>/dev/null; then
            print_warning "Force killing gateway process ${PID}"
            kill -9 ${PID} 2>/dev/null || true
        fi
        rm -f "${GATEWAY_PID_FILE}"
    else
        print_warning "PID file exists but process ${PID} not found"
        rm -f "${GATEWAY_PID_FILE}"
    fi
else
    print_info "No PID file found at ${GATEWAY_PID_FILE}"
fi

# Find all gateway-related processes
GATEWAY_PIDS=$(find_gateway_processes | sort -u)

if [ -n "${GATEWAY_PIDS}" ]; then
    print_warning "Found additional gateway processes: ${GATEWAY_PIDS}"
    
    for pid in ${GATEWAY_PIDS}; do
        if kill -0 ${pid} 2>/dev/null; then
            print_info "Stopping process ${pid}"
            kill -TERM ${pid} 2>/dev/null || true
        fi
    done
    
    sleep 2
    
    # Force kill any remaining
    REMAINING_PIDS=$(find_gateway_processes | sort -u)
    if [ -n "${REMAINING_PIDS}" ]; then
        print_warning "Force killing remaining processes: ${REMAINING_PIDS}"
        for pid in ${REMAINING_PIDS}; do
            kill -9 ${pid} 2>/dev/null || true
        done
    fi
fi

# Clean up any orphaned worker processes
MCP_PIDS=$(ps aux | grep -E "python.*src.server.*--stdio" | grep -v grep | awk '{print $2}' || true)

if [ -n "${MCP_PIDS}" ]; then
    print_warning "Cleaning up MCP worker processes: ${MCP_PIDS}"
    for pid in ${MCP_PIDS}; do
        kill -9 ${pid} 2>/dev/null || true
    done
    print_status "Cleaned up worker processes"
fi

# Verify all processes are stopped
FINAL_CHECK=$(find_gateway_processes | sort -u)

if [ -z "${FINAL_CHECK}" ]; then
    print_status "All gateway processes stopped successfully"
    echo -e "\n${GREEN}Gateway stopped!${NC}"
else
    print_error "Some processes may still be running: ${FINAL_CHECK}"
    echo -e "\n${RED}Gateway may not be fully stopped. Check manually.${NC}"
    exit 1
fi
