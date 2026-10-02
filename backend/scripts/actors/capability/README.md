# Capability Manager CLI

## Overview
The Capability Manager CLI is a comprehensive command-line interface for managing TMF ODA business capabilities, components, implementation jobs, and performance metrics. It provides a unified portal that integrates all capability-scripts functionality.

## Features
- **Capability Management**: Create, view, update, and delete capabilities
- **Component Management**: Manage software components and dependencies
- **Implementation Jobs**: Track and manage deployment jobs
- **Performance Metrics**: Monitor and analyze performance data
- **Analytics & Reports**: Generate comprehensive reports
- **Batch Operations**: Bulk import/export and updates
- **Journey Integration**: Link capabilities with transformation journeys

## Test Mode (No Authentication Required)
The CLI now supports a **TEST MODE** that allows you to run and explore all features without AWS credentials or authentication.

### How to Use Test Mode
By default, TEST_MODE is enabled in the script. When running in test mode:
- No AWS authentication is required
- All data operations use mock data
- Changes are not persisted
- Auto-login as "testuser"

### Running the CLI

```bash
# Make the script executable (if not already)
chmod +x /opt/mycode/ptr/ai-job-engine/scripts/actors/capability/capability-manager.py

# Run the CLI
./scripts/actors/capability/capability-manager.py
```

### Test Mode Features
In test mode, you can:
1. Browse mock capabilities (CAP-001, CAP-002, CAP-003)
2. View mock components and their details
3. See sample implementation jobs
4. Review mock performance metrics
5. Navigate through all menus and features
6. Test the user interface and workflows

### Sample Mock Data Available
- **Capabilities**: Customer Management, Product Catalog, Order Processing
- **Components**: Customer API, Customer Database
- **Jobs**: Deployment and migration jobs
- **Metrics**: Response time and success rate metrics

### Switching to Production Mode
To use with real AWS resources, edit the script and set:
```python
TEST_MODE = False
```

Then ensure you have:
1. AWS credentials configured
2. Required DynamoDB tables created
3. Proper IAM permissions

## Menu Navigation
The CLI uses a hierarchical menu system with breadcrumb navigation:
- Use number keys to select menu options
- Option `0` always returns to the previous menu
- Current context (capability, component) is displayed in the header
- Color-coded output for better visibility

## Key Shortcuts
- `list` - When prompted for an ID, type "list" to see available options
- `Enter` - Press Enter to skip optional fields
- `Ctrl+C` - Exit the application at any time

## Requirements
- Python 3.7+
- boto3 (only for production mode)
- AWS credentials (only for production mode)

## Support
For issues or questions, please contact the TMF ODA team.
