#!/usr/bin/env python3
"""
Comprehensive MCP Diagnostics Tool
==================================

This script helps diagnose and troubleshoot MCP (Model Context Protocol) stdio issues,
tool problems, and ensures MCP tools work reliably from local Cursor IDE.

Features:
- Environment validation
- MCP server connectivity tests
- Tool registration verification
- Database connectivity checks
- Process management utilities
- Configuration validation
- Performance testing
- Automated fixes for common issues

Usage:
    python3 mcp_diagnostics.py [--fix] [--verbose] [--test-tools]
"""

import os
import sys
import json
import asyncio
import subprocess
import time
import signal
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import argparse
import traceback

# Add project to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from src.services.ecommerce_service import EcommerceService
    from src.models.ecommerce_models import ProductBrowseRequest, CategoryCountsRequest
    ECOMMERCE_SERVICE_AVAILABLE = True
except ImportError:
    ECOMMERCE_SERVICE_AVAILABLE = False

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class MCPDiagnostics:
    """Comprehensive MCP diagnostics and troubleshooting tool"""
    
    def __init__(self, verbose: bool = False, auto_fix: bool = False):
        self.verbose = verbose
        self.auto_fix = auto_fix
        # Project root is parent directory since we're in diag/
        self.project_root = Path(__file__).parent.parent
        self.issues_found = []
        self.fixes_applied = []
        self.available_tools = []
        self.tool_test_results = {}
        
    def log(self, message: str, level: str = "INFO", color: str = Colors.WHITE):
        """Log message with color and timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_colors = {
            "INFO": Colors.BLUE,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "DEBUG": Colors.PURPLE
        }
        level_color = level_colors.get(level, Colors.WHITE)
        
        if level != "DEBUG" or self.verbose:
            print(f"{Colors.BOLD}[{timestamp}]{Colors.END} {level_color}[{level}]{Colors.END} {color}{message}{Colors.END}")
    
    def get_python_executable(self) -> str:
        """Get the appropriate Python executable (virtual env if available)"""
        venv_python = self.project_root / ".venv" / "bin" / "python"
        if venv_python.exists():
            return str(venv_python)
        return "python3"
    
    def run_command(self, cmd: str, timeout: int = 30, use_venv: bool = True) -> Dict[str, Any]:
        """Run shell command and return result"""
        try:
            # Replace python3 with venv python if requested and available
            if use_venv and "python3" in cmd:
                python_exec = self.get_python_executable()
                cmd = cmd.replace("python3", python_exec)
            
            self.log(f"Running: {cmd}", "DEBUG")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout,
                cwd=str(self.project_root)
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def check_environment(self) -> bool:
        """Check environment setup and dependencies"""
        self.log("🔍 Checking Environment Setup", "INFO", Colors.CYAN)
        all_good = True
        
        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.log(f"✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}", "SUCCESS")
        else:
            self.log(f"❌ Python version too old: {python_version.major}.{python_version.minor}.{python_version.micro} (need >= 3.8)", "ERROR")
            all_good = False
        
        # Check project structure
        required_files = [
            "mcp_stdio_server.py",
            "mcp-config.json",
            "src/services/ecommerce_service.py",
            "src/models/ecommerce_models.py",
            "src/tools/ecommerce_tools.py"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.log(f"✅ Found: {file_path}", "SUCCESS")
            else:
                self.log(f"❌ Missing: {file_path}", "ERROR")
                all_good = False
        
        # Check dependencies
        try:
            import boto3
            self.log("✅ boto3 available", "SUCCESS")
        except ImportError:
            self.log("❌ boto3 not available", "ERROR")
            all_good = False
        
        try:
            import loguru
            self.log("✅ loguru available", "SUCCESS")
        except ImportError:
            self.log("❌ loguru not available", "ERROR")
            all_good = False
        
        # Check uv installation
        uv_result = self.run_command("uv --version")
        if uv_result["success"]:
            self.log(f"✅ uv available: {uv_result['stdout']}", "SUCCESS")
        else:
            self.log("❌ uv not available", "ERROR")
            all_good = False
        
        return all_good
    
    def check_aws_credentials(self) -> bool:
        """Check AWS credentials and DynamoDB access"""
        self.log("🔍 Checking AWS Configuration", "INFO", Colors.CYAN)
        
        if not BOTO3_AVAILABLE:
            self.log("❌ boto3 not available, skipping AWS checks", "ERROR")
            return False
        
        try:
            # Check credentials
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is None:
                self.log("❌ No AWS credentials found", "ERROR")
                return False
            
            self.log("✅ AWS credentials found", "SUCCESS")
            
            # Check region - prioritize ap-south-1 as that's where our tables are
            region = os.getenv('AWS_REGION', 'ap-south-1')
            self.log(f"✅ AWS region: {region}", "SUCCESS")
            
            # Test DynamoDB access
            dynamodb = boto3.resource('dynamodb', region_name=region)
            
            # Check if required tables exist
            required_tables = ['AuroraSparkTheme-Products', 'AuroraSparkTheme-Inventory']
            for table_name in required_tables:
                try:
                    table = dynamodb.Table(table_name)
                    table.load()  # This will raise an exception if table doesn't exist
                    self.log(f"✅ DynamoDB table exists: {table_name}", "SUCCESS")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        self.log(f"❌ DynamoDB table not found: {table_name}", "ERROR")
                        return False
                    else:
                        self.log(f"❌ Error accessing table {table_name}: {e}", "ERROR")
                        return False
            
            return True
            
        except NoCredentialsError:
            self.log("❌ AWS credentials not configured", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ AWS configuration error: {e}", "ERROR")
            return False
    
    def check_mcp_config(self) -> bool:
        """Check MCP configuration file"""
        self.log("🔍 Checking MCP Configuration", "INFO", Colors.CYAN)
        
        config_file = self.project_root / "mcp-config.json"
        if not config_file.exists():
            self.log("❌ mcp-config.json not found", "ERROR")
            return False
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.log("✅ mcp-config.json is valid JSON", "SUCCESS")
            
            # Check structure
            if "mcpServers" not in config:
                self.log("❌ Missing 'mcpServers' in config", "ERROR")
                return False
            
            if "ecommerce-catalog" not in config["mcpServers"]:
                self.log("❌ Missing 'ecommerce-catalog' server config", "ERROR")
                return False
            
            server_config = config["mcpServers"]["ecommerce-catalog"]
            
            # Check required fields
            required_fields = ["command", "args", "cwd"]
            for field in required_fields:
                if field not in server_config:
                    self.log(f"❌ Missing '{field}' in server config", "ERROR")
                    return False
                else:
                    self.log(f"✅ Found '{field}': {server_config[field]}", "SUCCESS")
            
            # Check environment variables
            if "env" in server_config:
                env_vars = server_config["env"]
                important_vars = ["PYTHONPATH", "AWS_REGION"]
                for var in important_vars:
                    if var in env_vars:
                        self.log(f"✅ Environment variable '{var}': {env_vars[var]}", "SUCCESS")
                    else:
                        self.log(f"⚠️ Missing environment variable '{var}'", "WARNING")
            
            return True
            
        except json.JSONDecodeError as e:
            self.log(f"❌ Invalid JSON in mcp-config.json: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"❌ Error reading config: {e}", "ERROR")
            return False
    
    def get_mcp_processes(self) -> List[Dict[str, Any]]:
        """Get list of running MCP server processes"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and any('mcp_stdio_server.py' in arg for arg in cmdline):
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cmdline': ' '.join(cmdline),
                        'create_time': proc.info['create_time'],
                        'age_seconds': time.time() - proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes
    
    def check_mcp_processes(self) -> bool:
        """Check MCP server processes"""
        self.log("🔍 Checking MCP Server Processes", "INFO", Colors.CYAN)
        
        processes = self.get_mcp_processes()
        
        if not processes:
            self.log("⚠️ No MCP server processes found", "WARNING")
            return False
        
        for proc in processes:
            age_minutes = proc['age_seconds'] / 60
            self.log(f"✅ MCP process found: PID {proc['pid']}, age: {age_minutes:.1f}min", "SUCCESS")
            if self.verbose:
                self.log(f"   Command: {proc['cmdline']}", "DEBUG")
        
        # Check for zombie or stuck processes
        if len(processes) > 3:
            self.log(f"⚠️ Many MCP processes running ({len(processes)}), might need cleanup", "WARNING")
            self.issues_found.append("too_many_mcp_processes")
        
        return True
    
    def test_mcp_stdio_communication(self) -> bool:
        """Test MCP stdio communication directly"""
        self.log("🔍 Testing MCP Stdio Communication", "INFO", Colors.CYAN)
        
        try:
            # Test tools/list
            list_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
            
            cmd = f'echo \'{json.dumps(list_request)}\' | python3 mcp_stdio_server.py'
            result = self.run_command(cmd, timeout=15)
            
            if not result["success"]:
                self.log(f"❌ MCP stdio communication failed: {result['stderr']}", "ERROR")
                return False
            
            try:
                response = json.loads(result["stdout"].split('\n')[-1])  # Get last line (JSON response)
                if "result" in response and "tools" in response["result"]:
                    tools = response["result"]["tools"]
                    self.log(f"✅ MCP stdio communication working, {len(tools)} tools found", "SUCCESS")
                    
                    # Store tools for detailed analysis
                    self.available_tools = tools
                    
                    for tool in tools:
                        self.log(f"   📦 Tool: {tool['name']}", "SUCCESS")
                    
                    return True
                else:
                    self.log("❌ Invalid MCP response format", "ERROR")
                    return False
                    
            except json.JSONDecodeError:
                self.log("❌ Invalid JSON response from MCP server", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ MCP stdio test failed: {e}", "ERROR")
            return False
    
    def analyze_tool_schema(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze tool schema for potential issues"""
        analysis = {
            "name": tool.get("name", "unknown"),
            "has_description": bool(tool.get("description")),
            "has_schema": bool(tool.get("inputSchema")),
            "schema_issues": [],
            "parameter_count": 0,
            "required_params": 0,
            "optional_params": 0,
            "parameter_types": {},
            "complexity_score": 0
        }
        
        if tool.get("inputSchema"):
            schema = tool["inputSchema"]
            if "properties" in schema:
                properties = schema["properties"]
                analysis["parameter_count"] = len(properties)
                
                required = schema.get("required", [])
                analysis["required_params"] = len(required)
                analysis["optional_params"] = analysis["parameter_count"] - analysis["required_params"]
                
                # Analyze parameter types
                for param_name, param_def in properties.items():
                    param_type = param_def.get("type", "unknown")
                    analysis["parameter_types"][param_name] = {
                        "type": param_type,
                        "required": param_name in required,
                        "has_description": bool(param_def.get("description")),
                        "has_default": "default" in param_def
                    }
                
                # Calculate complexity score
                analysis["complexity_score"] = (
                    analysis["parameter_count"] * 2 +
                    analysis["required_params"] * 3 +
                    len([p for p in properties.values() if p.get("type") == "object"]) * 5
                )
            else:
                analysis["schema_issues"].append("No properties defined in schema")
        else:
            analysis["schema_issues"].append("No input schema defined")
        
        return analysis

    def test_cursor_like_tool_execution(self) -> bool:
        """Test tools exactly like Cursor would, with comprehensive analysis"""
        self.log("🔍 Cursor-Style Tool Analysis & Testing", "INFO", Colors.CYAN)
        
        if not self.available_tools:
            self.log("❌ No tools available for testing", "ERROR")
            return False
        
        all_tools_working = True
        
        for i, tool in enumerate(self.available_tools, 1):
            tool_name = tool.get("name", f"tool-{i}")
            self.log(f"\n📋 Analyzing Tool {i}/{len(self.available_tools)}: {tool_name}", "INFO", Colors.BOLD)
            
            # Analyze tool schema
            analysis = self.analyze_tool_schema(tool)
            self.tool_test_results[tool_name] = analysis
            
            # Report schema analysis
            if analysis["has_description"]:
                desc = tool.get("description", "")[:100] + ("..." if len(tool.get("description", "")) > 100 else "")
                self.log(f"   📝 Description: {desc}", "SUCCESS")
            else:
                self.log("   ⚠️ No description provided", "WARNING")
                analysis["schema_issues"].append("Missing description")
            
            if analysis["has_schema"]:
                self.log(f"   📊 Parameters: {analysis['parameter_count']} total "
                        f"({analysis['required_params']} required, {analysis['optional_params']} optional)", "SUCCESS")
                
                # Show parameter details
                for param_name, param_info in analysis["parameter_types"].items():
                    status = "✅" if param_info["has_description"] else "⚠️"
                    req_str = "required" if param_info["required"] else "optional"
                    default_str = f" (default: {tool['inputSchema']['properties'][param_name].get('default')})" if param_info["has_default"] else ""
                    self.log(f"     {status} {param_name}: {param_info['type']} ({req_str}){default_str}", "DEBUG")
                
                complexity = "Low" if analysis["complexity_score"] < 10 else "Medium" if analysis["complexity_score"] < 20 else "High"
                self.log(f"   🎯 Complexity: {complexity} (score: {analysis['complexity_score']})", "INFO")
            else:
                self.log("   ❌ No input schema defined", "ERROR")
                analysis["schema_issues"].append("Missing input schema")
            
            # Test tool execution with different scenarios
            tool_working = self.test_individual_tool(tool_name, tool, analysis)
            if not tool_working:
                all_tools_working = False
            
            # Report issues
            if analysis["schema_issues"]:
                self.log(f"   ⚠️ Schema Issues: {', '.join(analysis['schema_issues'])}", "WARNING")
        
        return all_tools_working

    def test_individual_tool(self, tool_name: str, tool: Dict[str, Any], analysis: Dict[str, Any]) -> bool:
        """Test individual tool with various parameter combinations"""
        self.log(f"   🧪 Testing {tool_name} execution...", "INFO")
        
        test_scenarios = self.generate_test_scenarios(tool, analysis)
        tool_working = True
        
        for scenario_name, test_args in test_scenarios.items():
            self.log(f"     🔬 Scenario: {scenario_name}", "DEBUG")
            
            success, response_data, error_msg = self.execute_tool_call(tool_name, test_args)
            
            if success:
                self.log(f"     ✅ {scenario_name}: Success", "SUCCESS")
                
                # Analyze response structure
                if response_data:
                    self.analyze_tool_response(tool_name, scenario_name, response_data)
            else:
                self.log(f"     ❌ {scenario_name}: {error_msg}", "ERROR")
                tool_working = False
                
                # Store detailed error info
                if tool_name not in self.tool_test_results:
                    self.tool_test_results[tool_name] = {}
                if "errors" not in self.tool_test_results[tool_name]:
                    self.tool_test_results[tool_name]["errors"] = {}
                self.tool_test_results[tool_name]["errors"][scenario_name] = error_msg
        
        return tool_working

    def generate_test_scenarios(self, tool: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Dict]:
        """Generate test scenarios based on tool schema"""
        scenarios = {}
        tool_name = tool.get("name", "")
        
        # Scenario 1: Minimal required parameters only
        if analysis["required_params"] == 0:
            scenarios["minimal"] = {}
        else:
            minimal_args = {}
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for param in required:
                if param in properties:
                    param_type = properties[param].get("type", "string")
                    minimal_args[param] = self.get_default_value_for_type(param_type, param)
            
            scenarios["minimal"] = minimal_args
        
        # Scenario 2: Typical usage (based on tool name)
        if tool_name == "browse-products":
            scenarios["typical"] = {"max_results": 5}
            scenarios["with_category"] = {"category": "fruits", "max_results": 3}
            scenarios["with_search"] = {"search_term": "apple", "max_results": 2}
            scenarios["price_filter"] = {"min_price": 10, "max_price": 100, "max_results": 5}
        elif tool_name == "get-category-counts":
            scenarios["typical"] = {}
        elif tool_name == "deliver-order":
            scenarios["successful_delivery"] = {
                "order_id": "test-order-successful",
                "delivery_status": "successful", 
                "customer_verified": True,
                "payment_collected": True,
                "signature_obtained": True,
                "photo_taken": True
            }
            scenarios["failed_delivery"] = {
                "order_id": "test-order-failed",
                "delivery_status": "failed",
                "customer_verified": False,
                "failure_reason": "Customer not available at address"
            }
        elif tool_name == "get-delivery-status":
            scenarios["typical"] = {"order_id": "test-order-status-check"}
        else:
            # Generic typical scenario
            typical_args = {}
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})
            
            for param_name, param_def in properties.items():
                if param_def.get("default") is not None:
                    typical_args[param_name] = param_def["default"]
                elif param_name in ["max_results", "limit", "count"]:
                    typical_args[param_name] = 5
                elif param_name in ["search", "query", "term"]:
                    typical_args[param_name] = "test"
            
            scenarios["typical"] = typical_args
        
        # Scenario 3: Edge cases
        if "max_results" in analysis["parameter_types"]:
            scenarios["edge_max_results"] = {"max_results": 1}
            scenarios["large_results"] = {"max_results": 50}
        
        return scenarios

    def get_default_value_for_type(self, param_type: str, param_name: str) -> Any:
        """Get appropriate default value for parameter type"""
        if param_type == "string":
            if "search" in param_name.lower() or "term" in param_name.lower():
                return "test"
            elif "category" in param_name.lower():
                return "fruits"
            return "test"
        elif param_type == "integer" or param_type == "number":
            if "max" in param_name.lower() or "limit" in param_name.lower():
                return 5
            elif "min" in param_name.lower():
                return 1
            elif "price" in param_name.lower():
                return 10
            return 1
        elif param_type == "boolean":
            return True
        elif param_type == "array":
            return []
        elif param_type == "object":
            return {}
        else:
            return None

    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> tuple:
        """Execute a tool call and return success, response_data, error_msg"""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            cmd = f'echo \'{json.dumps(request)}\' | python3 mcp_stdio_server.py'
            result = self.run_command(cmd, timeout=30)
            
            if not result["success"]:
                return False, None, f"Command failed: {result['stderr']}"
            
            try:
                response = json.loads(result["stdout"].split('\n')[-1])
                
                if "error" in response:
                    return False, None, f"JSON-RPC error: {response['error']}"
                
                if "result" in response:
                    result_data = response["result"]
                    
                    if isinstance(result_data, dict) and result_data.get("isError"):
                        error_content = result_data.get("content", [])
                        error_msg = error_content[0].get("text", "Unknown error") if error_content else "Unknown error"
                        return False, None, f"Tool error: {error_msg}"
                    
                    # Extract actual data from MCP response format
                    if isinstance(result_data, dict) and "content" in result_data:
                        content = result_data["content"]
                        if content and isinstance(content, list) and len(content) > 0:
                            text_content = content[0].get("text", "")
                            if text_content:
                                try:
                                    # Try to parse as JSON
                                    actual_data = json.loads(text_content)
                                    return True, actual_data, None
                                except json.JSONDecodeError:
                                    return True, {"raw_text": text_content}, None
                    
                    return True, result_data, None
                else:
                    return False, None, "No result in response"
                    
            except json.JSONDecodeError as e:
                return False, None, f"Invalid JSON response: {e}"
                
        except Exception as e:
            return False, None, f"Execution failed: {e}"

    def analyze_tool_response(self, tool_name: str, scenario: str, response_data: Dict[str, Any]):
        """Analyze tool response structure and content"""
        if tool_name not in self.tool_test_results:
            self.tool_test_results[tool_name] = {}
        if "responses" not in self.tool_test_results[tool_name]:
            self.tool_test_results[tool_name]["responses"] = {}
        
        response_analysis = {
            "has_data": bool(response_data),
            "data_type": type(response_data).__name__,
            "keys": list(response_data.keys()) if isinstance(response_data, dict) else [],
            "data_size": len(response_data) if hasattr(response_data, '__len__') else 0
        }
        
        # Tool-specific analysis
        if tool_name == "browse-products" and isinstance(response_data, dict):
            products = response_data.get("products", [])
            response_analysis.update({
                "product_count": len(products),
                "has_search_metadata": "search_metadata" in response_data,
                "has_categories": "categories" in response_data,
                "first_product_keys": list(products[0].keys()) if products else []
            })
            
            if products:
                self.log(f"       📦 Found {len(products)} products", "SUCCESS")
                sample_product = products[0]
                if "name" in sample_product and "price" in sample_product:
                    self.log(f"       🏷️ Sample: {sample_product['name']} - ${sample_product['price']}", "DEBUG")
        
        elif tool_name == "get-category-counts" and isinstance(response_data, dict):
            categories = response_data.get("categories", [])
            total_products = response_data.get("total_products", 0)
            response_analysis.update({
                "category_count": len(categories),
                "total_products": total_products,
                "has_timestamp": "timestamp" in response_data
            })
            
            if categories:
                self.log(f"       📊 Found {len(categories)} categories, {total_products} total products", "SUCCESS")
        
        self.tool_test_results[tool_name]["responses"][scenario] = response_analysis

    def test_tool_execution(self) -> bool:
        """Test actual tool execution (wrapper for new comprehensive testing)"""
        return self.test_cursor_like_tool_execution()
    
    def test_database_service(self) -> bool:
        """Test database service directly"""
        self.log("🔍 Testing Database Service", "INFO", Colors.CYAN)
        
        if not ECOMMERCE_SERVICE_AVAILABLE:
            self.log("❌ E-commerce service not available", "ERROR")
            return False
        
        try:
            async def test_service():
                service = EcommerceService()
                
                # Test category counts
                cat_request = CategoryCountsRequest()
                cat_result = await service.get_category_counts(cat_request)
                
                if cat_result.status == "success":
                    self.log(f"✅ Database service working: {cat_result.total_products} products found", "SUCCESS")
                    return True
                else:
                    self.log(f"❌ Database service error: {cat_result.error_message}", "ERROR")
                    return False
            
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we are, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, test_service())
                    return future.result(timeout=30)
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                return asyncio.run(test_service())
            
        except Exception as e:
            self.log(f"❌ Database service test failed: {e}", "ERROR")
            return False
    
    def cleanup_mcp_processes(self) -> bool:
        """Clean up stuck MCP processes"""
        self.log("🔧 Cleaning up MCP processes", "INFO", Colors.YELLOW)
        
        processes = self.get_mcp_processes()
        
        if not processes:
            self.log("✅ No MCP processes to clean up", "SUCCESS")
            return True
        
        cleaned = 0
        for proc in processes:
            try:
                os.kill(proc['pid'], signal.SIGTERM)
                time.sleep(1)
                # Check if process still exists
                try:
                    os.kill(proc['pid'], 0)  # This will raise OSError if process doesn't exist
                    # Process still exists, force kill
                    os.kill(proc['pid'], signal.SIGKILL)
                except OSError:
                    pass  # Process is gone
                
                self.log(f"✅ Cleaned up MCP process: PID {proc['pid']}", "SUCCESS")
                cleaned += 1
                
            except OSError:
                # Process already gone
                pass
            except Exception as e:
                self.log(f"❌ Failed to clean up PID {proc['pid']}: {e}", "ERROR")
        
        if cleaned > 0:
            self.fixes_applied.append(f"cleaned_up_{cleaned}_mcp_processes")
        
        return True
    
    def fix_common_issues(self) -> bool:
        """Apply fixes for common issues"""
        self.log("🔧 Applying fixes for common issues", "INFO", Colors.YELLOW)
        
        fixes_applied = 0
        
        # Fix 1: Cleanup stuck processes
        if "too_many_mcp_processes" in self.issues_found:
            self.cleanup_mcp_processes()
            fixes_applied += 1
        
        # Fix 2: Ensure correct table names in service
        service_file = self.project_root / "src/services/ecommerce_service.py"
        if service_file.exists():
            content = service_file.read_text()
            if "EcommerceApp-Products" in content:
                self.log("🔧 Updating default table names in service", "INFO", Colors.YELLOW)
                content = content.replace(
                    "os.getenv('PRODUCTS_TABLE_NAME', 'EcommerceApp-Products')",
                    "os.getenv('PRODUCTS_TABLE_NAME', 'AuroraSparkTheme-Products')"
                )
                content = content.replace(
                    "os.getenv('INVENTORY_TABLE_NAME', 'EcommerceApp-Inventory')",
                    "os.getenv('INVENTORY_TABLE_NAME', 'AuroraSparkTheme-Inventory')"
                )
                service_file.write_text(content)
                fixes_applied += 1
                self.fixes_applied.append("updated_default_table_names")
        
        if fixes_applied > 0:
            self.log(f"✅ Applied {fixes_applied} fixes", "SUCCESS")
        else:
            self.log("✅ No fixes needed", "SUCCESS")
        
        return True
    
    def generate_report(self) -> str:
        """Generate diagnostic report"""
        report = []
        report.append("=" * 80)
        report.append("MCP DIAGNOSTICS REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Project: {self.project_root}")
        report.append("")
        
        # Tool Analysis Section
        if self.tool_test_results:
            report.append("CURSOR MCP TOOL ANALYSIS")
            report.append("=" * 40)
            
            for tool_name, analysis in self.tool_test_results.items():
                report.append(f"\n🔧 TOOL: {tool_name}")
                report.append("-" * 30)
                
                # Schema Analysis
                if "parameter_count" in analysis:
                    report.append(f"Parameters: {analysis['parameter_count']} total ({analysis['required_params']} required)")
                    
                    if analysis.get("parameter_types"):
                        report.append("Parameter Details:")
                        for param_name, param_info in analysis["parameter_types"].items():
                            status = "✓" if param_info["has_description"] else "⚠"
                            req = "REQ" if param_info["required"] else "OPT"
                            report.append(f"  {status} {param_name}: {param_info['type']} ({req})")
                    
                    complexity = "Low" if analysis["complexity_score"] < 10 else "Medium" if analysis["complexity_score"] < 20 else "High"
                    report.append(f"Complexity: {complexity} (score: {analysis['complexity_score']})")
                
                # Schema Issues
                if analysis.get("schema_issues"):
                    report.append("Schema Issues:")
                    for issue in analysis["schema_issues"]:
                        report.append(f"  ⚠ {issue}")
                
                # Test Results
                if "responses" in analysis:
                    report.append("Test Scenarios:")
                    for scenario, response_info in analysis["responses"].items():
                        report.append(f"  ✓ {scenario}: {response_info.get('data_type', 'unknown')} response")
                        
                        # Tool-specific details
                        if tool_name == "browse-products" and "product_count" in response_info:
                            report.append(f"    → {response_info['product_count']} products returned")
                        elif tool_name == "get-category-counts" and "total_products" in response_info:
                            report.append(f"    → {response_info['total_products']} total products, {response_info['category_count']} categories")
                
                # Error Details
                if "errors" in analysis:
                    report.append("Errors Found:")
                    for scenario, error in analysis["errors"].items():
                        report.append(f"  ❌ {scenario}: {error}")
                
                report.append("")
            
            # Summary
            working_tools = len([t for t in self.tool_test_results.values() if not t.get("errors")])
            total_tools = len(self.tool_test_results)
            report.append(f"TOOL SUMMARY: {working_tools}/{total_tools} tools working correctly")
            report.append("")
        
        # Issues and Fixes
        if self.issues_found:
            report.append("ISSUES FOUND:")
            for issue in self.issues_found:
                report.append(f"  - {issue}")
            report.append("")
        
        if self.fixes_applied:
            report.append("FIXES APPLIED:")
            for fix in self.fixes_applied:
                report.append(f"  - {fix}")
            report.append("")
        
        # Cursor-specific recommendations
        report.append("CURSOR IDE INTEGRATION:")
        report.append("1. Tools available in Cursor:")
        if self.available_tools:
            for tool in self.available_tools:
                tool_name = tool.get("name", "unknown")
                desc = tool.get("description", "No description")[:60] + "..."
                report.append(f"   • {tool_name}: {desc}")
        else:
            report.append("   • No tools detected")
        
        report.append("")
        report.append("RECOMMENDATIONS:")
        report.append("1. Restart Cursor IDE after running diagnostics")
        report.append("2. Disable/enable MCP server in Cursor settings")
        report.append("3. Check AWS credentials if database tests fail")
        report.append("4. Run this script with --fix flag to auto-fix issues")
        
        if self.tool_test_results:
            problematic_tools = [name for name, data in self.tool_test_results.items() if data.get("errors")]
            if problematic_tools:
                report.append(f"5. Fix issues with tools: {', '.join(problematic_tools)}")
        
        report.append("")
        
        return "\n".join(report)
    
    async def run_full_diagnostics(self, test_tools: bool = True) -> bool:
        """Run complete diagnostics"""
        self.log("🚀 Starting MCP Diagnostics", "INFO", Colors.BOLD + Colors.CYAN)
        self.log(f"Project root: {self.project_root}", "INFO")
        
        all_good = True
        
        # Environment checks
        if not self.check_environment():
            all_good = False
        
        # AWS checks
        if not self.check_aws_credentials():
            all_good = False
        
        # Config checks
        if not self.check_mcp_config():
            all_good = False
        
        # Process checks
        self.check_mcp_processes()
        
        if test_tools:
            # Communication tests
            if not self.test_mcp_stdio_communication():
                all_good = False
            
            # Tool execution tests
            if not self.test_tool_execution():
                all_good = False
            
            # Database service tests
            if not self.test_database_service():
                all_good = False
        
        # Apply fixes if requested
        if self.auto_fix:
            self.fix_common_issues()
        
        # Generate report
        report = self.generate_report()
        
        # Save report to logs/ folder
        logs_dir = self.project_root / "logs"
        logs_dir.mkdir(exist_ok=True)  # Create logs directory if it doesn't exist
        
        report_file = logs_dir / f"mcp_diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.write_text(report)
        
        self.log("=" * 60, color=Colors.BOLD)
        if all_good:
            self.log("🎉 ALL DIAGNOSTICS PASSED!", "SUCCESS", Colors.BOLD + Colors.GREEN)
        else:
            self.log("⚠️ SOME ISSUES FOUND - CHECK REPORT", "WARNING", Colors.BOLD + Colors.YELLOW)
        
        self.log(f"📄 Report saved: {report_file}", "INFO")
        self.log("=" * 60, color=Colors.BOLD)
        
        return all_good

def main():
    parser = argparse.ArgumentParser(description="MCP Diagnostics Tool")
    parser.add_argument("--fix", action="store_true", help="Auto-fix common issues")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-tools", action="store_true", help="Skip tool testing")
    parser.add_argument("--cleanup", action="store_true", help="Just cleanup MCP processes")
    
    args = parser.parse_args()
    
    diagnostics = MCPDiagnostics(verbose=args.verbose, auto_fix=args.fix)
    
    if args.cleanup:
        diagnostics.cleanup_mcp_processes()
        return
    
    try:
        success = asyncio.run(diagnostics.run_full_diagnostics(test_tools=not args.no_tools))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Diagnostics interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}Diagnostics failed: {e}{Colors.END}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
