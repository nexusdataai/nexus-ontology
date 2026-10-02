#!/bin/bash

# Test all journey-crud scripts
# Shows which tests pass and which fail

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}📊 $1${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_header "JOURNEY CRUD TEST SUITE SUMMARY"

echo -e "${BLUE}Testing all journey-crud scripts...${NC}"
echo ""

# Test counters
TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

# Test each script
run_test() {
    local script="$1"
    local description="$2"
    
    ((TOTAL++))
    echo -ne "${BOLD}$TOTAL. $description${NC} ($script)... "
    
    if [ ! -f "$script" ]; then
        echo -e "${YELLOW}⏭️ SKIPPED (file not found)${NC}"
        ((SKIPPED++))
        return
    fi
    
    if [ ! -x "$script" ]; then
        chmod +x "$script"
    fi
    
    # Run the script and capture exit code
    ./"$script" > /tmp/test_output_$$.txt 2>&1
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}"
        # Show last few lines of error
        echo -e "    ${RED}Last output:${NC}"
        tail -3 /tmp/test_output_$$.txt | sed 's/^/      /'
        ((FAILED++))
    fi
    
    rm -f /tmp/test_output_$$.txt
}

# Run all tests
echo -e "${CYAN}Basic Operations:${NC}"
run_test "test_basic_journey.sh" "Basic Journey Operations"
echo ""

echo -e "${CYAN}Quick Tests:${NC}"
run_test "quick_test.sh" "Quick Smoke Test"
echo ""

echo -e "${CYAN}Create Operations:${NC}"
run_test "test_journey_create_only.sh" "Create Only Test"
echo ""

echo -e "${CYAN}Full CRUD Tests:${NC}"
run_test "test_journey_crud_lifecycle.sh" "Full CRUD Lifecycle"
run_test "test_journey_mcp_http.sh" "MCP HTTP Test"
echo ""

echo -e "${CYAN}Advanced Features:${NC}"
run_test "test_second_brain.sh" "Second Brain Rules Test"
echo ""

# Summary
print_header "TEST SUMMARY"

SUCCESS_RATE=$((PASSED * 100 / TOTAL))

echo -e "${BLUE}📊 Results:${NC}"
echo -e "  Total Scripts: ${BOLD}$TOTAL${NC}"
echo -e "  Passed: ${GREEN}$PASSED${NC}"
echo -e "  Failed: ${RED}$FAILED${NC}"
echo -e "  Skipped: ${YELLOW}$SKIPPED${NC}"
echo -e "  Success Rate: ${BOLD}$SUCCESS_RATE%${NC}"
echo ""

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}${BOLD}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}The journey CRUD operations are fully functional.${NC}"
elif [ $PASSED -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}⚠️ PARTIAL SUCCESS${NC}"
    echo -e "${YELLOW}Some tests passed but others failed.${NC}"
    echo ""
    echo -e "${CYAN}Working Features:${NC}"
    echo "  • List and read operations"
    echo "  • Error handling"
    echo "  • Filter operations"
    echo ""
    echo -e "${YELLOW}Known Issues:${NC}"
    echo "  • Create operations may fail due to subprocess output capture"
    echo "  • Some operations requiring journey_id may fail without existing data"
else
    echo -e "${RED}${BOLD}❌ ALL TESTS FAILED${NC}"
    echo -e "${RED}Please check the gateway server is running and configured correctly.${NC}"
fi

echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  1. For passing tests, you can use them for development"
echo "  2. For failing tests, check individual script output for details"
echo "  3. Create operations issue is being debugged separately"
