#!/bin/bash

#==============================================================================
# Basic Journey Operations Integration Test
#==============================================================================
# Tests basic operations: list, filter, read, delete, update with validation
# of both success and error handling scenarios
#==============================================================================

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common test utilities
source "$SCRIPT_DIR/../common/test_utils.sh"

# Test configuration
TEST_NAME="journey_basic_operations"

#==============================================================================
# Test Functions
#==============================================================================

test_list_operations() {
    start_test "List Operations"
    
    log_step "Testing list all journeys"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "list"}')
    
    if check_response_success "$response"; then
        local journey_count=$(get_json_field "$response" '.data | length')
        log_success "List operation successful - Found $journey_count journeys"
        end_test "List Operations" "passed"
        return 0
    else
        log_error "List operation failed"
        end_test "List Operations" "failed"
        return 1
    fi
}

test_filter_operations() {
    start_test "Filter Operations"
    
    log_step "Testing filter by status"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "list", "status_filter": "pending"}')
    
    if ! check_response_success "$response"; then
        log_error "Filter by status failed"
        end_test "Filter Operations" "failed"
        return 1
    fi
    
    log_step "Testing filter by component type"
    response=$(make_post_request "/tools/journeys_tool" '{"action": "list", "component_type_filter": "customer-management"}')
    
    if check_response_success "$response"; then
        log_success "Filter operations successful"
        end_test "Filter Operations" "passed"
        return 0
    else
        log_error "Filter by component type failed"
        end_test "Filter Operations" "failed"
        return 1
    fi
}

test_read_error_handling() {
    start_test "Read Error Handling"
    
    log_step "Testing read non-existent journey"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "read", "journey_id": "NONEXISTENT-123"}')
    
    if check_response_error "$response"; then
        log_success "Correctly handled non-existent journey"
    else
        log_warning "Expected error for non-existent journey"
    fi
    
    log_step "Testing read without journey_id"
    response=$(make_post_request "/tools/journeys_tool" '{"action": "read"}')
    
    if check_response_error "$response"; then
        log_success "Correctly rejected read without journey_id"
        end_test "Read Error Handling" "passed"
        return 0
    else
        log_error "Should have rejected read without journey_id"
        end_test "Read Error Handling" "failed"
        return 1
    fi
}

test_delete_error_handling() {
    start_test "Delete Error Handling"
    
    log_step "Testing delete non-existent journey"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "delete", "journey_id": "NONEXISTENT-456", "confirm": true}')
    
    if check_response_error "$response"; then
        log_success "Correctly handled non-existent journey deletion"
    else
        log_warning "Expected error for non-existent journey deletion"
    fi
    
    log_step "Testing delete without journey_id"
    response=$(make_post_request "/tools/journeys_tool" '{"action": "delete", "confirm": true}')
    
    if check_response_error "$response"; then
        log_success "Correctly rejected delete without journey_id"
        end_test "Delete Error Handling" "passed"
        return 0
    else
        log_error "Should have rejected delete without journey_id"
        end_test "Delete Error Handling" "failed"
        return 1
    fi
}

test_update_error_handling() {
    start_test "Update Error Handling"
    
    log_step "Testing update non-existent journey"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "update", "journey_id": "NONEXISTENT-789"}')
    
    if check_response_error "$response"; then
        log_success "Correctly handled non-existent journey update"
    else
        log_warning "Expected error for non-existent journey update"
    fi
    
    log_step "Testing update without journey_id"
    response=$(make_post_request "/tools/journeys_tool" '{"action": "update"}')
    
    if check_response_error "$response"; then
        log_success "Correctly rejected update without journey_id"
        end_test "Update Error Handling" "passed"
        return 0
    else
        log_error "Should have rejected update without journey_id"
        end_test "Update Error Handling" "failed"
        return 1
    fi
}

test_invalid_actions() {
    start_test "Invalid Action Handling"
    
    log_step "Testing invalid action"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "invalid_action"}')
    
    if ! check_response_error "$response"; then
        log_error "Should have rejected invalid action"
        end_test "Invalid Action Handling" "failed"
        return 1
    fi
    
    log_step "Testing missing action"
    response=$(make_post_request "/tools/journeys_tool" '{}')
    
    if check_response_error "$response"; then
        log_success "Correctly rejected missing action"
        end_test "Invalid Action Handling" "passed"
        return 0
    else
        log_error "Should have rejected missing action"
        end_test "Invalid Action Handling" "failed"
        return 1
    fi
}

test_dashboard_operations() {
    start_test "Dashboard Operations"
    
    log_step "Testing dashboard without journey_id"
    local response=$(make_post_request "/tools/journeys_tool" '{"action": "dashboard"}')
    
    if ! check_response_error "$response"; then
        log_warning "Expected error for dashboard without journey_id"
    fi
    
    log_step "Testing journey summary without journey_id"
    response=$(make_post_request "/tools/journeys_tool" '{"action": "get_journey_summary"}')
    
    if check_response_error "$response"; then
        log_success "Dashboard operations validated correctly"
        end_test "Dashboard Operations" "passed"
        return 0
    else
        log_warning "Expected error for summary without journey_id"
        end_test "Dashboard Operations" "warning"
        return 0
    fi
}

#==============================================================================
# Main Test Execution
#==============================================================================

main() {
    setup_test_environment
    
    print_test_header "Basic Journey Operations Test"
    
    log_info "Testing fundamental journey operations"
    log_info "Server: $MCP_SERVER_URL"
    echo ""
    
    # Run test suites
    local tests_passed=0
    local tests_failed=0
    
    if test_list_operations; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_filter_operations; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_read_error_handling; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_delete_error_handling; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_update_error_handling; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_invalid_actions; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    if test_dashboard_operations; then
        ((tests_passed++))
    else
        ((tests_failed++))
    fi
    
    # Test Summary
    local total_tests=$((tests_passed + tests_failed))
    
    print_test_summary "$tests_passed" "$tests_failed" "$total_tests"
    
    if [ $tests_failed -eq 0 ]; then
        log_success "All basic operations tests passed!"
        exit 0
    else
        log_error "$tests_failed test(s) failed"
        exit 1
    fi
}

# Run main function
main "$@"

