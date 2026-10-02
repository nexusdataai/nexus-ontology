#!/bin/bash

#==============================================================================
# Job Execution Integration Test
#==============================================================================
# Tests the run_job action functionality in the journey tool
# which allows execution of transformation jobs via MCP protocol
#==============================================================================

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common test utilities
source "$SCRIPT_DIR/../common/test_utils.sh"

# Test configuration
TEST_NAME="run_job_action"
TEST_JOURNEY_NAME="Job Execution Test Journey $(date +%s)"
TEST_JOURNEY_COMPONENT="product-management"

# Test data tracking
CREATED_JOURNEY_ID=""
AVAILABLE_STAGES=()
TEST_CLEANUP_NEEDED=false

#==============================================================================
# Helper Functions
#==============================================================================

# Get available stages for a journey
get_journey_stages() {
    local journey_id="$1"
    
    local list_payload=$(cat <<EOF
{
    "action": "list_stages",
    "journey_id": "$journey_id"
}
EOF
    )
    
    local response=$(make_post_request "/tools/journeys_tool" "$list_payload")
    local stages=$(get_json_field "$response" '.data[]?.stageId')
    
    if [ -z "$stages" ] || [ "$stages" = "null" ]; then
        echo "raw_analysis"
    else
        echo "$stages"
    fi
}

#==============================================================================
# Test Functions
#==============================================================================

test_create_journey_for_jobs() {
    start_test "Create Journey for Job Testing"
    
    local create_payload=$(cat <<EOF
{
    "action": "create",
    "name": "$TEST_JOURNEY_NAME",
    "description": "Automated test journey for job execution testing",
    "odaComponentType": "$TEST_JOURNEY_COMPONENT"
}
EOF
    )
    
    log_step "Creating journey for job execution testing"
    local response=$(make_post_request "/tools/journeys_tool" "$create_payload")
    
    if ! check_response_success "$response"; then
        local error_msg=$(get_error_message "$response")
        log_error "Failed to create journey: $error_msg"
        end_test "Create Journey for Job Testing" "failed"
        return 1
    fi
    
    CREATED_JOURNEY_ID=$(get_json_field "$response" '.journey_id')
    
    if assert_not_empty "$CREATED_JOURNEY_ID" "Journey ID should not be empty"; then
        log_success "Journey created with ID: $CREATED_JOURNEY_ID"
        TEST_CLEANUP_NEEDED=true
        
        # Get available stages
        local stages=$(get_journey_stages "$CREATED_JOURNEY_ID")
        AVAILABLE_STAGES=($stages)
        log_info "Available stages: ${AVAILABLE_STAGES[*]}"
        
        end_test "Create Journey for Job Testing" "passed"
        return 0
    else
        end_test "Create Journey for Job Testing" "failed"
        return 1
    fi
}

test_run_job_system_trigger() {
    start_test "Run Job with System Trigger"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping test"
        end_test "Run Job with System Trigger" "skipped"
        return 0
    fi
    
    local stage_id="${AVAILABLE_STAGES[0]:-raw_analysis}"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "$stage_id",
    "triggered_by": "system",
    "reason": "Automated integration test execution"
}
EOF
    )
    
    log_step "Running job with system trigger on stage: $stage_id"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if check_response_success "$response"; then
        local job_id=$(get_json_field "$response" '.job_id')
        log_success "Job started successfully"
        if [ -n "$job_id" ] && [ "$job_id" != "null" ]; then
            log_info "Job ID: $job_id"
        fi
        end_test "Run Job with System Trigger" "passed"
        return 0
    else
        local error_msg=$(get_error_message "$response")
        log_error "Failed to run job: $error_msg"
        end_test "Run Job with System Trigger" "failed"
        return 1
    fi
}

test_run_job_user_trigger() {
    start_test "Run Job with User Trigger"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping test"
        end_test "Run Job with User Trigger" "skipped"
        return 0
    fi
    
    local stage_id="${AVAILABLE_STAGES[0]:-raw_analysis}"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "$stage_id",
    "triggered_by": "user",
    "reason": "Manual execution for testing"
}
EOF
    )
    
    log_step "Running job with user trigger"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if check_response_success "$response"; then
        log_success "Job started with user trigger"
        end_test "Run Job with User Trigger" "passed"
        return 0
    else
        local error_msg=$(get_error_message "$response")
        log_error "Failed to run job: $error_msg"
        end_test "Run Job with User Trigger" "failed"
        return 1
    fi
}

test_run_job_api_trigger() {
    start_test "Run Job with API Trigger"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping test"
        end_test "Run Job with API Trigger" "skipped"
        return 0
    fi
    
    local stage_id="${AVAILABLE_STAGES[0]:-raw_analysis}"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "$stage_id",
    "triggered_by": "api",
    "reason": "API triggered execution"
}
EOF
    )
    
    log_step "Running job with API trigger"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if check_response_success "$response"; then
        log_success "Job started with API trigger"
        end_test "Run Job with API Trigger" "passed"
        return 0
    else
        local error_msg=$(get_error_message "$response")
        log_error "Failed to run job: $error_msg"
        end_test "Run Job with API Trigger" "failed"
        return 1
    fi
}

