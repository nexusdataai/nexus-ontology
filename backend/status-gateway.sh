#!/bin/bash

# status-gateway.sh - Check status of AI Job Engine MCP HTTP Gateway

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_PORT=${GATEWAY_PORT:-8000}
GATEWAY_SCRIPT="mcp_http_gateway.py"
GATEWAY_PID_FILE=".gateway.pid"
GATEWAY_LOG="gateway.log"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AI Job Engine Gateway Status${NC}"
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

# Check PID file
echo -e "\n${CYAN}Process Status:${NC}"
if [ -f "${GATEWAY_PID_FILE}" ]; then
    PID=$(cat "${GATEWAY_PID_FILE}")
    if kill -0 ${PID} 2>/dev/null; then
        print_status "Gateway is running (PID: ${PID})"
        
        # Get process details
        PS_INFO=$(ps -p ${PID} -o pid,vsz,rss,pcpu,pmem,etime,comm --no-headers 2>/dev/null)
        if [ -n "${PS_INFO}" ]; then
            echo "  Process details:"
            echo "    PID    VSZ(KB)  RSS(KB)  %CPU  %MEM  ELAPSED"
            echo "    ${PS_INFO}"
        fi
    else
        print_error "PID file exists but process ${PID} is not running"
    fi
else
    print_warning "No PID file found"
fi

# Check if any gateway processes are running
GATEWAY_PIDS=$(ps aux | grep -E "python.*${GATEWAY_SCRIPT}" | grep -v grep | awk '{print $2}' || true)
if [ -n "${GATEWAY_PIDS}" ]; then
    echo -e "\n${CYAN}All Gateway Processes:${NC}"
    for pid in ${GATEWAY_PIDS}; do
        echo "  PID ${pid}: $(ps -p ${pid} -o comm= 2>/dev/null || echo 'unknown')"
    done
fi

# Check port
echo -e "\n${CYAN}Port Status:${NC}"
if lsof -i :${GATEWAY_PORT} >/dev/null 2>&1; then
    print_status "Port ${GATEWAY_PORT} is in use"
    echo "  Processes using port ${GATEWAY_PORT}:"
    lsof -i :${GATEWAY_PORT} | grep LISTEN | head -5 | awk '{printf "    PID %-8s %s\n", $2, $1}'
else
    print_warning "Port ${GATEWAY_PORT} is not in use"
fi

