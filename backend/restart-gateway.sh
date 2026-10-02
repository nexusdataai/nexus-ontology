#!/bin/bash

# restart-gateway.sh - Restart the AI Job Engine MCP HTTP Gateway
# This script safely stops any existing gateway processes and starts a fresh instance

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
GATEWAY_LOG="gateway.log"
GATEWAY_PID_FILE=".gateway.pid"
MAX_WAIT_TIME=10  # Maximum seconds to wait for shutdown/startup

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Job Engine Gateway Restart Script${NC}"
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

# Function to check if port is in use
check_port() {
    lsof -i :$1 >/dev/null 2>&1
}

# Function to find gateway processes
find_gateway_processes() {
    # Find processes running the gateway script
    ps aux | grep -E "python.*${GATEWAY_SCRIPT}" | grep -v grep | awk '{print $2}' || true
    
    # Also check for processes on the gateway port
    lsof -ti :${GATEWAY_PORT} 2>/dev/null || true
}

# Step 1: Stop existing gateway
echo -e "\n${BLUE}Step 1: Stopping existing gateway...${NC}"

# Check if PID file exists
if [ -f "${GATEWAY_PID_FILE}" ]; then
    OLD_PID=$(cat "${GATEWAY_PID_FILE}")
    if kill -0 ${OLD_PID} 2>/dev/null; then
        print_info "Found gateway process from PID file: ${OLD_PID}"
        kill ${OLD_PID} 2>/dev/null || true
        sleep 1
    fi
    rm -f "${GATEWAY_PID_FILE}"
fi

# Find all gateway-related processes
GATEWAY_PIDS=$(find_gateway_processes | sort -u)

if [ -n "${GATEWAY_PIDS}" ]; then
    print_warning "Found running gateway processes: ${GATEWAY_PIDS}"
    
    # Try graceful shutdown first
    for pid in ${GATEWAY_PIDS}; do
        if kill -0 ${pid} 2>/dev/null; then
            print_info "Sending SIGTERM to process ${pid}"
            kill -TERM ${pid} 2>/dev/null || true
        fi
    done
    
    # Wait for graceful shutdown
    WAIT_COUNT=0
    while [ ${WAIT_COUNT} -lt ${MAX_WAIT_TIME} ]; do
        REMAINING_PIDS=$(find_gateway_processes | sort -u)
        if [ -z "${REMAINING_PIDS}" ]; then
            print_status "All gateway processes stopped gracefully"
            break
        fi
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
        echo -n "."
    done
    echo ""
    
    # Force kill if still running
    REMAINING_PIDS=$(find_gateway_processes | sort -u)
    if [ -n "${REMAINING_PIDS}" ]; then
        print_warning "Force killing remaining processes: ${REMAINING_PIDS}"
        for pid in ${REMAINING_PIDS}; do
            kill -9 ${pid} 2>/dev/null || true
        done
        sleep 1
    fi
else
    print_status "No existing gateway processes found"
fi

# Step 2: Clean up any orphaned worker processes
echo -e "\n${BLUE}Step 2: Cleaning up worker processes...${NC}"

# Find MCP stdio server processes
MCP_PIDS=$(ps aux | grep -E "python.*src.server.*--stdio" | grep -v grep | awk '{print $2}' || true)

if [ -n "${MCP_PIDS}" ]; then
    print_warning "Found orphaned MCP worker processes: ${MCP_PIDS}"
    for pid in ${MCP_PIDS}; do
        kill -9 ${pid} 2>/dev/null || true
    done
    print_status "Cleaned up orphaned workers"
else
    print_status "No orphaned workers found"
fi

# Step 3: Verify port is free
echo -e "\n${BLUE}Step 3: Verifying port ${GATEWAY_PORT} is free...${NC}"

if check_port ${GATEWAY_PORT}; then
    print_error "Port ${GATEWAY_PORT} is still in use!"
    print_info "Processes using port ${GATEWAY_PORT}:"
    lsof -i :${GATEWAY_PORT}
    
    # Try to free the port
    print_warning "Attempting to free port ${GATEWAY_PORT}..."
    lsof -ti :${GATEWAY_PORT} | xargs -r kill -9 2>/dev/null || true
    sleep 2
    
    if check_port ${GATEWAY_PORT}; then
        print_error "Failed to free port ${GATEWAY_PORT}. Please check manually."
        exit 1
    fi
fi

print_status "Port ${GATEWAY_PORT} is free"

# Step 4: Check virtual environment
echo -e "\n${BLUE}Step 4: Checking environment...${NC}"

