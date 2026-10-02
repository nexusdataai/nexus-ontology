# Claude Plugin Integration for GitHub Actions

## Overview

This integration allows you to use your Claude plugin with agents/commands/skills in GitHub Actions while enabling actual file system operations.

## Architecture

```
Your Claude Plugin (Agents/Commands/Skills)
           ↓
    Claude Agent Wrapper
           ↓
    File System Bridge
           ↓
    Git Operations
           ↓
    GitHub Actions
```

## How It Works

1. **Your Claude Plugin** generates text responses with instructions
2. **Claude Agent Wrapper** parses these responses for specific patterns
3. **File System Bridge** executes actual file operations
4. **Git Operations** commits and pushes changes
5. **GitHub Actions** creates PRs for review

## Setting Up Your Plugin

### Option 1: Plugin in Same Repository

Place your plugin code in `claude-plugin/` directory:

```
claude-plugin/
├── __init__.py
├── agents/
│   ├── devops_agent.py
│   ├── coder_agent.py
│   └── reviewer_agent.py
├── commands/
│   ├── fix_command.py
│   ├── implement_command.py
│   └── deploy_command.py
├── skills/
│   ├── refactoring.py
│   ├── testing.py
│   └── optimization.py
└── config.yaml
```

### Option 2: External Plugin Package

Install from PyPI or GitHub:

```python
# In the workflow
pip install your-claude-plugin
# or
pip install git+https://github.com/your-org/claude-plugin.git
```

## Response Format for File Operations

Your Claude agents should return responses in this format:

### File Editing
```
FILE_EDIT: path/to/file.py
```python
# Complete updated file content
def function():
    return "updated"
```
```

### File Creation
```
FILE_CREATE: path/to/newfile.py
```python
# Complete new file content
class NewClass:
    pass
```
```

### File Deletion
```
FILE_DELETE: path/to/oldfile.py
```

### Shell Commands
```
SHELL_CMD:
```bash
npm install package-name
```
```

## Agent Command Examples

### Basic Commands
```bash
# Fix a bug
@coder fix-bug "TypeError in auth.py line 45"

# Implement feature
@coder implement "Add OAuth2 authentication"

# Deploy configuration
@devops deploy "Setup Kubernetes deployment"

# Code review
@reviewer analyze "Check for security vulnerabilities"
```

### With Context
```bash
# Specify files
@coder refactor "Improve performance" --files "api/handlers.py api/models.py"

# With detailed context
@devops configure "Setup Redis caching" --context "High traffic API endpoints"
```

## Custom Agent Definition

```python
# claude-plugin/agents/custom_agent.py

class CustomAgent:
    def __init__(self):
        self.name = "@custom"
        self.skills = ["analyze", "optimize", "document"]
        self.model = "claude-3-haiku-20240307"
        
    def execute(self, skill, context, files=None):
        """Execute agent skill"""
        prompt = self.build_prompt(skill, context, files)
        response = self.call_claude(prompt)
        return self.format_response(response)
        
    def format_response(self, response):
        """Format response with file operation markers"""
        formatted = ""
        
        for change in response.changes:
            if change.type == "edit":
                formatted += f"FILE_EDIT: {change.file}\n"
                formatted += f"```{change.language}\n"
                formatted += change.content
                formatted += "\n```\n\n"
            elif change.type == "create":
                formatted += f"FILE_CREATE: {change.file}\n"
                formatted += f"```{change.language}\n"
                formatted += change.content
                formatted += "\n```\n\n"
                
        return formatted
```

## Workflow Configuration

### Basic Setup

```yaml
name: Claude Agent Development

on:
  workflow_dispatch:
    inputs:
      agent_command:
        description: 'e.g., @coder fix-bug "auth issue"'
        required: true
```

### Environment Variables

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.CLAUDE_API_KEY }}
  # Optional: for custom plugin configuration
  PLUGIN_CONFIG: ${{ secrets.PLUGIN_CONFIG }}
  PLUGIN_API_KEYS: ${{ secrets.PLUGIN_API_KEYS }}
```

## Advanced Integration

### 1. Plugin with Multiple Models

```python
class MultiModelAgent:
    def __init__(self):
        self.models = {
            "quick": "claude-3-haiku-20240307",
            "balanced": "claude-3-sonnet-20240229",
            "powerful": "claude-3-opus-20240229"
        }
        
    def select_model(self, task_complexity):
        if task_complexity < 3:
            return self.models["quick"]
        elif task_complexity < 7:
            return self.models["balanced"]
        else:
            return self.models["powerful"]
```

### 2. Chain of Agents

```python
class AgentChain:
    def execute_chain(self, task):
        # Step 1: Analyzer agent
        analysis = self.analyzer.analyze(task)
        
        # Step 2: Coder agent
        code = self.coder.implement(analysis)
        
        # Step 3: Reviewer agent
        review = self.reviewer.review(code)
        
        # Step 4: Apply fixes
        final = self.coder.apply_review(code, review)
        
        return final
```

### 3. Custom Skills

```python
class CustomSkill:
    @staticmethod
    def database_migration(context):
        """Generate database migration files"""
        return f"""
        FILE_CREATE: migrations/001_initial.sql
        ```sql
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE
        );
        ```
        
        FILE_CREATE: migrations/002_add_timestamps.sql
        ```sql
        ALTER TABLE users
        ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
        ```
        """
```

## Testing Your Integration

### Local Testing

```bash
# Test your wrapper locally
export ANTHROPIC_API_KEY="your-key"
export AGENT_COMMAND="@coder fix-bug"
export CONTEXT="Fix authentication error"
export TARGET_FILES="auth.py"

python claude_agent_wrapper.py
```

### GitHub Actions Testing

1. Fork the repository
2. Add your API key to secrets
3. Run workflow manually from Actions tab
4. Review the created PR

## Best Practices

1. **Clear Response Formats**: Ensure your agents return properly formatted responses
2. **Atomic Changes**: Each agent execution should be a complete, working change
3. **Error Handling**: Include try-catch blocks in your wrapper
4. **Testing**: Always test locally before deploying to GitHub Actions
5. **Review PRs**: Never auto-merge without review

## Troubleshooting

### Agent Not Found
```python
# Add fallback in wrapper
if agent not in self.agents:
    print(f"Unknown agent: {agent}, using default")
    agent = "@coder"
```

### File Parsing Issues
```python
# Use more specific patterns
pattern = r'FILE_EDIT:\s*([^\n]+)\n```(?:python|py)?\n(.*?)```'
```

### Git Conflicts
```bash
# In workflow, always create new branch
git checkout -b agent-changes-$(date +%s)
```

## Examples of Agent Commands

```bash
# Bug fixing
@coder fix-bug "TypeError: cannot read property 'id' of undefined"

# Feature implementation
@coder implement "Add user profile page with edit functionality"

# Refactoring
@coder refactor "Convert callbacks to async/await pattern"

# Testing
@tester add-tests "Create unit tests for UserService class"

# Documentation
@docs document "Add JSDoc comments to all public methods"

# Deployment
@devops deploy "Create Docker configuration for production"

# Security
@security audit "Check for SQL injection vulnerabilities"

# Performance
@optimizer improve "Optimize database queries in reporting module"
```

## Security Considerations

1. **API Keys**: Always use GitHub Secrets
2. **Code Review**: Review all AI-generated changes
3. **Permissions**: Limit repository permissions
4. **Validation**: Validate agent responses before applying
5. **Sandboxing**: Consider running in isolated environments

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review workflow logs in GitHub Actions
3. Test locally with verbose output
4. Ensure response format matches expected patterns