# Check health endpoint
echo -e "\n${CYAN}Health Check:${NC}"
HEALTH_RESPONSE=$(curl -s -f http://localhost:${GATEWAY_PORT}/health 2>/dev/null)
if [ $? -eq 0 ]; then
    print_status "Gateway is responding to health checks"
    
    # Parse health response
    HEALTH_STATUS=$(echo "${HEALTH_RESPONSE}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Status: {data.get('status', 'unknown')}\"
    workers = data.get('workers', {})
    if workers:
        print(f\"  Workers: {workers.get('total_workers', 0)} total, {workers.get('busy_workers', 0)} busy\"
        print(f\"  Requests: {workers.get('total_requests', 0)} total, {workers.get('total_errors', 0)} errors\"
except:
    pass
" 2>/dev/null)
    
    if [ -n "${HEALTH_STATUS}" ]; then
        echo "${HEALTH_STATUS}"
    fi
else
    print_error "Gateway is not responding to health checks"
fi

# Check gateway info
echo -e "\n${CYAN}Gateway Information:${NC}"
GATEWAY_INFO=$(curl -s -f http://localhost:${GATEWAY_PORT}/ 2>/dev/null)
if [ $? -eq 0 ]; then
    INFO_PARSED=$(echo "${GATEWAY_INFO}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Service: {data.get('service', 'Unknown')}\"
    print(f\"  Version: {data.get('version', 'Unknown')}\"
    print(f\"  Protocols: {', '.join(data.get('protocol', [])) if isinstance(data.get('protocol'), list) else data.get('protocol', 'Unknown')}\"
    print(f\"  Transport: {', '.join(data.get('transport', []))}\"
    print(f\"  Streaming: {data.get('streaming', False)}\"
    print(f\"  APIs Enabled: {data.get('apis_enabled', False)}\"
    
    workers = data.get('workers', {})
    if workers:
        print(f\"\\n  Worker Pool:\"
        print(f\"    Total Workers: {workers.get('total_workers', 0)}\"
        print(f\"    Busy Workers: {workers.get('busy_workers', 0)}\"
        print(f\"    Total Requests: {workers.get('total_requests', 0)}\"
        print(f\"    Total Errors: {workers.get('total_errors', 0)}\"
        
        details = workers.get('worker_details', [])
        if details:
            print(f\"\\n  Worker Details:\"
            for w in details:
                busy_status = '(busy)' if w.get('busy') else '(idle)'
                print(f\"    Worker {w.get('id', '?')} {busy_status}: {w.get('requests', 0)} requests, {w.get('errors', 0)} errors\"
except Exception as e:
    print(f\"  Error parsing response: {e}\"
" 2>/dev/null)
    
    if [ -n "${INFO_PARSED}" ]; then
        echo "${INFO_PARSED}"
    else
        print_warning "Could not parse gateway information"
    fi
else
    print_warning "Gateway info endpoint not accessible"
fi

# Check MCP workers
echo -e "\n${CYAN}MCP Workers:${NC}"
MCP_PIDS=$(ps aux | grep -E "python.*src.server.*--stdio" | grep -v grep | awk '{print $2}' || true)
if [ -n "${MCP_PIDS}" ]; then
    WORKER_COUNT=$(echo "${MCP_PIDS}" | wc -l)
    print_status "Found ${WORKER_COUNT} MCP worker process(es)"
    for pid in ${MCP_PIDS}; do
        echo "  Worker PID ${pid}"
    done
else
    print_warning "No MCP worker processes found"
fi

# Check log file
echo -e "\n${CYAN}Log File:${NC}"
if [ -f "${GATEWAY_LOG}" ]; then
    LOG_SIZE=$(du -h "${GATEWAY_LOG}" | cut -f1)
    LOG_LINES=$(wc -l < "${GATEWAY_LOG}")
    print_info "Log file: ${GATEWAY_LOG} (${LOG_SIZE}, ${LOG_LINES} lines)"
    
    # Check for recent errors
    RECENT_ERRORS=$(tail -100 "${GATEWAY_LOG}" | grep -i "error" | wc -l)
    if [ ${RECENT_ERRORS} -gt 0 ]; then
        print_warning "Found ${RECENT_ERRORS} error(s) in last 100 log lines"
        echo "  Recent errors:"
        tail -100 "${GATEWAY_LOG}" | grep -i "error" | tail -3 | while read line; do
            echo "    $(echo "$line" | cut -c1-80)..."
        done
    fi
else
    print_warning "Log file not found at ${GATEWAY_LOG}"
fi

# Summary
echo -e "\n${BLUE}========================================${NC}"
if curl -s -f http://localhost:${GATEWAY_PORT}/health >/dev/null 2>&1; then
    echo -e "${GREEN}Gateway Status: RUNNING${NC}"
    echo -e "${BLUE}Gateway URL:${NC} http://localhost:${GATEWAY_PORT}"
    echo -e "${BLUE}Health Check:${NC} http://localhost:${GATEWAY_PORT}/health"
    echo -e "${BLUE}Documentation:${NC} http://localhost:${GATEWAY_PORT}/docs"
    echo -e "${BLUE}Tools List:${NC} curl -H \"X-API-Key: super-secret\" http://localhost:${GATEWAY_PORT}/tools"
else
    echo -e "${RED}Gateway Status: NOT RUNNING or NOT HEALTHY${NC}"
    echo -e "\n${YELLOW}To start the gateway, run:${NC}"
    echo "  ./start_gateway.sh"
    echo -e "\n${YELLOW}Or to restart:${NC}"
    echo "  ./restart-gateway.sh"
fi
echo -e "${BLUE}========================================${NC}"
