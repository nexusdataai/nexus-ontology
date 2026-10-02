#!/bin/bash

#==============================================================================
# Journey CRUD Lifecycle Integration Test
#==============================================================================
# Tests complete journey lifecycle: Create → Update → Delete
# Verifies all related records are properly managed in DynamoDB
#==============================================================================

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common test utilities
source "$SCRIPT_DIR/../common/test_utils.sh"

# Test configuration
TEST_NAME="journey_crud_lifecycle"
TEST_JOURNEY_NAME="Test Journey CRUD $(date +%s)"
TEST_DESCRIPTION="Comprehensive CRUD test journey with full lifecycle validation"
ODA_COMPONENT_TYPE="product-management"

# Test data tracking
CREATED_JOURNEY_ID=""
INITIAL_DB_COUNT=0
TEST_CLEANUP_NEEDED=false

#==============================================================================
# Test Functions
#==============================================================================

test_create_journey() {
    start_test "Create Journey"
    
    local create_payload=$(cat <<EOF
{
    "action": "create",
    "journey_data": {
        "name": "$TEST_JOURNEY_NAME",
        "description": "$TEST_DESCRIPTION",
        "odaComponentType": "$ODA_COMPONENT_TYPE",
        "stages": [
            {"stageId": "raw_analysis", "name": "Raw Analysis", "order": 1},
            {"stageId": "data_migration", "name": "Data Migration", "order": 2}
        ]
    }
}
EOF
    )
    
    log_step "Creating journey: $TEST_JOURNEY_NAME"
    local response=$(make_post_request "/tools/journeys_tool" "$create_payload")
    
    if ! check_response_success "$response"; then
        local error_msg=$(get_error_message "$response")
        log_error "Failed to create journey: $error_msg"
        end_test "Create Journey" "failed"
        return 1
    fi
    
    CREATED_JOURNEY_ID=$(get_json_field "$response" '.journey_id')
    
    if assert_not_empty "$CREATED_JOURNEY_ID" "Journey ID should not be empty"; then
        log_success "Journey created with ID: $CREATED_JOURNEY_ID"
        TEST_CLEANUP_NEEDED=true
        
        # Verify in DynamoDB
        sleep 1  # Allow time for DynamoDB write
        if journey_exists_in_dynamodb "$CREATED_JOURNEY_ID"; then
            log_success "Journey verified in DynamoDB"
            end_test "Create Journey" "passed"
            return 0
        else
            log_error "Journey not found in DynamoDB"
            end_test "Create Journey" "failed"
            return 1
        fi
    else
        end_test "Create Journey" "failed"
        return 1
    fi
}

