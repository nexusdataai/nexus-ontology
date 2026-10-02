"""
Claude Plugin Adapter for GitHub Actions
This adapter bridges your existing Claude plugin with file system operations
"""

import os
import sys
import json
import re
import importlib
from typing import Dict, List, Any, Optional
from pathlib import Path

class ClaudePluginAdapter:
    """
    Adapter to use your existing Claude plugin in GitHub Actions
    with actual file system operations
    """
    
    def __init__(self, plugin_path: str = None):
        """
        Initialize the adapter with your plugin
        
        Args:
            plugin_path: Path to your Claude plugin module
        """
        self.plugin = None
        self.agents = {}
        self.commands = {}
        self.skills = {}
        
        if plugin_path:
            self.load_plugin(plugin_path)
        else:
            self.load_default_plugin()
    
    def load_plugin(self, plugin_path: str):
        """Load your existing Claude plugin"""
        try:
            # Add plugin path to Python path
            sys.path.insert(0, plugin_path)
            
            # Try to import the main plugin module
            # Adjust these imports based on your plugin structure
            try:
                # Option 1: Plugin with main entry point
                plugin_module = importlib.import_module('claude_plugin')
                self.plugin = plugin_module
                
                # Load agents if available
                if hasattr(plugin_module, 'agents'):
                    self.agents = plugin_module.agents
                
                # Load commands if available
                if hasattr(plugin_module, 'commands'):
                    self.commands = plugin_module.commands
                    
                # Load skills if available
                if hasattr(plugin_module, 'skills'):
                    self.skills = plugin_module.skills
                    
            except ImportError:
                # Option 2: Try loading individual components
                try:
                    from agents import DevOpsAgent, CoderAgent, ReviewerAgent
                    self.agents = {
                        '@devops': DevOpsAgent(),
                        '@coder': CoderAgent(),
                        '@reviewer': ReviewerAgent()
                    }
                except ImportError:
                    pass
                
                try:
                    from commands import load_commands
                    self.commands = load_commands()
                except ImportError:
                    pass
                    
                try:
                    from skills import load_skills
                    self.skills = load_skills()
                except ImportError:
                    pass
                    
            print(f"Plugin loaded from {plugin_path}")
            print(f"Agents: {list(self.agents.keys())}")
            print(f"Commands: {list(self.commands.keys())}")
            print(f"Skills: {list(self.skills.keys())}")
            
        except Exception as e:
            print(f"Error loading plugin: {e}")
            self.load_default_plugin()
    
    def load_default_plugin(self):
        """Load default plugin configuration if custom plugin not found"""
        print("Loading default plugin configuration...")
        
        # Default agents
        self.agents = {
            '@devops': {
                'name': 'DevOps Agent',
                'skills': ['deploy', 'configure', 'monitor', 'scale'],
                'model': 'claude-3-haiku-20240307'
            },
            '@coder': {
                'name': 'Coder Agent',
                'skills': ['implement', 'fix-bug', 'refactor', 'optimize'],
                'model': 'claude-3-sonnet-20240229'
            },
            '@reviewer': {
                'name': 'Reviewer Agent',
                'skills': ['review', 'analyze', 'suggest', 'validate'],
                'model': 'claude-3-haiku-20240307'
            },
            '@tester': {
                'name': 'Tester Agent',
                'skills': ['add-tests', 'test', 'coverage', 'integration-test'],
                'model': 'claude-3-haiku-20240307'
            },
            '@docs': {
                'name': 'Documentation Agent',
                'skills': ['document', 'api-docs', 'readme', 'comments'],
                'model': 'claude-3-haiku-20240307'
            }
        }
        
        # Default commands
        self.commands = {
            'fix': self.fix_command,
            'implement': self.implement_command,
            'deploy': self.deploy_command,
            'test': self.test_command,
            'document': self.document_command
        }
        
        # Default skills
        self.skills = {
            'refactor': self.refactor_skill,
            'optimize': self.optimize_skill,
            'secure': self.secure_skill,
            'migrate': self.migrate_skill
        }
    
    def execute_plugin_command(self, command: str, context: str = "", files: List[str] = None) -> str:
        """
        Execute a command from your Claude plugin
        
        Args:
            command: The plugin command (e.g., "@coder fix-bug")
            context: Additional context
            files: Target files
            
        Returns:
            Response string with file operation markers
        """
        
        # Parse the command
        agent_name, skill, command_context = self.parse_command(command)
        
        # Check if we have a specific agent handler
        if agent_name in self.agents:
            agent = self.agents[agent_name]
            
            # If agent is an object with execute method
            if hasattr(agent, 'execute'):
                response = agent.execute(skill, context, files)
            # If agent is a dictionary configuration
            elif isinstance(agent, dict):
                response = self.execute_agent_dict(agent, skill, context, files)
            else:
                response = self.fallback_execution(agent_name, skill, context, files)
        else:
            response = self.fallback_execution(agent_name, skill, context, files)
            
        # Convert response to file operation format if needed
        return self.format_response_for_file_ops(response)
    
    def parse_command(self, command: str) -> tuple:
        """Parse command into agent, skill, and context"""
        parts = command.split(maxsplit=2)
        agent = parts[0] if parts else ""
        skill = parts[1] if len(parts) > 1 else ""
        context = parts[2] if len(parts) > 2 else ""
        return agent, skill, context
    
    def execute_agent_dict(self, agent: Dict, skill: str, context: str, files: List[str]) -> str:
        """Execute agent from dictionary configuration"""
        # This is where you'd integrate with your actual Claude API calls
        # For now, returning a formatted response
        return f"""
        Agent: {agent['name']}
        Skill: {skill}
        Context: {context}
        Files: {files}
        
        # Simulated response - replace with actual plugin logic
        FILE_EDIT: {files[0] if files else 'main.py'}
        ```python
        # Code generated by {agent['name']}
        def generated_function():
            pass
        ```
        """
    
    def format_response_for_file_ops(self, response: str) -> str:
        """
        Convert plugin response to file operation format
        
        Your plugin might return responses in different formats.
        This method converts them to the standard format:
        - FILE_EDIT: filename
        - FILE_CREATE: filename
        - FILE_DELETE: filename
        - SHELL_CMD: command
        """
        
        # If response already contains file operation markers, return as is
        if any(marker in response for marker in ['FILE_EDIT:', 'FILE_CREATE:', 'FILE_DELETE:', 'SHELL_CMD:']):
            return response
        
        # Try to detect and format common response patterns
        formatted = ""
        
        # Pattern 1: Code blocks with filenames
        code_block_pattern = r'```(\w+)?\s*#?\s*([^\n]+\.\w+)\n(.*?)```'
        for match in re.finditer(code_block_pattern, response, re.DOTALL):
            lang, filename, code = match.groups()
            formatted += f"FILE_EDIT: {filename}\n```{lang or ''}\n{code}```\n\n"
        
        # Pattern 2: Direct file references
        file_ref_pattern = r'(?:File|file|FILE):\s*([^\n]+\.\w+)\n'
        for match in re.finditer(file_ref_pattern, response):
            filename = match.group(1)
            # Look for code after the file reference
            code_after = response[match.end():].split('\n\n')[0]
            if code_after:
                formatted += f"FILE_EDIT: {filename}\n```\n{code_after}\n```\n\n"
        
        # If no patterns matched, return original response with a note
        if not formatted:
            formatted = f"# Original plugin response (no file operations detected):\n{response}"
        
        return formatted
    
    def fallback_execution(self, agent: str, skill: str, context: str, files: List[str]) -> str:
        """Fallback execution when agent not found"""
        return f"""
        # Fallback execution for {agent} {skill}
        # Context: {context}
        # Files: {files}
        
        # No specific handler found for this agent/skill combination.
        # Using default response format.
        
        FILE_EDIT: {files[0] if files else 'main.py'}
        ```python
        # TODO: Implement {skill} for {context}
        pass
        ```
        """
    
    # Default command implementations
    def fix_command(self, context: str, files: List[str]) -> str:
        """Default fix command implementation"""
        return f"""
        FILE_EDIT: {files[0] if files else 'main.py'}
        ```python
        # Bug fix for: {context}
        # Fixed implementation here
        ```
        """
    
    def implement_command(self, context: str, files: List[str]) -> str:
        """Default implement command implementation"""
        return f"""
        FILE_CREATE: {files[0] if files else 'new_feature.py'}
        ```python
        # Implementation for: {context}
        class NewFeature:
            def __init__(self):
                pass
        ```
        """
    
    def deploy_command(self, context: str, files: List[str]) -> str:
        """Default deploy command implementation"""
        return f"""
        FILE_CREATE: Dockerfile
        ```dockerfile
        FROM python:3.11-slim
        WORKDIR /app
        COPY . .
        RUN pip install -r requirements.txt
        CMD ["python", "main.py"]
        ```
        
        FILE_CREATE: docker-compose.yml
        ```yaml
        version: '3.8'
        services:
          app:
            build: .
            ports:
              - "8000:8000"
        ```
        """
    
    def test_command(self, context: str, files: List[str]) -> str:
        """Default test command implementation"""
        return f"""
        FILE_CREATE: test_{files[0] if files else 'main.py'}
        ```python
        import unittest
        
        class TestMain(unittest.TestCase):
            def test_example(self):
                self.assertTrue(True)
        
        if __name__ == '__main__':
            unittest.main()
        ```
        """
    
    def document_command(self, context: str, files: List[str]) -> str:
        """Default document command implementation"""
        return f"""
        FILE_EDIT: {files[0] if files else 'main.py'}
        ```python
        \"\"\"
        Module documentation for {context}
        
        This module provides...
        \"\"\"
        
        # Existing code with added docstrings
        ```
        """
    
    # Default skill implementations
    def refactor_skill(self, context: str, files: List[str]) -> str:
        """Default refactor skill"""
        return f"FILE_EDIT: {files[0] if files else 'main.py'}\n```python\n# Refactored code\n```"
    
    def optimize_skill(self, context: str, files: List[str]) -> str:
        """Default optimize skill"""
        return f"FILE_EDIT: {files[0] if files else 'main.py'}\n```python\n# Optimized code\n```"
    
    def secure_skill(self, context: str, files: List[str]) -> str:
        """Default secure skill"""
        return f"FILE_EDIT: {files[0] if files else 'main.py'}\n```python\n# Security improvements\n```"
    
    def migrate_skill(self, context: str, files: List[str]) -> str:
        """Default migrate skill"""
        return f"FILE_CREATE: migrations/001_migration.sql\n```sql\n-- Migration SQL\n```"


def integrate_with_github_action():
    """Main function to integrate plugin with GitHub Actions"""
    
    # Get environment variables
    command = os.environ.get('AGENT_COMMAND', '')
    context = os.environ.get('CONTEXT', '')
    target_files = os.environ.get('TARGET_FILES', '').split()
    plugin_path = os.environ.get('PLUGIN_PATH', 'claude-plugin')
    
    print(f"Integrating Claude Plugin from: {plugin_path}")
    print(f"Command: {command}")
    print(f"Context: {context}")
    print(f"Files: {target_files}")
    
    # Initialize adapter
    adapter = ClaudePluginAdapter(plugin_path if os.path.exists(plugin_path) else None)
    
    # Execute plugin command
    response = adapter.execute_plugin_command(command, context, target_files)
    
    print("\n=== Plugin Response ===")
    print(response)
    
    return response


if __name__ == "__main__":
    integrate_with_github_action()
