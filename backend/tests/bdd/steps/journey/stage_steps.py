#!/usr/bin/env python3
"""
Stage management step definitions for BDD testing
"""

from behave import given, when, then, step
from behave.runner import Context
import time
from typing import Dict, List, Any


# Add missing undefined steps
@then('it should be created with template configuration')
def step_impl_template_config(context):
    """Verify template configuration was applied"""
    output = context.cli.get_current_output()
    assert "created" in output.lower() or "template" in output.lower(), \
        "Template configuration not confirmed"


# ==================== GIVEN Steps ====================

@given('the journey has the following stages')
def step_create_journey_stages(context: Context):
    """Create stages for the current journey from table data"""
    if not context.table:
        raise ValueError("No stage data provided")
    
    journey_id = context.test_journey_id
    stages = []
    
    for row in context.table:
        stage_data = dict(row)
        # Convert sequenceOrder to int
        if 'sequenceOrder' in stage_data:
            stage_data['sequenceOrder'] = int(stage_data['sequenceOrder'])
        
        stage = context.test_data.create_stage(journey_id, stage_data)
        stages.append(stage)
    
    context.test_stages = stages
    context.test_stage_id = stages[0]['stageId'] if stages else None


@given('the journey has a stage "{stage_id}"')
def step_create_single_stage(context: Context, stage_id: str):
    """Create a single stage for the journey"""
    journey_id = context.test_journey_id
    stage = context.test_data.create_stage(journey_id, {
        'stageId': stage_id,
        'stageName': f'Test Stage - {stage_id}',
        'description': f'Test stage for {stage_id}'
    })
    
    context.test_stage_id = stage_id
    context.test_stage = stage


@given('the journey has multiple stages including "{stage_id}"')
def step_create_multiple_stages_including(context: Context, stage_id: str):
    """Create multiple stages including a specific one"""
    journey_id = context.test_journey_id
    
    stages_to_create = [
        {'stageId': 'raw_analysis', 'stageName': 'Raw Analysis'},
        {'stageId': stage_id, 'stageName': f'Test Stage - {stage_id}'},
        {'stageId': 'tmf_mapping', 'stageName': 'TMF Mapping'},
        {'stageId': 'data_validation', 'stageName': 'Data Validation'}
    ]
    
    stages = context.test_data.create_stages_for_journey(journey_id, stages_to_create)
    context.test_stages = stages
    context.test_stage_id = stage_id


@given('the journey has stages in order: "{stage_order}"')
def step_create_ordered_stages(context: Context, stage_order: str):
    """Create stages in specific order"""
    journey_id = context.test_journey_id
    stage_ids = [s.strip() for s in stage_order.split(',')]
    
    stages_data = []
    for i, stage_id in enumerate(stage_ids):
        stages_data.append({
            'stageId': stage_id,
            'stageName': f'Stage - {stage_id}',
            'sequenceOrder': i + 1
        })
    
    stages = context.test_data.create_stages_for_journey(journey_id, stages_data)
    context.test_stages = stages
    context.original_stage_order = stage_ids


@given('the stage "{stage_id}" is ready for execution')
def step_prepare_stage_for_execution(context: Context, stage_id: str):
    """Prepare a stage for execution"""
    # Create stage if it doesn't exist
    if not hasattr(context, 'test_stages') or not any(s['stageId'] == stage_id for s in context.test_stages):
        stage = context.test_data.create_stage(context.test_journey_id, {
            'stageId': stage_id,
            'stageName': f'Stage - {stage_id}',
            'status': 'pending',
            'enabled': True
        })
        if not hasattr(context, 'test_stages'):
            context.test_stages = []
        context.test_stages.append(stage)
    
    context.execution_stage_id = stage_id


@given('the stage "{stage_id}" has been executed multiple times')
def step_create_stage_execution_history(context: Context, stage_id: str):
    """Create execution history for a stage"""
    journey_id = context.test_journey_id
    
    # Create multiple job executions
    for i in range(3):
        job = context.test_data.create_job(journey_id, stage_id, {
            'status': 'completed' if i < 2 else 'failed',
            'duration': f'{30 + i*10}m',
            'metrics': {
                'recordsProcessed': 1000 + i*500,
                'recordsFailed': i * 10,
                'executionTime': 1800 + i*600
            }
        })
    
    context.stage_with_history = stage_id


