#!/bin/bash

# Test script to verify MCP stdio server works exactly as Cursor would use it
# This simulates the stdin/stdout communication that Cursor expects

set -e

echo "🔍 Testing MCP Stdio Server for Cursor Compatibility"
echo "=================================================="

PROJECT_DIR="/opt/mycode/promode/promodeagro-mcp"

cd "$PROJECT_DIR"

echo "📍 Working Directory: $(pwd)"
echo ""

# Set environment variables exactly as Cursor would
export PYTHONPATH="$PROJECT_DIR"
export LOG_LEVEL="INFO" 
export AWS_REGION="ap-south-1"

echo "🚀 Starting MCP stdio server with Cursor's exact configuration..."
echo "Command: uv run --project $PROJECT_DIR python mcp_stdio_server.py"
echo ""

# Create a temporary file for server communication
TEMP_INPUT=$(mktemp)
TEMP_OUTPUT=$(mktemp)

# Cleanup function
cleanup() {
    rm -f "$TEMP_INPUT" "$TEMP_OUTPUT"
    kill $SERVER_PID 2>/dev/null || true
}
trap cleanup EXIT

echo "🔧 Testing MCP Initialize (Cursor's first call)..."

# Test 1: Initialize
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "clientInfo": {"name": "cursor", "version": "1.0"}}}' > "$TEMP_INPUT"

INIT_RESPONSE=$(uv run --project "$PROJECT_DIR" python mcp_stdio_server.py < "$TEMP_INPUT" | head -1 2>/dev/null || echo "ERROR")

if echo "$INIT_RESPONSE" | grep -q '"result"'; then
    echo "✅ Initialize: OK"
    echo "   Protocol Version: $(echo "$INIT_RESPONSE" | grep -o '"protocolVersion":"[^"]*"' | cut -d':' -f2 | tr -d '"')"
    echo "   Server Name: $(echo "$INIT_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d':' -f2 | tr -d '"')"
else
    echo "❌ Initialize: FAILED"
    echo "Response: $INIT_RESPONSE"
    exit 1
fi

echo ""
echo "📋 Testing MCP Tools List (Cursor's second call)..."

# Test 2: Tools List
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' > "$TEMP_INPUT"

TOOLS_RESPONSE=$(uv run --project "$PROJECT_DIR" python mcp_stdio_server.py < "$TEMP_INPUT" | head -1 2>/dev/null || echo "ERROR")

if echo "$TOOLS_RESPONSE" | grep -q '"tools"'; then
    echo "✅ Tools list: OK"
    TOOL_COUNT=$(echo "$TOOLS_RESPONSE" | grep -o '"name":"[^"]*"' | wc -l)
    echo "   Tools found: $TOOL_COUNT"
    echo "   Tool names: $(echo "$TOOLS_RESPONSE" | grep -o '"name":"[^"]*"' | cut -d':' -f2 | tr -d '"' | tr '\n' ', ' | sed 's/,$//')"
else
    echo "❌ Tools list: FAILED"
    echo "Response: $TOOLS_RESPONSE"
    exit 1
fi

echo ""
echo "🧪 Testing a tool call (get-category-counts)..."

# Test 3: Tool Call
echo '{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get-category-counts", "arguments": {}}}' > "$TEMP_INPUT"

TOOL_RESPONSE=$(timeout 30s uv run --project "$PROJECT_DIR" python mcp_stdio_server.py < "$TEMP_INPUT" | head -1 2>/dev/null || echo "TIMEOUT")

if echo "$TOOL_RESPONSE" | grep -q '"result"' && echo "$TOOL_RESPONSE" | grep -q '"content"'; then
    echo "✅ Tool call: OK"
    if echo "$TOOL_RESPONSE" | grep -q '"categories"'; then
        echo "   Response contains category data ✅"
    else
        echo "   Response structure looks valid ✅"
    fi
else
    echo "❌ Tool call: FAILED"
    echo "Response: $TOOL_RESPONSE"
fi

echo ""
echo "🎉 MCP Stdio Server Compatibility Test Complete!"
echo ""
echo "If all tests passed ✅, the stdio server is working correctly."
echo "Now restart Cursor IDE and the tools should appear!"
echo ""
echo "Next steps:"
echo "1. ⭐ RESTART CURSOR IDE completely"
echo "2. 🔄 Toggle the MCP server OFF then ON in Cursor settings"
echo "3. 🎯 Try prompts like 'Browse products in vegetables category'"
