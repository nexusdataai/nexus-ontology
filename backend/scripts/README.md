# Scripts Directory

This directory contains various utility and operational scripts for the AI Job Engine system.

## Directory Structure

### `/journey-scripts/`
Contains all TMF ODA Transformation Journey management scripts. These scripts handle the complete lifecycle of transformation journeys, including:

- **Journey Management**: Create, read, update, delete journeys
- **Stage Management**: Manage transformation stages
- **Rules Management**: Second Brain rules configuration
- **Job Execution**: Run transformation jobs
- **Testing & Utilities**: Various test and utility scripts

For detailed documentation of journey scripts, see [journey-scripts/README.md](journey-scripts/README.md)

### `/actors/`
Contains interactive CLI actors for various system components:

- **`sample/`**: Sample CLI actors demonstrating patterns
- **`journeys/`**: Journey management CLI actor (`journey-manager.py`)

## Quick Start

### Journey Management
```bash
# List all journeys
python scripts/journey-scripts/manage_journey.py --action list-journeys

# Create a new journey
python scripts/journey-scripts/create_complete_journey.py --name "My Journey" --component-type customer-management

# Run a transformation job
python scripts/journey-scripts/run_transformation_job.py --journey-id JRN-123 --stage-id raw_analysis

# Interactive Journey Manager CLI
python scripts/actors/journeys/journey-manager.py
```

## Script Categories

### Core Journey Scripts
- `manage_journey.py` - Comprehensive journey management
- `create_complete_journey.py` - Create complete journey with stages and rules
- `manage_journey_stages.py` - Stage-specific operations
- `manage_second_brain_rules.py` - Rule management

### Execution Scripts
- `run_transformation_job.py` - Execute transformation jobs

### Database Management
- `setup_dynamodb.py` - Setup DynamoDB tables and GSIs
- `inspect_dynamodb_table.py` - Inspect table structure and data
- `cleanup_dynamodb_table.py` - Clean up table data
- `cleanup_incomplete_journeys.py` - Remove incomplete journeys
- `delete_journey.py` - Delete specific journeys

### Testing Scripts
- `test_stage_creation.py` - Test stage creation
- `test_stage_creation_fix.py` - Test stage creation fixes
- `test_ui_development_stage.py` - Test UI development stage
- `manage_journey_test.py` - Comprehensive journey tests

### Update Scripts
- `update_raw_analysis_steps.py` - Update raw analysis stage steps

## Environment Setup

All scripts automatically handle AWS authentication using:
1. AWS_PROFILE environment variable
2. AWS_ROLE_ARN for role assumption
3. Default AWS credential chain

## Dependencies

Scripts require proper Python path setup to import from `src/` modules:
- `src.utils.aws_client_utils` - AWS client utilities
- `src.utils.job_executor` - Job execution utilities
- Other project modules

## Notes

- All journey-related scripts have been organized into the `journey-scripts/` subdirectory for better organization
- Scripts automatically adjust their import paths based on their location
- Interactive CLI actors are kept in the `actors/` directory for separation of concerns