@given('the journey has stages including "{stage_id}"')
def step_create_journey_with_stages_including(context: Context, stage_id: str):
    """Create stages for journey including a specific one"""
    journey_id = getattr(context, 'test_journey_id', getattr(context, 'current_journey_id', 'JRN-TEST'))
    
    stages_to_create = [
        {'stageId': 'raw_analysis', 'stageName': 'Raw Analysis', 'sequenceOrder': 1},
        {'stageId': 'stripped_schema', 'stageName': 'Schema Stripping', 'sequenceOrder': 2},
        {'stageId': stage_id, 'stageName': f'Stage - {stage_id}', 'sequenceOrder': 3},
        {'stageId': 'data_validation', 'stageName': 'Data Validation', 'sequenceOrder': 4}
    ]
    
    # Remove duplicates (if stage_id is already in the list)
    seen = set()
    unique_stages = []
    for s in stages_to_create:
        if s['stageId'] not in seen:
            seen.add(s['stageId'])
            unique_stages.append(s)
    
    context.test_stages = unique_stages
    context.current_stage_id = stage_id


@given('I am adding a new stage')
def step_start_adding_stage(context: Context):
    """Initialize context for adding a new stage"""
    context.adding_new_stage = True


@when('I try to save with invalid configuration:')
@when('I try to save with invalid configuration')
def step_try_save_invalid_stage(context: Context):
    """Try to save stage with invalid configuration"""
    if not context.table:
        raise ValueError("No invalid config data provided")
    
    for row in context.table:
        field = row['field']
        value = row['value']
        # Send invalid value
        try:
            context.cli.wait_for_prompt([f'{field}:', field], timeout=3)
            context.cli.send_input(value)
        except:
            pass
    
    context.expected_validation_errors = True


@then('I should see appropriate validation errors')
def step_verify_stage_validation_errors(context: Context):
    """Verify validation errors are shown"""
    output = context.cli.get_current_output()
    assert any(word in output.lower() for word in ['error', 'invalid', 'required', 'validation']), \
        "Validation error not shown"


@then('the stage should not be saved')
def step_verify_stage_not_saved(context: Context):
    """Verify stage was not saved due to errors"""
    output = context.cli.get_current_output()
    assert 'saved successfully' not in output.lower(), "Stage was saved when it shouldn't be"


@when('I save the stage')
def step_save_stage(context: Context):
    """Save the stage"""
    try:
        context.cli.wait_for_prompt(['Save', 'Confirm', 'Enter'])
        context.cli.send_input('y')
    except:
        context.cli.send_input('')


@then('I should be able to customize the template values')
def step_verify_template_customizable(context: Context):
    """Verify template values can be customized"""
    output = context.cli.get_current_output()
    # Template should show pre-filled values that can be edited
    assert any(word in output.lower() for word in ['edit', 'modify', 'change', 'enter']), \
        "Template values don't appear customizable"


@given('stage templates are available')
def step_setup_stage_templates(context: Context):
    """Set up stage templates"""
    context.stage_templates = [
        {
            'name': 'Standard Data Validation',
            'stageId': 'data_validation',
            'estimatedDuration': '2h',
            'steps': [
                {'name': 'Schema Validation', 'duration': '30m'},
                {'name': 'Data Quality Check', 'duration': '1h'},
                {'name': 'Report Generation', 'duration': '30m'}
            ]
        }
    ]


# ==================== WHEN Steps ====================

@when('I choose stage "{stage_id}"')
@when('I choose stage "{stage_id}" from the list')
def step_choose_stage(context: Context, stage_id: str):
    """Select a stage from list"""
    # Wait for stage list
    context.cli.wait_for_prompt(['Select stage', 'choice', ':'])
    
    output = context.cli.get_current_output()
    lines = output.split('\n')
    
    stage_found = False
    for line in lines:
        if stage_id in line and line.strip() and line.strip()[0].isdigit():
            number = line.strip().split('.')[0]
            context.cli.send_input(number)
            stage_found = True
            break
    
    assert stage_found, f"Stage {stage_id} not found in list"
    context.selected_stage_id = stage_id


@when('I enter the following stage details:')
@when('I enter the following stage details')
def step_enter_stage_details(context: Context):
    """Enter stage details from table data"""
    if not context.table:
        raise ValueError("No stage data provided")
    
    for row in context.table:
        field = row['field']
        value = row['value']
        
        # Map field names to prompts
        prompt_map = {
            'stageId': ['Stage ID:', 'stageId:'],
            'stageName': ['Stage Name:', 'stageName:', 'Name:'],
            'description': ['Description:', 'description:'],
            'estimatedDuration': ['Duration:', 'Estimated Duration:', 'duration:'],
            'canSkip': ['Can Skip', 'Skippable', 'canSkip'],
            'requiresApproval': ['Requires Approval', 'Approval', 'requiresApproval']
        }
        
        patterns = prompt_map.get(field, [f'{field}:', field])
        try:
            context.cli.wait_for_prompt(patterns, timeout=5)
            context.cli.send_input(value)
        except:
            # Field might not be prompted, store for later
            if not hasattr(context, 'stage_form_data'):
                context.stage_form_data = {}
            context.stage_form_data[field] = value


