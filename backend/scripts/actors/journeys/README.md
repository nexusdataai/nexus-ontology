# Enhanced Journey Manager CLI

## Overview

The Enhanced Journey Manager is a comprehensive, interactive command-line interface that consolidates all TMF ODA Transformation Journey management functionalities into a single, unified portal. It incorporates all features from the journey-scripts folder with an intuitive nested menu system and breadcrumb navigation.

## Features

### 🎯 Core Functionality

1. **Journey Management**
   - Create, update, delete, and clone journeys
   - Export/import journeys as JSON
   - Interactive journey creation wizard
   - Journey selection and filtering

2. **Stage Management**
   - Add, update, delete, and reorder stages
   - Enable/disable stages
   - Manage stage steps
   - Default 6-stage transformation template

3. **Second Brain Rules**
   - Add, update, delete rules
   - Enable/disable rules
   - Export/import rules
   - Interactive rule builder
   - Default rules templates

4. **Job Execution**
   - Run transformation jobs
   - Monitor job progress in real-time
   - Cancel running jobs
   - Retry failed jobs
   - Batch operations
   - Job metrics and timeline

5. **Logs & Reports**
   - View and search logs
   - Export logs in multiple formats
   - Generate performance reports
   - Error analysis and summaries
   - Custom report generation

6. **Dashboards**
   - Journey dashboard with comprehensive metrics
   - Job execution dashboards
   - Stage progress visualization
   - Rules effectiveness metrics
   - System overview and health
   - Performance analytics

7. **Database Operations**
   - Setup DynamoDB tables and indexes
   - Inspect table structure
   - View table statistics
   - Cleanup operations
   - Data export
   - Health checks

8. **Quick Actions**
   - Status overview
   - Quick transformation runs
   - Recent activities view
   - Health checks
   - Complete journey creation
   - Batch transformations

## Usage

### Starting the Journey Manager

```bash
cd /opt/mycode/ptr/ai-job-engine
python3 scripts/actors/journeys/journey-manager.py
```

### Navigation

The journey manager uses a nested menu system with breadcrumb navigation:

```
====================================================================================================
🚀 [TMF ODA JOURNEY MANAGER] Enhanced v3.0
📍 Main Menu > Journey Management > Create Journey
📋 Create New Journey
====================================================================================================
```

Navigate using numbered menu options and follow the prompts. Use `0` to go back to the previous menu.

### Menu Structure

```
Main Menu
├── 1. Journey Operations
│   ├── List Journeys
│   ├── Create Journey
│   ├── Select Journey
│   ├── Update Journey
│   ├── Delete Journey
│   ├── Clone Journey
│   ├── Export/Import
│   └── ...
├── 2. Stage Management
├── 3. Second Brain Rules
├── 4. Job Execution
├── 5. Logs & Reports
├── 6. Dashboards
├── 7. Database Operations
├── 8. Quick Actions
└── 0. Exit
```

## Key Features

### Real-time Job Monitoring

When running jobs, you can monitor progress in real-time:

```
📊 Monitoring Job Progress (Ctrl+C to stop)...
------------------------------------------------------------
🏃 Status: running | Progress: [████████████░░░░░░░░] 60%
```

### Visual Progress Indicators

The manager uses visual indicators throughout:
- Progress bars with color coding
- Status emojis (⏳ pending, 🏃 running, ✅ completed, ❌ failed)
- Formatted tables and dashboards

### Batch Operations

Perform operations on multiple items:
- Run transformations across multiple journeys
- Retry all failed jobs
- Cancel multiple running jobs
- Run specific stages across journeys

### Comprehensive Error Handling

- Detailed error messages
- Suggestions and recommendations
- Rollback capabilities
- Validation at each step

## AWS Authentication

The Journey Manager automatically handles AWS authentication using:
1. `AWS_PROFILE` environment variable
2. `AWS_ROLE_ARN` for role assumption
3. Default AWS credential chain

## Dependencies

The Enhanced Journey Manager integrates with:
- `manage_journey.py` - Core journey operations
- `manage_journey_stages.py` - Stage management
- `manage_second_brain_rules.py` - Rules management
- `TransformationJobExecutor` - Job execution
- DynamoDB and S3 AWS services

## Architecture

The manager follows a modular architecture:
- `EnhancedJourneyManager` - Main orchestrator class
- `MenuContext` - Breadcrumb navigation management
- Integrated managers from journey-scripts
- AWS resource management
- Helper utilities for formatting and display

## Best Practices

1. **Always Select a Journey First**: Many operations require a selected journey
2. **Use Test Mode**: When testing, enable test mode to prevent actual data changes
3. **Monitor Long Operations**: Use the monitoring features for long-running jobs
4. **Regular Health Checks**: Run system health checks periodically
5. **Export Before Major Changes**: Export journeys before making significant modifications

## Troubleshooting

### Common Issues

1. **No Journeys Found**
   - Check AWS credentials
   - Verify DynamoDB table exists
   - Ensure proper IAM permissions

2. **Job Failures**
   - Check error logs
   - Verify stage configuration
   - Review Second Brain rules

3. **Performance Issues**
   - Run performance analytics
   - Check for hot partitions
   - Review resource utilization

### Debug Mode

Set environment variable for additional logging:
```bash
export DEBUG=true
python3 scripts/actors/journeys/journey-manager.py
```

## Version History

- **v3.0** - Enhanced version with all journey-scripts functionality integrated
- **v2.0** - Basic journey manager with authentication
- **v1.0** - Initial CLI implementation

## Support

For issues or questions:
1. Check the logs in the Logs & Reports section
2. Run the health check in Database Operations
3. Review error summaries and analytics
4. Contact the system administrator

---

**Note**: This is a powerful tool with the ability to modify production data. Always use caution and verify operations in test mode first.
