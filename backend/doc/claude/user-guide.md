# 📖 Claude DevOps Assistant Plugin - User Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Using Commands](#using-commands)
4. [Working with Agents](#working-with-agents)
5. [Leveraging Skills](#leveraging-skills)
6. [Automation with Hooks](#automation-with-hooks)
7. [Claude CLI Integration](#claude-cli-integration)
8. [Agent SDK Usage](#agent-sdk-usage)
9. [Practical Examples](#practical-examples)
10. [Advanced Usage](#advanced-usage)
11. [Troubleshooting](#troubleshooting)

## Introduction

The DevOps Assistant Plugin extends Claude's capabilities with powerful DevOps automation features. Once installed, it seamlessly integrates with Claude CLI and can be used through various interfaces including chat, CLI commands, and SDK integrations.

### Key Features
- 🔧 **Commands**: DevOps operations via simple commands
- 🤖 **Agents**: Specialized AI agents for specific tasks
- 💡 **Skills**: Reusable capabilities for complex operations
- 🔄 **Hooks**: Automated workflows and triggers
- 🔌 **MCP Servers**: Integration with external services

## Getting Started

### Prerequisites
- Claude CLI installed and configured
- Plugin installed (see README.md for installation)
- Proper permissions configured

### Verify Installation
```bash
# Check if plugin is installed
cat ~/.claude/settings.json | jq '.enabledPlugins'

# Verify plugin is enabled
grep "devops-assistant" ~/.claude/settings.json
```

## Using Commands

The plugin provides commands prefixed with `@devops` that can be used in Claude chat or CLI.

### Available Commands

#### 1. Status Command
Check infrastructure and service status:

```bash
# In Claude CLI interactive mode
claude
> @devops status

# With specific parameters
> @devops status --service api-gateway --environment prod

# Direct CLI execution
claude -p "@devops status --format json"
```

#### 2. Logs Command
Retrieve and analyze logs:

```bash
# View recent logs
> @devops logs

# Filter by service and time
> @devops logs --service database --since "1 hour ago"

# Search for errors
> @devops logs --filter error --tail 100
```

### Command Syntax

Commands follow this pattern:
```
@devops <command> [--parameter value] [--flag]
```

Examples:
```bash
@devops status                           # Basic usage
@devops status --service api             # With parameter
@devops logs --tail 50 --follow          # Multiple parameters
```

## Working with Agents

Agents are specialized AI assistants that activate for specific tasks.

### Available Agents

#### 1. Security Reviewer
Automatically reviews code for security issues:

```bash
# In Claude chat
"Review this code for security vulnerabilities: [paste code]"

# The security-reviewer agent automatically activates
```

#### 2. Performance Tester
Analyzes and tests performance:

```bash
# Trigger performance analysis
"Test the performance of our API endpoints"

# Agent will:
# - Analyze current performance metrics
# - Identify bottlenecks
# - Suggest optimizations
```

#### 3. Compliance Checker
Ensures compliance with standards:

```bash
"Check if our deployment meets SOC2 compliance requirements"

# Agent validates against compliance frameworks
```

#### 4. Repository Initializer
Automates repository creation from boilerplate templates:

```bash
# Trigger repository initialization
"Initialize new API service from our boilerplate template"

# Agent will:
# - Fork/clone boilerplate repository
# - Apply project-specific customizations
# - Create branch structure (dev, stage)
# - Push initial code with configured settings
```

#### 5. Spec System Prompt Loader
Initializes and maps the correct workflow system prompts:

```bash
# Initialize spec workflow
"Load system prompt for creating a new feature spec"

# Agent will:
# - Map to correct prompt file path
# - Load appropriate workflow configuration
# - Must be called first for spec processes
```

#### 6. Spec Requirements Writer
Creates and refines requirements documents using EARS syntax:

```bash
# Create requirements document
"Write requirements for user authentication feature"

# Agent will:
# - Generate EARS-compliant requirements
# - Create functional and non-functional requirements
# - Define acceptance criteria
# - Establish requirements traceability
```

#### 7. Design Spec Writer
Creates technical design documents from requirements:

```bash
# Generate design document
"Create design spec for the authentication requirements"

# Agent will:
# - Analyze requirements document
# - Define architecture patterns
# - Create component relationships
# - Specify data models and interfaces
```

#### 8. Spec Tasks Writer
Generates actionable implementation task lists:

```bash
# Create task breakdown
"Generate implementation tasks from the design document"

# Agent will:
# - Break down design into coding tasks
# - Create ordered task list
# - Define task dependencies
# - Estimate implementation effort
```

#### 9. Spec Implementer
Executes coding tasks from task lists:

```bash
# Implement specific task
"Execute task 2.1 from the task list"

# Agent will:
# - Read requirements and design specs
# - Implement functional code
# - Follow architecture patterns
# - Update task completion status
```

#### 10. Test Spec Writer
Creates comprehensive test documentation and code:

```bash
# Generate test specifications
"Write test cases for the authentication feature"

# Agent will:
# - Create test documentation
# - Generate executable test code
# - Define acceptance criteria tests
# - Ensure 1:1 mapping between docs and tests
```

#### 11. Spec Judge
Evaluates and combines multiple spec document versions:

```bash
# Evaluate document versions
"Compare and select best requirements from multiple versions"

# Agent will:
# - Assess document quality
# - Compare multiple versions
# - Select or combine best solutions
# - Provide improvement recommendations
```

### Activating Agents

Agents can be activated in three ways:

**1. Automatic Activation** (based on context)
```bash
# Just mention the task
"Can you review our deployment security?"
# Security reviewer agent activates automatically
```

**2. Explicit Activation**
```bash
# Use agent name directly
"@agent security-reviewer analyze the terraform configs"
```

**3. Programmatic Activation** (via SDK)
```python
from claude import agents

# Load and use specific agent
security_agent = agents.load('security-reviewer')
result = security_agent.analyze(code_path='./src')
```

## Leveraging Skills

Skills are reusable capabilities that can be invoked for specific tasks.

### Available Skills

#### 1. Code Reviewer Skill
```bash
# In Claude chat
"Review the Python code in app.py for best practices"

# Via CLI
claude -p "Use code-reviewer skill to analyze the repository"
```

#### 2. PDF Processor Skill
```bash
# Process documentation
"Extract and summarize the deployment guide from guide.pdf"

# Batch processing
"Process all PDF reports in /docs folder"
```

### Using Skills in Conversations

Skills integrate naturally into conversations:

```bash
# Claude automatically uses appropriate skills
User: "Review our API code and generate a security report as PDF"
Claude: [Uses code-reviewer skill → generates findings → uses pdf-processor to create report]
```

## Automation with Hooks

Hooks provide automated triggers for DevOps workflows.

### Git Hooks
Automatically installed and activated:

```bash
# Pre-commit hook
git commit -m "Update API"
# → Automatically runs security scan
# → Formats code
# → Validates configuration

# Pre-push hook  
git push origin main
# → Runs tests
# → Checks compliance
# → Validates deployment readiness
```

### Deployment Hooks
```bash
# Pre-deployment
@devops deploy --env production
# → Backup current state
# → Validate configuration
# → Check dependencies

# Post-deployment
# → Health checks
# → Monitoring activation
# → Notification sending
```

## Claude CLI Integration

### Interactive Mode

Start Claude in interactive mode with the plugin:

```bash
# Start Claude CLI
claude

# Now you can use plugin features
> @devops status
> Tell me about our infrastructure health
> Review the recent deployment logs
```

### Non-Interactive Mode (Scripting)

Use the `-p` flag for scripting:

```bash
# Get status report
claude -p "@devops status --format json" > status.json

# Analyze logs
claude -p "Analyze the last 100 error logs from production" 

# Chain commands
claude -p "@devops status" && claude -p "@devops logs --filter error"
```

### Pipeline Integration

```yaml
# In CI/CD pipeline (e.g., GitHub Actions)
- name: DevOps Status Check
  run: |
    claude -p "@devops status --environment ${{ github.event.deployment.environment }}"
    
- name: Security Review
  run: |
    claude -p "Review security of changed files" --allowed-tools "Read,Bash"
```

## Agent SDK Usage

### Basic SDK Integration

```python
# Python example
from claude import Claude, plugins

# Initialize Claude with plugin
claude = Claude()
devops_plugin = plugins.load('devops-assistant')

# Use plugin commands
status = devops_plugin.execute_command('status', {
    'environment': 'production',
    'format': 'json'
})

# Use plugin agents
security_agent = devops_plugin.get_agent('security-reviewer')
review_result = security_agent.review({
    'code_path': './src',
    'severity': 'high'
})
```

### JavaScript/TypeScript SDK

```javascript
// Node.js example
const { Claude } = require('@claude/sdk');

// Initialize with plugin
const claude = new Claude({
  plugins: ['devops-assistant']
});

// Execute commands
async function checkStatus() {
  const result = await claude.plugin('devops-assistant')
    .command('status')
    .execute({ environment: 'prod' });
  
  console.log(result);
}

// Use agents
async function securityReview() {
  const agent = await claude.plugin('devops-assistant')
    .agent('security-reviewer');
  
  const findings = await agent.analyze({
    target: './app',
    checkType: 'full'
  });
  
  return findings;
}
```

### Advanced SDK Features

```python
# Webhook integration
from claude.plugins import devops

# Set up webhook handler
@devops.hook('deployment.started')
def on_deployment_start(event):
    # Custom logic when deployment starts
    devops.command('status', {'service': event.service})
    
# Skill composition
async def complex_workflow():
    # Chain multiple skills
    review = await devops.skill('code-reviewer').analyze('./src')
    
    if review.has_issues:
        report = await devops.skill('pdf-processor').generate_report(review)
        await send_to_team(report)
    
    return await devops.command('deploy', {'safe_mode': review.has_issues})
```

## Practical Examples

### Example 1: Daily Status Report

```bash
#!/bin/bash
# daily-status.sh

# Get comprehensive status
STATUS=$(claude -p "@devops status --format json")

# Analyze logs for errors
ERRORS=$(claude -p "@devops logs --filter error --since '24 hours ago'")

# Generate report
claude -p "Generate a daily DevOps report based on: $STATUS and $ERRORS"
```

### Example 2: Automated Code Review

```python
# review-pr.py
from claude import Claude

claude = Claude()

def review_pull_request(pr_number):
    # Get PR changes
    changes = get_pr_changes(pr_number)
    
    # Perform security review
    review = claude.run(
        f"Review these code changes for security issues: {changes}",
        tools=['security-reviewer']
    )
    
    # Post review comments
    post_review_to_pr(pr_number, review)
    
    return review.approved
```

### Example 3: Infrastructure Monitoring

```javascript
// monitor.js
const { Claude } = require('@claude/sdk');

class InfrastructureMonitor {
  constructor() {
    this.claude = new Claude({ plugins: ['devops-assistant'] });
  }
  
  async checkHealth() {
    // Get status
    const status = await this.claude
      .plugin('devops-assistant')
      .command('status')
      .execute({ format: 'json' });
    
    // Check thresholds
    if (status.cpu_usage > 80) {
      await this.scaleUp();
    }
    
    if (status.error_rate > 0.01) {
      await this.alertTeam(status);
    }
    
    return status;
  }
  
  async scaleUp() {
    return await this.claude.run(
      "Scale up the API service by 2 instances"
    );
  }
}
```

### Example 4: ChatOps Integration

```python
# slack-bot.py
from slack_sdk import WebClient
from claude import Claude

claude = Claude()
slack = WebClient(token=SLACK_TOKEN)

def handle_slack_command(command, channel):
    # Route DevOps commands to Claude
    if command.startswith('/devops'):
        response = claude.run(f"@devops {command[8:]}")
        slack.chat_postMessage(channel=channel, text=response)
    
    elif command.startswith('/review'):
        response = claude.run(
            f"Review the code security",
            agents=['security-reviewer']
        )
        slack.chat_postMessage(channel=channel, text=response)
```

### Example 5: Repository Initialization

```python
# init-repo.py
from claude import Claude

claude = Claude()

def initialize_new_service(service_name, team_name):
    # Trigger repository initialization
    response = claude.run(
        f"""Initialize a new repository:
        - Use boilerplate: https://github.com/{team_name}/boilerplate-api
        - New repo: https://github.com/{team_name}/{service_name}
        - Create dev and stage branches
        - Update README with {service_name} details
        - Commit message: 'Initial {service_name} setup'
        """,
        agents=['repository-initializer']
    )
    
    return response

# Batch initialization for microservices
services = ['user-service', 'payment-service', 'notification-service']
for service in services:
    result = initialize_new_service(service, 'your-org')
    print(f"Initialized: {service} - {result.status}")
```

```bash
# Via CLI
claude -p "Initialize new API service from https://github.com/your-org/boilerplate-api into api-onboarding-service repository"

# The repository-initializer agent will:
# 1. Fork/clone the boilerplate
# 2. Create the new repository
# 3. Apply customizations (README, configs)
# 4. Create branch structure (main, dev, stage)
# 5. Push with "Initial onboarding" commit
```

## Advanced Usage

### Custom Workflows

Create complex automation workflows:

```yaml
# .claude-workflow.yml
name: deployment-pipeline
triggers:
  - push:
      branch: main

steps:
  - name: Status Check
    command: "@devops status"
    
  - name: Security Review
    agent: security-reviewer
    params:
      severity: high
      
  - name: Performance Test
    agent: performance-tester
    params:
      endpoints: ["api/*", "web/*"]
      
  - name: Deploy
    command: "@devops deploy"
    condition: ${{ steps.security.passed && steps.performance.passed }}
```

### Environment-Specific Configuration

```json
// .claude-plugin-config.json
{
  "devops-assistant": {
    "environments": {
      "development": {
        "auto_deploy": true,
        "security_level": "low"
      },
      "production": {
        "auto_deploy": false,
        "security_level": "high",
        "require_approval": true
      }
    }
  }
}
```

### Extending the Plugin

Add custom commands or skills:

```python
# custom_skill.py
from claude.plugins.devops import register_skill

@register_skill('custom-analyzer')
class CustomAnalyzer:
    def analyze(self, target):
        # Custom analysis logic
        return results
        
# Register with plugin
devops_plugin.add_skill(CustomAnalyzer())
```

## Troubleshooting

### Common Issues

#### Plugin Commands Not Working
```bash
# Verify plugin is enabled
cat ~/.claude/settings.json | grep devops-assistant

# Check plugin validation
claude plugin validate /path/to/plugin

# Reinstall if needed
claude plugin uninstall devops-assistant
claude plugin install devops-assistant
```

#### Agent Not Activating
```bash
# Check agent configuration
cat ~/.claude/plugins/devops-assistant/agents/*.md

# Manually activate agent
claude -p "@agent security-reviewer review this code"

# Check logs
tail -f ~/.claude/logs/claude.log
```

#### Permission Errors
```bash
# Grant necessary permissions
claude plugin permissions devops-assistant --grant-all

# Or specific permissions
claude plugin permissions devops-assistant --grant file:read,process:execute
```

### Debug Mode

Enable debug mode for detailed information:

```bash
# Run with debug flag
claude --debug "@devops status"

# Verbose output
claude -vvv "@devops logs"

# Trace mode
CLAUDE_TRACE=1 claude "@devops status"
```

### Getting Help

```bash
# Plugin-specific help
claude help @devops

# Command help
claude help @devops status

# View documentation
claude docs devops-assistant
```

## Best Practices

1. **Use Appropriate Tools**: Choose the right tool for the task
   - Commands for operations
   - Agents for analysis
   - Skills for specific capabilities

2. **Security First**: Always review security implications
   - Use security-reviewer agent for code changes
   - Enable security hooks for deployments
   - Regular compliance checks

3. **Automate Wisely**: Balance automation with control
   - Use hooks for repetitive tasks
   - Keep manual approval for critical operations
   - Monitor automated actions

4. **Performance Monitoring**: Keep track of system health
   - Regular status checks
   - Log analysis for issues
   - Performance testing before deployment

5. **Documentation**: Keep your usage documented
   - Document custom workflows
   - Share team configurations
   - Maintain runbooks

## Support & Resources

- **Plugin Repository**: https://github.com/trilogy-group/swarm-claude-plugin
- **Documentation**: See `sample-plugin/README.md`
- **Issues**: Report at repository issues page
- **Community**: Join Claude plugin developers community

---

*Last Updated: November 2024 | Plugin Version: 1.0.0*