test_read_journey() {
    start_test "Read Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping read test"
        end_test "Read Journey" "skipped"
        return 0
    fi
    
    local read_payload=$(cat <<EOF
{
    "action": "read",
    "journey_id": "$CREATED_JOURNEY_ID"
}
EOF
    )
    
    log_step "Reading journey: $CREATED_JOURNEY_ID"
    local response=$(make_post_request "/tools/journeys_tool" "$read_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to read journey"
        end_test "Read Journey" "failed"
        return 1
    fi
    
    local journey_name=$(get_json_field "$response" '.data.metadata.name')
    local journey_status=$(get_json_field "$response" '.data.metadata.status')
    
    if assert_equal "$journey_name" "$TEST_JOURNEY_NAME" "Journey name should match"; then
        log_success "Journey data retrieved successfully"
        log_info "  Name: $journey_name"
        log_info "  Status: $journey_status"
        end_test "Read Journey" "passed"
        return 0
    else
        end_test "Read Journey" "failed"
        return 1
    fi
}

test_update_journey() {
    start_test "Update Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping update test"
        end_test "Update Journey" "skipped"
        return 0
    fi
    
    local updated_description="Updated test description $(date +%s)"
    local update_payload=$(cat <<EOF
{
    "action": "update",
    "journey_id": "$CREATED_JOURNEY_ID",
    "journey_data": {
        "status": "running",
        "priority": "critical",
        "description": "$updated_description"
    }
}
EOF
    )
    
    log_step "Updating journey status and priority"
    local response=$(make_post_request "/tools/journeys_tool" "$update_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to update journey"
        end_test "Update Journey" "failed"
        return 1
    fi
    
    # Verify update by reading again
    local read_payload=$(cat <<EOF
{
    "action": "read",
    "journey_id": "$CREATED_JOURNEY_ID"
}
EOF
    )
    
    sleep 1  # Allow time for DynamoDB update
    response=$(make_post_request "/tools/journeys_tool" "$read_payload")
    
    local new_status=$(get_json_field "$response" '.data.metadata.status')
    local new_priority=$(get_json_field "$response" '.data.metadata.priority')
    local new_description=$(get_json_field "$response" '.data.metadata.description')
    
    if assert_equal "$new_status" "running" "Status should be updated" && \
       assert_equal "$new_priority" "critical" "Priority should be updated"; then
        log_success "Journey updated successfully"
        end_test "Update Journey" "passed"
        return 0
    else
        end_test "Update Journey" "failed"
        return 1
    fi
}

test_add_stages() {
    start_test "Add Stages to Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping stages test"
        end_test "Add Stages to Journey" "skipped"
        return 0
    fi
    
    local add_stages_payload=$(cat <<EOF
{
    "action": "add_default_stages",
    "journey_id": "$CREATED_JOURNEY_ID"
}
EOF
    )
    
    log_step "Adding default stages to journey"
    local response=$(make_post_request "/tools/journeys_tool" "$add_stages_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to add stages"
        end_test "Add Stages to Journey" "failed"
        return 1
    fi
    
    # List stages to verify
    local list_stages_payload=$(cat <<EOF
{
    "action": "list_stages",
    "journey_id": "$CREATED_JOURNEY_ID"
}
EOF
    )
    
    response=$(make_post_request "/tools/journeys_tool" "$list_stages_payload")
    
    if check_response_success "$response"; then
        local stage_count=$(get_json_field "$response" '.data | length')
        log_success "Added $stage_count stages to journey"
        
        if [ "$stage_count" -gt 0 ]; then
            end_test "Add Stages to Journey" "passed"
            return 0
        else
            log_error "No stages were added"
            end_test "Add Stages to Journey" "failed"
            return 1
        fi
    else
        end_test "Add Stages to Journey" "failed"
        return 1
    fi
}

test_add_rules() {
    start_test "Add Rules to Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping rules test"
        end_test "Add Rules to Journey" "skipped"
        return 0
    fi
    
    local add_rule_payload=$(cat <<EOF
{
    "action": "add_rule",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "raw_analysis",
    "rule_data": {
        "type": "transformation",
        "title": "API Version Update Rule",
        "description": "Update API version from v2 to v3",
        "priority": "high",
        "scope": "global",
        "context": "api",
        "content": "Upgrade API version from 2.x to 3.0 for TMF compliance"
    }
}
EOF
    )
    
    log_step "Adding transformation rule to journey"
    local response=$(make_post_request "/tools/journeys_tool" "$add_rule_payload")
    
    if check_response_success "$response"; then
        log_success "Rule added successfully"
        
        # List rules to verify
        local list_rules_payload=$(cat <<EOF
{
    "action": "list_rules",
    "journey_id": "$CREATED_JOURNEY_ID",
    "stage_id": "raw_analysis"
}
EOF
        )
        
        response=$(make_post_request "/tools/journeys_tool" "$list_rules_payload")
        local rule_count=$(get_json_field "$response" '.data | length')
        
        if [ "$rule_count" -gt 0 ]; then
            log_success "Journey has $rule_count rule(s)"
            end_test "Add Rules to Journey" "passed"
            return 0
        else
            end_test "Add Rules to Journey" "failed"
            return 1
        fi
    else
        log_error "Failed to add rule"
        end_test "Add Rules to Journey" "failed"
        return 1
    fi
}

test_export_journey() {
    start_test "Export Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping export test"
        end_test "Export Journey" "skipped"
        return 0
    fi
    
    local export_payload=$(cat <<EOF
{
    "action": "export_complete",
    "journey_id": "$CREATED_JOURNEY_ID",
    "output_file": "/tmp/test_journey_export_$CREATED_JOURNEY_ID.json"
}
EOF
    )
    
    log_step "Exporting complete journey configuration"
    local response=$(make_post_request "/tools/journeys_tool" "$export_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to export journey"
        end_test "Export Journey" "failed"
        return 1
    fi
    
    # Export writes to file, verify via message or metadata
    local output_file=$(get_json_field "$response" '.metadata.output_file')
    local message=$(get_json_field "$response" '.message')
    
    if [ -n "$output_file" ] || echo "$message" | grep -q "exported"; then
        log_success "Journey exported successfully"
        log_info "  Output file: $output_file"
        
        # Optionally verify file exists on local filesystem (if accessible)
        if [ -f "$output_file" ]; then
            local has_journey=$(jq -e '.journey' "$output_file" > /dev/null 2>&1 && echo "true" || echo "false")
            log_info "  File verified: $has_journey"
        fi
        
        end_test "Export Journey" "passed"
        return 0
    else
        log_error "Export did not produce expected output"
        end_test "Export Journey" "failed"
        return 1
    fi
}

test_delete_journey() {
    start_test "Delete Journey"
    
    if [ -z "$CREATED_JOURNEY_ID" ]; then
        log_warning "No journey ID available, skipping delete test"
        end_test "Delete Journey" "skipped"
        return 0
    fi
    
    # Get record count before deletion
    local before_count=$(get_journey_record_count "$CREATED_JOURNEY_ID")
    log_info "Records before deletion: $before_count"
    
    local delete_payload=$(cat <<EOF
{
    "action": "delete",
    "journey_id": "$CREATED_JOURNEY_ID",
    "confirm": true
}
EOF
    )
    
    log_step "Deleting journey: $CREATED_JOURNEY_ID"
    local response=$(make_post_request "/tools/journeys_tool" "$delete_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to delete journey"
        end_test "Delete Journey" "failed"
        return 1
    fi
    
    sleep 2  # Allow time for DynamoDB deletion
    
    # Verify deletion in DynamoDB
    local after_count=$(get_journey_record_count "$CREATED_JOURNEY_ID")
    log_info "Records after deletion: $after_count"
    
    if [ "$after_count" -eq 0 ]; then
        log_success "Journey and all related records deleted successfully"
        TEST_CLEANUP_NEEDED=false
        end_test "Delete Journey" "passed"
        return 0
    else
        log_error "Journey records still exist in DynamoDB (count: $after_count)"
        end_test "Delete Journey" "failed"
        return 1
    fi
}

test_list_journeys() {
    start_test "List Journeys"
    
    local list_payload=$(cat <<EOF
{
    "action": "list"
}
EOF
    )
    
    log_step "Listing all journeys"
    local response=$(make_post_request "/tools/journeys_tool" "$list_payload")
    
    if ! check_response_success "$response"; then
        log_error "Failed to list journeys"
        end_test "List Journeys" "failed"
        return 1
    fi
    
    local journey_count=$(get_json_field "$response" '.data | length')
    log_success "Found $journey_count journey(s) in the system"
    
    end_test "List Journeys" "passed"
    return 0
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
    
    log_info "Starting Journey CRUD Lifecycle Tests"
    log_info "Server: $SERVER_URL"
    echo ""
    
    # Get initial database state
    INITIAL_DB_COUNT=$(get_dynamodb_count)
    log_info "Initial DynamoDB record count: $INITIAL_DB_COUNT"
    
    # Run tests in sequence
    test_create_journey
    test_read_journey
    test_update_journey
    test_add_stages
    test_add_rules
    test_export_journey
    test_delete_journey
    test_list_journeys
    
    # Cleanup
    cleanup_test_data
    
    # Final database state check
    local final_count=$(get_dynamodb_count)
    log_info "Final DynamoDB record count: $final_count"
    
    # Generate summary and exit
    cleanup_test_environment
    exit $?
}

# Trap to ensure cleanup on exit
trap cleanup_test_data EXIT

# Run main function
main "$@"