test_run_job_different_stage() {
    start_test "Run Job on Different Stage"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping test"
        end_test "Run Job on Different Stage" "skipped"
        return 0
    fi
    
    if [ ${#AVAILABLE_STAGES[@]} -lt 2 ]; then
        log_warning "Only one stage available, skipping test"
        end_test "Run Job on Different Stage" "skipped"
        return 0
    fi
    
    local stage_id="${AVAILABLE_STAGES[1]}"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "$stage_id",
    "triggered_by": "test",
    "reason": "Testing different stage execution"
}
EOF
    )
    
    log_step "Running job on stage: $stage_id"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if check_response_success "$response"; then
        log_success "Job started on different stage"
        end_test "Run Job on Different Stage" "passed"
        return 0
    else
        local error_msg=$(get_error_message "$response")
        log_error "Failed to run job: $error_msg"
        end_test "Run Job on Different Stage" "failed"
        return 1
    fi
}

test_run_job_invalid_journey() {
    start_test "Run Job with Invalid Journey ID (Error Handling)"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "INVALID-JRN-99999",
    "stage_id": "raw_analysis",
    "triggered_by": "test",
    "reason": "Testing error handling"
}
EOF
    )
    
    log_step "Testing run_job with invalid journey ID"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if ! check_response_success "$response"; then
        log_success "Correctly rejected invalid journey ID"
        end_test "Run Job with Invalid Journey ID (Error Handling)" "passed"
        return 0
    else
        log_error "Should have rejected invalid journey ID"
        end_test "Run Job with Invalid Journey ID (Error Handling)" "failed"
        return 1
    fi
}

test_run_job_invalid_stage() {
    start_test "Run Job with Invalid Stage ID (Error Handling)"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping test"
        end_test "Run Job with Invalid Stage ID (Error Handling)" "skipped"
        return 0
    fi
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "invalid_stage_xyz",
    "triggered_by": "test",
    "reason": "Testing error handling"
}
EOF
    )
    
    log_step "Testing run_job with invalid stage ID"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if ! check_response_success "$response"; then
        log_success "Correctly rejected invalid stage ID"
        end_test "Run Job with Invalid Stage ID (Error Handling)" "passed"
        return 0
    else
        log_error "Should have rejected invalid stage ID"
        end_test "Run Job with Invalid Stage ID (Error Handling)" "failed"
        return 1
    fi
}

test_run_job_empty_journey() {
    start_test "Run Job with Empty Journey ID (Validation)"
    
    local run_job_payload=$(cat <<EOF
{
    "action": "run_job",
    "journey_id": "",
    "stage_id": "raw_analysis",
    "triggered_by": "test",
    "reason": "Testing validation"
}
EOF
    )
    
    log_step "Testing run_job with empty journey ID"
    local response=$(make_post_request "/tools/journeys_tool" "$run_job_payload")
    
    if ! check_response_success "$response"; then
        log_success "Correctly rejected empty journey ID"
        end_test "Run Job with Empty Journey ID (Validation)" "passed"
        return 0
    else
        log_error "Should have rejected empty journey ID"
        end_test "Run Job with Empty Journey ID (Validation)" "failed"
        return 1
    fi
}

#==============================================================================
# Cleanup Function
#==============================================================================

cleanup_test_data() {
    if [ "$TEST_CLEANUP_NEEDED" = "true" ] && [ -n "$CREATED_JOURNEY_ID" ]; then
        log_info "Cleaning up test journey: $CREATED_JOURNEY_ID"
        cleanup_journey "$CREATED_JOURNEY_ID"
    fi
}

#==============================================================================
# Main Execution
#==============================================================================

main() {
    # Parse arguments
    local server_url="${1:-$DEFAULT_URL}"
    
    # Setup test environment
    if ! setup_test_environment "$TEST_NAME" "$server_url"; then
        exit 1
    fi
    
    log_info "Starting Job Execution Tests"
    log_info "Server: $SERVER_URL"
    echo ""
    
    # Run tests in sequence
    test_create_journey_for_jobs
    
    echo ""
    log_info "=== Basic Job Execution Tests ==="
    test_run_job_system_trigger
    test_run_job_user_trigger
    test_run_job_api_trigger
    test_run_job_different_stage
    
    echo ""
    log_info "=== Error Handling Tests ==="
    test_run_job_invalid_journey
    test_run_job_invalid_stage
    test_run_job_empty_journey
    
    # Cleanup
    cleanup_test_data
    TEST_CLEANUP_NEEDED=false
    
    # Generate summary and exit
    cleanup_test_environment
    exit $?
}

# Trap to ensure cleanup on exit
trap cleanup_test_data EXIT

# Run main function
main "$@"