if [ ! -d ".venv" ]; then
    print_error "Virtual environment not found at .venv"
    print_info "Please create it with: uv venv"
    exit 1
fi

if [ ! -f ".venv/bin/python" ]; then
    print_error "Python not found in virtual environment"
    exit 1
fi

print_status "Virtual environment found"

# Step 5: Backup old log if exists
if [ -f "${GATEWAY_LOG}" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_LOG="logs/gateway_${TIMESTAMP}.log"
    mkdir -p logs
    mv "${GATEWAY_LOG}" "${BACKUP_LOG}"
    print_status "Backed up old log to ${BACKUP_LOG}"
fi

# Step 6: Set environment variables
echo -e "\n${BLUE}Step 6: Setting environment variables...${NC}"

export MIN_WORKERS=${MIN_WORKERS:-2}
export MAX_WORKERS=${MAX_WORKERS:-8}
export MCP_REQUEST_TIMEOUT=${MCP_REQUEST_TIMEOUT:-60.0}
export API_KEY=${API_KEY:-super-secret}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

print_info "MIN_WORKERS: ${MIN_WORKERS}"
print_info "MAX_WORKERS: ${MAX_WORKERS}"
print_info "MCP_REQUEST_TIMEOUT: ${MCP_REQUEST_TIMEOUT}"
print_info "LOG_LEVEL: ${LOG_LEVEL}"

# Step 7: Start the gateway
echo -e "\n${BLUE}Step 7: Starting gateway...${NC}"

# Activate virtual environment and start gateway
source .venv/bin/activate

nohup python ${GATEWAY_SCRIPT} --host 0.0.0.0 --port ${GATEWAY_PORT} > ${GATEWAY_LOG} 2>&1 &
NEW_PID=$!

# Save PID for future reference
echo ${NEW_PID} > ${GATEWAY_PID_FILE}

print_info "Started gateway with PID ${NEW_PID}"

# Step 8: Verify gateway is running
echo -e "\n${BLUE}Step 8: Verifying gateway startup...${NC}"

WAIT_COUNT=0
GATEWAY_READY=false

while [ ${WAIT_COUNT} -lt ${MAX_WAIT_TIME} ]; do
    # Check if process is still running
    if ! kill -0 ${NEW_PID} 2>/dev/null; then
        print_error "Gateway process died unexpectedly"
        print_info "Check ${GATEWAY_LOG} for errors:"
        tail -n 20 ${GATEWAY_LOG}
        exit 1
    fi
    
    # Check if port is listening
    if check_port ${GATEWAY_PORT}; then
        # Try to connect to the health endpoint
        if curl -s -f http://localhost:${GATEWAY_PORT}/health >/dev/null 2>&1; then
            GATEWAY_READY=true
            break
        fi
    fi
    
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done
echo ""

if [ "${GATEWAY_READY}" = true ]; then
    print_status "Gateway is running and healthy!"
    
    # Get gateway status
    echo -e "\n${BLUE}Gateway Status:${NC}"
    GATEWAY_INFO=$(curl -s http://localhost:${GATEWAY_PORT}/ 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Service: {data.get('service', 'Unknown')}\"
print(f\"  Version: {data.get('version', 'Unknown')}\"
print(f\"  Workers: {data.get('workers', {}).get('total_workers', 0)}\"
print(f\"  APIs Enabled: {data.get('apis_enabled', False)}\"
" 2>/dev/null || echo "  Unable to get status")
    
    echo "${GATEWAY_INFO}"
    
    echo -e "\n${GREEN}Gateway successfully restarted!${NC}"
    echo -e "${BLUE}Gateway URL:${NC} http://localhost:${GATEWAY_PORT}"
    echo -e "${BLUE}Health Check:${NC} http://localhost:${GATEWAY_PORT}/health"
    echo -e "${BLUE}Documentation:${NC} http://localhost:${GATEWAY_PORT}/docs"
    echo -e "${BLUE}Log File:${NC} ${GATEWAY_LOG}"
    echo -e "${BLUE}PID File:${NC} ${GATEWAY_PID_FILE}"
    
    # Show how to tail logs
    echo -e "\n${BLUE}To monitor logs:${NC}"
    echo "  tail -f ${GATEWAY_LOG}"
    
    # Show how to stop
    echo -e "\n${BLUE}To stop the gateway:${NC}"
    echo "  kill \$(cat ${GATEWAY_PID_FILE})"
    
else
    print_error "Gateway failed to start properly"
    print_info "Last 20 lines of log:"
    tail -n 20 ${GATEWAY_LOG}
    exit 1
fi