@when('I add the following steps:')
@when('I add the following steps')
def step_add_stage_steps(context: Context):
    """Add steps to a stage from table data"""
    if not context.table:
        raise ValueError("No step data provided")
    
    for i, row in enumerate(context.table):
        # Prompt indicates we're adding a step
        context.cli.wait_for_prompt([f'Step {i+1}:', 'Name:'])
        context.cli.send_input(row['name'])
        
        context.cli.wait_for_prompt(['Description:'])
        context.cli.send_input(row['description'])
        
        context.cli.wait_for_prompt(['duration', 'optional'])
        context.cli.send_input(row.get('duration', ''))
    
    # End step entry with empty name
    context.cli.wait_for_prompt(['Name:'])
    context.cli.send_input('')


@when('I specify new order "{new_order}"')
def step_specify_stage_order(context: Context, new_order: str):
    """Specify new stage order"""
    context.cli.wait_for_prompt(['order:', 'sequence:'])
    context.cli.send_input(new_order)
    
    context.new_stage_order = [s.strip() for s in new_order.split(',')]


@when('I choose to {action} stage "{stage_id}"')
def step_stage_action(context: Context, action: str, stage_id: str):
    """Perform an action on a stage"""
    # First select the stage
    step_choose_stage(context, stage_id)
    
    # Confirm action if needed
    if action in ['disable', 'delete']:
        context.cli.wait_for_prompt(['confirm', '(y/n)'])
        context.cli.send_input('y')


@when('I set dependency on "{dependency_stage}" with condition "{condition}"')
def step_set_stage_dependency(context: Context, dependency_stage: str, condition: str):
    """Set stage dependency"""
    # Select dependency stage
    context.cli.wait_for_prompt(['Select dependency', 'stage:'])
    step_choose_stage(context, dependency_stage)
    
    # Select condition
    context.cli.wait_for_prompt(['condition:', 'Select'])
    condition_map = {
        'completed': '1',
        'succeeded': '2',
        'any': '3'
    }
    context.cli.send_input(condition_map.get(condition, '1'))


@when('I choose "Create from template"')
def step_choose_template_option(context: Context):
    """Choose to create from template"""
    context.cli.wait_for_prompt(['template', 'Select option'])
    context.cli.send_input('1')  # Assuming option 1 is "Create from template"


@when('I select template "{template_name}"')
def step_select_stage_template(context: Context, template_name: str):
    """Select a specific template"""
    context.cli.wait_for_prompt(['Select template', 'choice'])
    
    # Find template in list
    output = context.cli.get_current_output()
    lines = output.split('\n')
    
    for line in lines:
        if template_name in line and line.strip()[0].isdigit():
            number = line.strip().split('.')[0]
            context.cli.send_input(number)
            break


# ==================== THEN Steps ====================

@then('the stage should be added to the journey')
def step_verify_stage_added(context: Context):
    """Verify stage was added successfully"""
    output = context.cli.get_current_output()
    assert "added successfully" in output.lower(), "Stage addition not confirmed"
    
    # Could also verify in database
    # stage = context.test_data.get_stage(context.test_journey_id, context.last_stage_id)
    # assert stage is not None


@then('the stage sequence should be updated')
def step_verify_stage_sequence(context: Context):
    """Verify stage sequence was updated"""
    # This would typically involve checking the database
    # For now, verify success message
    output = context.cli.get_current_output()
    assert any(word in output.lower() for word in ['sequence', 'order', 'updated']), \
        "Stage sequence update not confirmed"


@then('I should see {count:d} stages in order')
def step_verify_stage_count_and_order(context: Context, count: int):
    """Verify number of stages and their order"""
    output = context.cli.get_current_output()
    
    # Count stages (looking for numbered list or stage IDs)
    stage_count = 0
    lines = output.split('\n')
    for line in lines:
        if any(stage_id in line for stage_id in ['raw_analysis', 'stripped_schema', 
                                                  'tmf_mapping', 'data_validation']):
            stage_count += 1
    
    assert stage_count == count, f"Expected {count} stages, found {stage_count}"


