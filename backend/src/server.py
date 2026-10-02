# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""AI Job Engine MCP Server - Journey Management for TMF ODA Transformations.

This is a Model Context Protocol (MCP) server that enables AI assistants to manage
TMF ODA transformation journeys, stages, and Second Brain rules.

The server provides comprehensive tools for:
- Journey CRUD operations (create, read, update, delete, list)
- Stage management (add, update, delete, default stages)
- Second Brain rules management (AI-assisted transformation rules)
- Job monitoring and utilities
- Import/Export capabilities

All functionality is organized into modular services for maintainability and extensibility.
"""

# Load environment variables from .env files for application settings
# Note: AWS credentials are NOT loaded from .env files - they come from:
#   - On ECS: Task role (automatic via boto3)
#   - Locally: ~/.aws/credentials (set by aws-login.sh)
# Only USE_LOCALSTACK and application settings are read from .env files.
from pathlib import Path as _Path
try:
    from dotenv import load_dotenv as _load_dotenv
    _server_dir = _Path(__file__).parent.parent  # Go up to project root
    _env_local = _server_dir / '.env.local'
    _env_file = _server_dir / '.env'
    if _env_local.exists():
        _load_dotenv(_env_local, override=False)  # Don't override system env vars
    elif _env_file.exists():
        _load_dotenv(_env_file, override=False)
except ImportError:
    pass

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from pathlib import Path

from loguru import logger
from mcp.server.fastmcp import FastMCP

from .consts import CALL_ANALYSIS_MCP_SERVER_APPLICATION_NAME
from .services.journey_service import JourneyService
from .services.logs_and_reports_service import LogsAndReportsService
from .models.journey_model import JourneyActionRequest
from .models.logs_and_reports_model import LogsAndReportsActionRequest

# Import license tool
try:
    from .license.tools.license_tool import license_tool as _license_tool_func, init_license_tool
    from .license.services.license_service import LicenseService
    from .license.services.audit_service import AuditService
    LICENSE_TOOL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"License tool not available: {e}")
    LICENSE_TOOL_AVAILABLE = False



# Global MCP instance
mcp = FastMCP(CALL_ANALYSIS_MCP_SERVER_APPLICATION_NAME)

# Initialize services
journey_service = JourneyService()
logs_and_reports_service = LogsAndReportsService()

# Initialize license tool if available
if LICENSE_TOOL_AVAILABLE:
    try:
        _license_service = LicenseService()
        _audit_service = AuditService()
        init_license_tool(_license_service, _audit_service)
        logger.info("License tool initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize license tool: {e}")
        LICENSE_TOOL_AVAILABLE = False


# ==========================================
# Journey Management Tool with Streaming
# ==========================================

@mcp.tool()
async def journeys_tool(
    action: str,
    journey_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    rule_id: Optional[str] = None,
    job_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    odaComponentType: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    journey_data: Optional[Dict[str, Any]] = None,
    stage_data: Optional[Dict[str, Any]] = None,
    rule_data: Optional[Dict[str, Any]] = None,
    rule_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    component_type_filter: Optional[str] = None,
    include_all: bool = False,
    confirm: bool = False,
    job_status: Optional[str] = None,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    error_message: Optional[str] = None,
    job_ids: Optional[list] = None,
    reason: Optional[str] = None,
    triggered_by: Optional[str] = None,
    output_file: Optional[str] = None,
    input_file: Optional[str] = None,
    new_journey_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Comprehensive journey management tool for TMF ODA transformation journeys.
    Now with streaming support for list operations and progress reporting.
    """
    try:
        # Create request object
        request = JourneyActionRequest(
            action=action,
            journey_id=journey_id,
            stage_id=stage_id,
            rule_id=rule_id,
            job_id=job_id,
            name=name,
            description=description,
            odaComponentType=odaComponentType,
            priority=priority,
            status=status,
            journey_data=journey_data,
            stage_data=stage_data,
            rule_data=rule_data,
            rule_type=rule_type,
            status_filter=status_filter,
            component_type_filter=component_type_filter,
            include_all=include_all,
            confirm=confirm,
            job_status=job_status,
            progress=progress,
            current_step=current_step,
            error_message=error_message,
            job_ids=job_ids,
            reason=reason,
            triggered_by=triggered_by,
            output_file=output_file,
            input_file=input_file,
            new_journey_id=new_journey_id,
        )
        
        # Report progress for long operations
        if action in ["list", "export_complete", "import_complete", "get_comprehensive"]:
            logger.info(f"Starting {action} operation...")
        
        # Execute action via service
        response = await journey_service.execute_action(request)
        
        # Convert to standard dict format
        response_dict = response.model_dump(exclude_none=True)
        
        # For list operations, return full list instead of streaming chunks
        if action == "list" and response_dict.get("data"):
            journeys = response_dict["data"]
            logger.info(f"Found {len(journeys)} journeys")
            response_dict["total_count"] = len(journeys)
        
        return response_dict
        
    except ValueError as e:
        logger.error(f"Validation error in journeys_tool: {str(e)}")
        return {
            "status": "error",
            "message": f"Validation error: {str(e)}",
            "operation": action,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error in journeys_tool: {str(e)}")
        return {
            "status": "error",
            "message": f"Error executing journey operation: {str(e)}",
            "operation": action,
            "error": str(e)
        }


# ==========================================
# License Management Tool
# ==========================================

if LICENSE_TOOL_AVAILABLE:
    @mcp.tool()
    async def license_tool(
        action: str,
        license_key: Optional[str] = None,
        renewal_key: Optional[str] = None,
        reason: Optional[str] = None,
        feature_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        License management tool for AI Job Engine.
        
        Actions:
        - activate: Activate a license key (requires license_key)
        - status: Get current license status
        - deactivate: Deactivate current license (requires reason)
        - renew: Renew license with new key (requires renewal_key)
        - check_feature: Check if feature is accessible (requires feature_id)
        - audit_logs: Get license audit logs
        - validate: Validate current license
        """
        try:
            return await _license_tool_func(
                action=action,
                license_key=license_key,
                renewal_key=renewal_key,
                reason=reason,
                feature_id=feature_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(f"Error in license_tool: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing license operation: {str(e)}",
                "operation": action,
                "error": str(e)
            }


# ==========================================
# Logs and Reports Management Tool
# ==========================================

@mcp.tool()
async def logs_and_reports_tool(
    action: str,
    journey_id: Optional[str] = None,
    job_id: Optional[str] = None,
    stage_name: Optional[str] = None,
    step_name: Optional[str] = None,
    log_level: Optional[str] = None,
    log_message: Optional[str] = None,
    search_query: Optional[str] = None,
    log_source: str = "system",
    log_details: Optional[Dict[str, Any]] = None,
    report_type: Optional[str] = None,
    report_title: Optional[str] = None,
    report_content: Optional[Dict[str, Any]] = None,
    report_summary: Optional[str] = None,
    output_file: Optional[str] = None,
    export_format: str = "json",
    level_filter: Optional[str] = None,
    step_filter: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Comprehensive logs and reports management for TMF ODA journey jobs.
    Supports streaming for log analysis and report generation.
    
    Actions:
    - Log Management: get_job_logs, add_log_entry, search_logs, get_logs_by_level, 
                     export_job_logs, get_error_summary, list_available_logs
    - Report Management: get_job_reports, create_job_report, generate_summary_report,
                        generate_performance_report, generate_error_analysis_report,
                        list_available_reports, export_reports
    - Analytics: analyze_job_performance, analyze_error_patterns
    """
    try:
        # Create request object
        request = LogsAndReportsActionRequest(
            action=action,
            journey_id=journey_id,
            job_id=job_id,
            stage_name=stage_name,
            step_name=step_name,
            log_level=log_level,
            log_message=log_message,
            search_query=search_query,
            log_source=log_source,
            log_details=log_details,
            report_type=report_type,
            report_title=report_title,
            report_content=report_content,
            report_summary=report_summary,
            output_file=output_file,
            export_format=export_format,
            level_filter=level_filter,
            step_filter=step_filter,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        # Report progress for long operations
        if action in ["analyze_job_performance", "analyze_error_patterns", "generate_performance_report"]:
            logger.info(f"Starting {action} analysis...")
        
        # Execute action via service
        response = await logs_and_reports_service.execute_action(request)
        
        # For search operations, return full results
        if action == "search_logs" and isinstance(response, dict):
            if "logs" in response:
                logger.info(f"Found {len(response['logs'])} matching logs")
                response["total_count"] = len(response["logs"])
        
        return response
        
    except ValueError as e:
        logger.error(f"Validation error in logs_and_reports_tool: {str(e)}")
        from datetime import datetime, timezone
        return {
            "result": {
                "status": "error",
                "message": f"Validation error: {str(e)}",
                "operation": action,
                "error_code": "VALIDATION_ERROR",
                "error_details": {"error": str(e)}
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
    except Exception as e:
        logger.error(f"Error in logs_and_reports_tool: {str(e)}")
        from datetime import datetime, timezone
        return {
            "result": {
                "status": "error",
                "message": f"Error executing logs and reports operation: {str(e)}",
                "operation": action,
                "error_code": "INTERNAL_ERROR",
                "error_details": {"error": str(e)}
            },
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }


# ==========================================
# Service Status Helper
# ==========================================

# @mcp.info()  # Not supported by FastMCP
async def service_status() -> Dict[str, Any]:
    """Get the current status of all services."""
    logger.info("Checking service status...")
    status = {}
    
    # Check Journey Service
    try:
        test_request = JourneyActionRequest(action="list")
        result = await journey_service.execute_action(test_request)
        status["journey_service"] = {
            "status": "available",
            "message": "Journey Service is operational",
            "total_journeys": len(result.data) if hasattr(result, 'data') and result.data else 0
        }
    except Exception as e:
        status["journey_service"] = {
            "status": "unavailable",
            "message": f"Journey Service is not operational: {str(e)}"
        }
    
    # Check Logs and Reports Service
    try:
        test_request = LogsAndReportsActionRequest(action="list_available_logs")
        result = await logs_and_reports_service.execute_action(test_request)
        status["logs_and_reports_service"] = {
            "status": "available",
            "message": "Logs and Reports Service is operational"
        }
    except Exception as e:
        status["logs_and_reports_service"] = {
            "status": "unavailable",
            "message": f"Logs and Reports Service is not operational: {str(e)}"
        }
    
    status["server_info"] = {
        "name": CALL_ANALYSIS_MCP_SERVER_APPLICATION_NAME,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }
    
    return status


def create_server() -> FastMCP:
    """Create and configure the Site Analysis MCP server."""
    
    # MCP Server ready with all tools
    logger.info("MCP Server initialized successfully with Journey Management and Logs & Reports tools")
    return mcp


# ==========================================
# MCP Stdio Server for JSON-RPC Protocol
# ==========================================

class MCPStdioServer:
    """MCP Server using stdio transport for Cursor compatibility"""
    
    def __init__(self):
        self.capabilities = {
            "tools": {}
        }
        self.server_info = {
            "name": "AI Job Engine MCP Server",
            "version": "1.0.0"
        }
        self.tools = self._get_tools()
        # Use the global service instances
        self.journey_service = journey_service
        self.logs_and_reports_service = logs_and_reports_service
        
    def _get_tools(self) -> Dict[str, Any]:
        """Get available tools definitions - Journey management and Logs&Reports tools"""
        return {
            # Journey management tool
            "journeys_tool": {
                "name": "journeys_tool",
                "description": "Core journey, stage, and rule management (CRUD operations). Supports journey CRUD, stage management, rule management, and job utilities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform: create, read, update, delete, list, list_stages, add_stage, update_stage, delete_stage, add_default_stages, list_rules, add_rule, update_rule, delete_rule, export_complete, import_complete, dashboard, get_journey_summary, get_comprehensive, update_job_status, get_job_metrics, get_job_timeline, batch_cancel_jobs"
                        },
                        "journey_id": {"type": "string", "description": "Journey ID"},
                        "stage_id": {"type": "string", "description": "Stage ID"},
                        "rule_id": {"type": "string", "description": "Rule ID"},
                        "job_id": {"type": "string", "description": "Job ID"},
                        "name": {"type": "string", "description": "Journey name (for create)"},
                        "description": {"type": "string", "description": "Journey description"},
                        "odaComponentType": {"type": "string", "description": "ODA component type"},
                        "priority": {"type": "string", "description": "Journey priority (high, medium, low)"},
                        "status": {"type": "string", "description": "Journey status"},
                        "journey_data": {"type": "object", "description": "Journey data dict"},
                        "stage_data": {"type": "object", "description": "Stage data dict"},
                        "rule_data": {"type": "object", "description": "Rule data dict"},
                        "rule_type": {"type": "string", "description": "Filter by rule type"},
                        "status_filter": {"type": "string", "description": "Filter by status"},
                        "component_type_filter": {"type": "string", "description": "Filter by component type"},
                        "include_all": {"type": "boolean", "description": "Include all details", "default": False},
                        "confirm": {"type": "boolean", "description": "Skip confirmation prompts", "default": False},
                        "job_status": {"type": "string", "description": "Job status for updates"},
                        "progress": {"type": "integer", "description": "Job progress percentage (0-100)"},
                        "current_step": {"type": "string", "description": "Current step for job updates"},
                        "error_message": {"type": "string", "description": "Error message for job updates"},
                        "job_ids": {"type": "array", "items": {"type": "string"}, "description": "List of job IDs"},
                        "reason": {"type": "string", "description": "Reason for operation"},
                        "output_file": {"type": "string", "description": "Output file path"},
                        "input_file": {"type": "string", "description": "Input file path"},
                        "new_journey_id": {"type": "string", "description": "New journey ID for import"}
                    },
                    "required": ["action"]
                }
            },
            # Logs and Reports management tool
            "logs_and_reports_tool": {
                "name": "logs_and_reports_tool",
                "description": "Comprehensive logs and reports management for TMF ODA journey jobs. Supports log retrieval, searching, filtering, report generation, performance analysis, and error pattern detection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform: get_job_logs, add_log_entry, search_logs, get_logs_by_level, export_job_logs, get_error_summary, list_available_logs, get_job_reports, create_job_report, generate_summary_report, generate_performance_report, generate_error_analysis_report, list_available_reports, export_reports, analyze_job_performance, analyze_error_patterns"
                        },
                        "journey_id": {"type": "string", "description": "Journey ID"},
                        "job_id": {"type": "string", "description": "Job ID"},
                        "stage_name": {"type": "string", "description": "Stage name"},
                        "step_name": {"type": "string", "description": "Step name"},
                        "log_level": {"type": "string", "description": "Log level (error/warning/info/debug)"},
                        "log_message": {"type": "string", "description": "Log message"},
                        "search_query": {"type": "string", "description": "Search query string"},
                        "log_source": {"type": "string", "description": "Log source", "default": "system"},
                        "log_details": {"type": "object", "description": "Additional log details"},
                        "report_type": {"type": "string", "description": "Report type (summary/performance/error_analysis/custom)"},
                        "report_title": {"type": "string", "description": "Report title"},
                        "report_content": {"type": "object", "description": "Report content data"},
                        "report_summary": {"type": "string", "description": "Report summary"},
                        "output_file": {"type": "string", "description": "Output file path"},
                        "export_format": {"type": "string", "description": "Export format (json/csv/txt/html)", "default": "json"},
                        "level_filter": {"type": "string", "description": "Filter by log level"},
                        "step_filter": {"type": "string", "description": "Filter by step name"},
                        "start_time": {"type": "string", "description": "Start time filter (ISO 8601)"},
                        "end_time": {"type": "string", "description": "End time filter (ISO 8601)"},
                        "limit": {"type": "integer", "description": "Result limit", "default": 100},
                        "offset": {"type": "integer", "description": "Result offset", "default": 0}
                    },
                    "required": ["action"]
                }
            },
            # License management tool
            "license_tool": {
                "name": "license_tool",
                "description": "License management tool for AI Job Engine. Supports license activation, status, deactivation, renewal, feature checking, audit logs, and validation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform: activate, status, deactivate, renew, check_feature, audit_logs, validate"
                        },
                        "license_key": {"type": "string", "description": "License key for activation"},
                        "renewal_key": {"type": "string", "description": "Renewal key for renewal"},
                        "reason": {"type": "string", "description": "Reason for deactivation"},
                        "feature_id": {"type": "string", "description": "Feature ID for access check"},
                        "start_date": {"type": "string", "description": "Start date for audit logs (ISO format)"},
                        "end_date": {"type": "string", "description": "End date for audit logs (ISO format)"},
                        "limit": {"type": "integer", "description": "Maximum results for audit logs", "default": 100},
                        "offset": {"type": "integer", "description": "Pagination offset for audit logs", "default": 0}
                    },
                    "required": ["action"]
                }
            }
        }

    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        logger.info("MCP Server initializing...")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": self.server_info,
            "instructions": "\n# AI Job Engine MCP Server - Journey Management\n\nProvides comprehensive journey management tools for TMF ODA transformations.\n\nAvailable tools:\n- journeys_tool: Core journey, stage, and rule management (CRUD operations)\n- logs_and_reports_tool: Comprehensive logs and reports management\n\nSupports:\n- Journey CRUD (create, read, update, delete, list)\n- Stage management (add, update, delete, default stages)\n- Second Brain rules (AI-assisted transformation rules)\n- Job monitoring and utilities\n"
        }

    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request"""
        logger.info("Listing available tools")
        tools_list = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in self.tools.values()
        ]
        return {"tools": tools_list}

    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        logger.info(f"Calling tool: {tool_name}")
        
        if tool_name == "journeys_tool":
            # Call the existing journeys_tool function
            result = await journeys_tool(**arguments)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        elif tool_name == "logs_and_reports_tool":
            # Call the existing logs_and_reports_tool function
            result = await logs_and_reports_tool(**arguments)
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        elif tool_name == "license_tool":
            # Call the license_tool function
            if LICENSE_TOOL_AVAILABLE:
                result = await _license_tool_func(**arguments)
            else:
                result = {"status": "error", "message": "License tool not available"}
            return {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }]
            }
        else:
            raise Exception(f"Unknown tool: {tool_name}")

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP request"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "initialize":
                result = await self.handle_initialize(params)
            elif method == "tools/list":
                result = await self.handle_tools_list(params)
            elif method == "tools/call":
                result = await self.handle_tools_call(params)
            elif method == "notifications/initialized":
                # Standard MCP notification - no response needed
                return None
            else:
                raise Exception(f"Unsupported method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    async def run(self):
        """Main server loop reading from stdin and writing to stdout"""
        logger.info("Starting AI Job Engine MCP Stdio Server")
        logger.info("Listening on stdin for MCP requests")
        logger.info(f"Available tools: journeys_tool, logs_and_reports_tool")
        
        # Configure logging to stderr to avoid interfering with stdio
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
        
        try:
            while True:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:  # EOF
                    break
                    
                line = line.strip()
                if not line:  # Empty line
                    continue
                
                try:
                    # Parse JSON-RPC request
                    request = json.loads(line)
                    logger.info(f"Received request: {request.get('method')}")
                    
                    # Handle request
                    response = await self.handle_request(request)
                    
                    # Send response to stdout (skip for notifications that return None)
                    if response is not None:
                        response_line = json.dumps(response, separators=(',', ':'))
                        print(response_line, flush=True)  # Important: flush immediately
                        logger.info(f"Sent response for: {request.get('method')}")
                    else:
                        logger.info(f"Handled notification: {request.get('method')}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32700,
                            "message": "Parse error"
                        }
                    }
                    print(json.dumps(error_response, separators=(',', ':')), flush=True)
                
        except KeyboardInterrupt:
            logger.info("Server shutting down")


async def main():
    """Main entry point for the MCP server."""
    
    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info("Starting AI Job Engine MCP Server")
    logger.info("=" * 80)
    logger.info(f"Server: {CALL_ANALYSIS_MCP_SERVER_APPLICATION_NAME}")
    logger.info(f"Version: 1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info("=" * 80)
    
    # Test service availability at startup
    logger.info("Testing service availability...")
    
    # Test Journey Service
    try:
        test_request = JourneyActionRequest(action="list")
        result = await journey_service.execute_action(test_request)
        count = len(result.data) if hasattr(result, 'data') and result.data else 0
        logger.info(f"  ✓ Journey Service available ({count} journeys found)")
    except Exception as e:
        logger.warning(f"  ✗ Journey Service not available: {e}")
        
    # Test Logs and Reports Service
    try:
        test_request = LogsAndReportsActionRequest(action="list_available_logs")
        result = await logs_and_reports_service.execute_action(test_request)
        logger.info(f"  ✓ Logs and Reports Service available")
    except Exception as e:
        logger.warning(f"  ✗ Logs and Reports Service not available: {e}")
    
    logger.info("=" * 80)
    
    # The server is initialized via decorators
    logger.info("MCP Server is ready and running!")
    logger.info("")
    logger.info("Available Tools:")
    logger.info("  - journeys_tool: Core journey, stage, and rule management (CRUD operations)")
    logger.info("  - logs_and_reports_tool: Comprehensive logs and reports management")
    logger.info("")
    
    # Running FastMCP directly now starts the event loop and handles requests
    # mcp.run() # Don't call run() here, it should be called in __main__
    
    # Instead, keep the server running
    try:
        # Wait for the event loop - FastMCP should handle the actual serving
        # The run() method should be called from __main__ when invoked
        
        # For testing purposes, we just keep the service alive
        logger.info("MCP server is running...")
        
        # Use the built-in MCP run functionality
        try:
            await mcp.run()
        except RuntimeError as e:
            if "already running" in str(e).lower() or "cannot be called" in str(e).lower():
                logger.warning("Asyncio event loop conflict detected - server tools are registered and functional")
                logger.info("MCP tools are available for client connections")
                
                logger.info("Server is running and ready to accept MCP client connections...")
                logger.info("Press Ctrl+C to stop the server")
                
                # Simple wait that responds to KeyboardInterrupt properly
                try:
                    while True:
                        await asyncio.sleep(0.5)
                except KeyboardInterrupt:
                    logger.info("Server shutdown requested")
                    raise
            else:
                raise
        
    except KeyboardInterrupt:
        logger.info("Shutting down AI Job Engine MCP Server...")
    except Exception as e:
        logger.error(f"Error running AI Job Engine MCP Server: {str(e)}")
        raise


if __name__ == "__main__":
    # Support both direct execution and FastMCP CLI
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Use custom stdio handler for Cursor compatibility
        server = MCPStdioServer()
        asyncio.run(server.run())
    else:
        # Run with asyncio for standalone testing
        asyncio.run(main())