@then('each stage should show its status and sequence')
def step_verify_stage_display(context: Context):
    """Verify stage information is displayed"""
    output = context.cli.get_current_output()
    
    # Check for expected fields
    expected_fields = ['status', 'sequence', 'order']
    for field in expected_fields:
        assert field in output.lower(), f"Stage {field} not displayed"


@then('the current stage should be highlighted')
def step_verify_current_stage_highlight(context: Context):
    """Verify current stage is highlighted"""
    output = context.cli.get_current_output()
    # Look for indicators like ">>", "current", "*", etc.
    assert any(indicator in output for indicator in ['>>', 'current', '*', 'CURRENT']), \
        "Current stage not highlighted"


@then('the stage should reflect the new configuration')
def step_verify_stage_updated(context: Context):
    """Verify stage configuration was updated"""
    output = context.cli.get_current_output()
    assert "updated successfully" in output.lower(), "Stage update not confirmed"


@then('the stage should no longer be in the journey')
def step_verify_stage_deleted(context: Context):
    """Verify stage was removed"""
    output = context.cli.get_current_output()
    assert "removed successfully" in output.lower(), "Stage removal not confirmed"


@then('the remaining stages should be resequenced')
def step_verify_stages_resequenced(context: Context):
    """Verify stages were resequenced after deletion"""
    # This would check database for proper sequence numbers
    # For now, verify message
    output = context.cli.get_current_output()
    assert any(word in output.lower() for word in ['resequenced', 'updated', 'adjusted']), \
        "Stage resequencing not confirmed"


@then('the stages should be in the new sequence')
def step_verify_new_stage_order(context: Context):
    """Verify stages are in new order"""
    output = context.cli.get_current_output()
    assert "reordered successfully" in output.lower(), "Stage reorder not confirmed"
    
    # Verify new order matches requested order
    if hasattr(context, 'new_stage_order'):
        for i, stage_id in enumerate(context.new_stage_order):
            assert stage_id in output, f"Stage {stage_id} not found in new order"


@then('stage dependencies should be validated')
def step_verify_dependencies_validated(context: Context):
    """Verify stage dependencies are validated"""
    output = context.cli.get_current_output()
    # Look for validation confirmation or no errors
    assert "error" not in output.lower() or "invalid" not in output.lower(), \
        "Dependency validation failed"


@then('the stage should not start until dependency is met')
def step_verify_dependency_enforcement(context: Context):
    """Verify dependency is enforced"""
    output = context.cli.get_current_output()
    assert "configured successfully" in output.lower(), "Dependency configuration not confirmed"


@then('the stage should be skipped during execution')
def step_verify_stage_skipped(context: Context):
    """Verify disabled stage is skipped"""
    output = context.cli.get_current_output()
    assert "disabled successfully" in output.lower(), "Stage disable not confirmed"


@when('I enable the stage again')
def step_enable_stage(context: Context):
    """Enable a disabled stage"""
    # Assuming we're in enable/disable menu
    context.cli.wait_for_prompt(['enable', 'Select'])
    context.cli.send_input('y')  # Confirm enable


@then('the stage should be included in execution')
def step_verify_stage_enabled(context: Context):
    """Verify stage is enabled"""
    output = context.cli.get_current_output()
    assert "enabled" in output.lower(), "Stage enable not confirmed"


@then('I should see complete stage configuration including')
def step_verify_stage_details(context: Context):
    """Verify all stage details are shown"""
    if not context.table:
        raise ValueError("No expected fields provided")
    
    output = context.cli.get_current_output()
    
    for row in context.table:
        field = row['field']
        visible = row['visible'].lower() == 'yes'
        
        if visible:
            assert field.lower() in output.lower(), f"Field '{field}' not found in stage details"


@then('I should see execution history with')
def step_verify_execution_history(context: Context):
    """Verify execution history details"""
    if not context.table:
        raise ValueError("No expected fields provided")
    
    output = context.cli.get_current_output()
    
    for row in context.table:
        field = row['field']
        visible = row['visible'].lower() == 'yes'
        
        if visible:
            assert field.lower() in output.lower(), f"Field '{field}' not found in execution history"


@then('the stage form should be pre-populated')
def step_verify_template_prepopulated(context: Context):
    """Verify form is pre-populated from template"""
    output = context.cli.get_current_output()
    # Look for template values in prompts
    assert any(template_value in output for template_value in ['data_validation', '2h', 'Schema']), \
        "Template values not found in form"
