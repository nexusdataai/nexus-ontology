import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional

import httpx
from langflow.custom import Component
from langflow.io import (
    StrInput,
    BoolInput,
    Output,
    DropdownInput,
    SecretStrInput
)
from langflow.schema import Data
from langflow.logging import logger
import traceback
import time


class MCPHTTPClient:
    """Client for connecting to remote MCP servers via HTTP"""
    
    def __init__(self, base_url: str, auth_token: str = ""):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.http_client = None
        self.message_id = 0
        self.connected = False
    
    async def connect(self):
        """Connect to the HTTP MCP bridge"""
        if self.connected:
            logger.info("🔄 Already connected, skipping connection")
            return
            
        logger.info(f"🚀 Starting HTTP connection to {self.base_url}")
        
        try:
            # Create HTTP client
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0),
                headers=headers
            )
            
            # Test connection
            logger.info("🔧 Testing connection...")
            
            response = await self.http_client.get(f"{self.base_url}/health")
            response.raise_for_status()
            
            health_data = response.json()
            print(f"✅ Connected to MCP HTTP Bridge: {health_data}")
            
            # Initialize the MCP server
            logger.info("🔧 Initializing MCP server...")
            await self._initialize_mcp_server()
            
            self.connected = True
            logger.info("✅ HTTP connection established and MCP server initialized")
            
        except Exception as e:
            logger.error(f"❌ HTTP connection failed: {str(e)}")
            
            if self.http_client:
                await self.http_client.aclose()
                self.http_client = None
            
            raise Exception(f"Failed to connect via HTTP: {str(e)}")
    
    async def _initialize_mcp_server(self):
        """Initialize the MCP server after connection"""
        logger.info("🔧 Sending MCP initialize request...")
        
        # Send initialize request
        init_response = await self._send_mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "langflow-http-mcp",
                "version": "1.0.0"
            }
        })
        logger.info(f"📥 Initialize response: {init_response}")
        
        # Send initialized notification
        logger.info("📢 Sending initialized notification...")
        await self._send_mcp_notification("notifications/initialized")
        logger.info("✅ MCP server initialization complete")
    
    async def _send_mcp_request(self, method: str, params: Optional[Dict] = None, debug_msgs=None):
        """Send JSON-RPC request via HTTP"""
        if not self.http_client:
            raise Exception("HTTP connection not established")
        if debug_msgs is None:
            debug_msgs = []
        self.message_id += 1
        request_data = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method
        }
        if params:
            request_data["params"] = params
        url = f"{self.base_url}/mcp/request"
        timeout_val = getattr(self.http_client, 'timeout', None)
        debug_msgs.append(f"[DEBUG] Sending MCP request to URL: {url}")
        debug_msgs.append(f"[DEBUG] Request payload: {request_data}")
        debug_msgs.append(f"[DEBUG] Timeout: {timeout_val}")
        start_time = time.time()
        debug_msgs.append(f"[DEBUG] Request start time: {start_time}")
        try:
            response = await self.http_client.post(
                url,
                json=request_data
            )
            end_time = time.time()
            debug_msgs.append(f"[DEBUG] Request end time: {end_time}")
            debug_msgs.append(f"[DEBUG] Request duration: {end_time - start_time:.2f} seconds")
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"📥 Response: {response_data}")
            debug_msgs.append(f"[DEBUG] Response status: {response.status_code}")
            debug_msgs.append(f"[DEBUG] Response body: {response.text}")
            return response_data
        except httpx.TimeoutException as e:
            end_time = time.time()
            debug_msgs.append(f"[DEBUG] Request end time: {end_time}")
            debug_msgs.append(f"[DEBUG] Request duration: {end_time - start_time:.2f} seconds")
            debug_msgs.append(f"[DEBUG] TimeoutException: {str(e)}")
            debug_msgs.append(traceback.format_exc())
            logger.error(f"❌ HTTP request timed out: {str(e)}")
            raise Exception(f"HTTP MCP request timed out: {str(e)}")
        except httpx.ConnectError as e:
            end_time = time.time()
            debug_msgs.append(f"[DEBUG] Request end time: {end_time}")
            debug_msgs.append(f"[DEBUG] Request duration: {end_time - start_time:.2f} seconds")
            debug_msgs.append(f"[DEBUG] ConnectError: {str(e)}")
            debug_msgs.append(traceback.format_exc())
            logger.error(f"❌ HTTP connection error: {str(e)}")
            raise Exception(f"HTTP MCP connection error: {str(e)}")
        except httpx.HTTPStatusError as e:
            end_time = time.time()
            debug_msgs.append(f"[DEBUG] Request end time: {end_time}")
            debug_msgs.append(f"[DEBUG] Request duration: {end_time - start_time:.2f} seconds")
            debug_msgs.append(f"[DEBUG] HTTPStatusError: {e.response.status_code} {e.response.text}")
            debug_msgs.append(traceback.format_exc())
            logger.error(f"❌ HTTP status error: {e.response.status_code} {e.response.text}")
            raise Exception(f"HTTP MCP server error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            end_time = time.time()
            debug_msgs.append(f"[DEBUG] Request end time: {end_time}")
            debug_msgs.append(f"[DEBUG] Request duration: {end_time - start_time:.2f} seconds")
            debug_msgs.append(f"[DEBUG] Exception: {str(e)}")
            debug_msgs.append(traceback.format_exc())
            logger.error(f"❌ HTTP request failed: {str(e)}")
            raise Exception(f"HTTP MCP request failed: {str(e)}")
    
    async def _send_mcp_notification(self, method: str, params: Optional[Dict] = None):
        """Send JSON-RPC notification via HTTP"""
        if not self.http_client:
            raise Exception("HTTP connection not established")
            
        notification_data = {
            "jsonrpc": "2.0",
            "method": method
        }
        
        if params:
            notification_data["params"] = params
        
        logger.info(f"📢 Sending notification: {json.dumps(notification_data)}")
        
        try:
            response = await self.http_client.post(
                f"{self.base_url}/mcp/notification",
                json=notification_data
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"❌ Notification failed: {str(e)}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools on the remote server"""
        logger.info("📋 Requesting tools list from MCP server...")
        print("📋 Requesting fresh tools list from MCP server...")
        
        response = await self._send_mcp_request("tools/list")
        
        if "result" in response:
            tools = response["result"].get("tools", [])
            tool_names = [tool.get("name", "Unknown") for tool in tools]
            logger.info(f"📋 Retrieved {len(tools)} tools from server: {tool_names}")
            print(f"📋 Retrieved {len(tools)} tools from server: {tool_names}")
            return tools
        elif "error" in response:
            logger.error(f"❌ MCP server returned error: {response['error']}")
            print(f"❌ MCP server returned error: {response['error']}")
            raise Exception(f"MCP Error: {response['error']}")
        else:
            logger.error(f"❌ Unexpected response format: {response}")
            print(f"❌ Unexpected response format: {response}")
            raise Exception(f"Unexpected response: {response}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any], debug_mode: bool = False, collect_debug: bool = False):
        debug_msgs = []
        logger.info(f"🔧 Calling tool: {tool_name}")
        msg = f"🔧 Calling tool: {tool_name} with args: {arguments}"
        print(msg)
        if collect_debug:
            debug_msgs.append(msg)
        try:
            response = await self._send_mcp_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            }, debug_msgs=debug_msgs)
        except Exception as e:
            # The exception message is already detailed and debug_msgs is filled
            return f"{str(e)}", debug_msgs
        msg = f"[DEBUG] Raw response from server: {response}"
        if debug_mode:
            print(msg)
        logger.info(msg)
        if collect_debug:
            debug_msgs.append(msg)
        if "result" in response:
            content = response["result"].get("content", [{"text": "No content returned"}])
            if content and isinstance(content, list) and len(content) > 0:
                return content[0].get("text", str(content)), debug_msgs
            return str(content), debug_msgs
        elif "error" in response:
            return f"MCP Error: {response['error']}", debug_msgs
        else:
            return f"Unexpected response: {response}", debug_msgs
    
    async def disconnect(self):
        """Close the HTTP connection"""
        logger.info("🔌 Closing HTTP connection...")
        
        self.connected = False
        
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        logger.info("✅ HTTP connection closed")


class MCPHTTPComponent(Component):
    display_name = "MCP HTTP Server"
    description = "Connect to an MCP server running on a remote machine via HTTP bridge"
    documentation: str = "https://docs.langflow.org/components-custom-components"
    icon = "server"
    name = "MCPHTTPComponent"

    inputs = [
        DropdownInput(
            name="action",
            display_name="Action",
            options=[
                "List Tools",
                "Execute Tool",
                "Test Connection"
            ],
            info="The action to perform with the MCP server",
            real_time_refresh=True,
            tool_mode=True,
        ),
        StrInput(
            name="base_url",
            display_name="Base URL",
            info="HTTP URL of the Alert Correlation Engine MCP server (e.g., http://localhost:8000)",
            value="http://localhost:8000",
            advanced=False,
        ),
        SecretStrInput(
            name="auth_token",
            display_name="Auth Token",
            info="Optional authentication token for the HTTP bridge",
            advanced=True,
        ),
        DropdownInput(
            name="selected_tool",
            display_name="Selected Tool",
            options=[],
            info="Choose a tool to view or execute (used for List Tools and Execute Tool actions)",
            real_time_refresh=True,
            refresh_button=True,
            tool_mode=True,
        ),
        StrInput(
            name="tool_arguments",
            display_name="Tool Arguments (JSON)",
            info="JSON object with arguments for the selected tool",
            value="{}",
            advanced=False,
            tool_mode=True,
        ),
        BoolInput(
            name="debug_mode",
            display_name="Debug Mode",
            info="Enable detailed debug output",
            value=False,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Data", name="data", method="execute_mcp_action"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.http_client: Optional[MCPHTTPClient] = None
        self.available_tools: List[Dict[str, Any]] = []
        self.tool_names: List[str] = []

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Update build configuration dynamically"""
        try:
            # Check if we should refresh tools
            should_refresh = False
            
            # Refresh when action changes to "Execute Tool" or "List Tools"
            if field_name == "action" and field_value in ["Execute Tool", "List Tools"]:
                should_refresh = True
                logger.info(f"🔄 Action changed to {field_value} - will refresh tools")
            
            # Refresh when base_url changes
            elif field_name == "base_url":
                should_refresh = True
                logger.info(f"🔄 Base URL changed to {field_value} - will refresh tools")
                print(f"🔄 Base URL changed to {field_value} - will refresh tools")
                
                # Clear all cached data when URL changes
                self.available_tools = []
                self.tool_names = []
                if self.http_client:
                    try:
                        # This will be handled async later
                        pass
                    except:
                        pass
            
            # Refresh when selected_tool refresh button is clicked
            elif field_name == "selected_tool":
                # Allow refresh for both List Tools and Execute Tool actions
                current_action = build_config.get("action", {}).get("value", "")
                if current_action in ["Execute Tool", "List Tools"]:
                    should_refresh = True
                    logger.info(f"🔄 Selected Tool refresh button clicked - will refresh tools for action: {current_action}")
            
            if should_refresh:
                # Try to refresh tools if we have a base_url
                base_url = build_config.get("base_url", {}).get("value", "")
                if base_url:
                    logger.info(f"🔗 Attempting to refresh tools for URL: {base_url}")
                    
                    # Run async tool refresh in sync context
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(self._refresh_tools(base_url))
                        if "selected_tool" in build_config:
                            build_config["selected_tool"]["options"] = self.tool_names
                            logger.info(f"✅ Updated dropdown with {len(self.tool_names)} tools: {self.tool_names}")
                            print(f"✅ Updated dropdown with {len(self.tool_names)} tools: {self.tool_names}")
                    except Exception as e:
                        logger.warning(f"Tool refresh failed: {str(e)}")
                        print(f"❌ Tool refresh failed: {str(e)}")
                        if "selected_tool" in build_config:
                            build_config["selected_tool"]["options"] = []
                else:
                    logger.info("⚠️ No base_url available for tool refresh")
                    print("⚠️ No base_url available for tool refresh")
                    if "selected_tool" in build_config:
                        build_config["selected_tool"]["options"] = []
                        
        except Exception as e:
            error_msg = f"Failed to refresh tools: {str(e)}"
            logger.warning(error_msg)
            print(f"❌ {error_msg}")
            if "selected_tool" in build_config:
                build_config["selected_tool"]["options"] = []
        
        return build_config

    def post_code_processing(self, new_build_config: dict, current_build_config: dict) -> dict:
        """Called after build config is updated - try to load tools on initial load"""
        try:
            # Check if action is Execute Tool or List Tools and we don't have tools yet
            current_action = new_build_config.get("action", {}).get("value", "")
            if current_action in ["Execute Tool", "List Tools"] and not self.tool_names:
                base_url = new_build_config.get("base_url", {}).get("value", "")
                
                if base_url:
                    logger.info(f"🔄 Post-processing: Action is {current_action}, trying to load tools for {base_url}")
                    print(f"🔄 Post-processing: Action is {current_action}, trying to load tools for {base_url}")
                    
                    # Run async tool refresh in sync context
                    loop = None
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(self._refresh_tools(base_url))
                        if "selected_tool" in new_build_config:
                            new_build_config["selected_tool"]["options"] = self.tool_names
                            logger.info(f"✅ Post-processing: Updated with {len(self.tool_names)} tools")
                            print(f"✅ Post-processing: Updated with {len(self.tool_names)} tools")
                    except Exception as e:
                        logger.warning(f"Post-processing tool refresh failed: {str(e)}")
                        print(f"❌ Post-processing tool refresh failed: {str(e)}")
                        if "selected_tool" in new_build_config:
                            new_build_config["selected_tool"]["options"] = []
        
        except Exception as e:
            logger.warning(f"Post-processing error: {str(e)}")
            print(f"❌ Post-processing error: {str(e)}")
        
        return new_build_config

    async def _force_refresh_tools(self):
        """Force refresh tools by clearing cache and reconnecting"""
        if self.http_client:
            try:
                await self.http_client.disconnect()
            except:
                pass
            self.http_client = None
        
        self.available_tools = []
        self.tool_names = []
        
        # Reconnect and refresh
        await self._ensure_connected()

    async def _refresh_tools(self, base_url: str):
        """Refresh the list of available tools from the remote server"""
        logger.info("🔄 Starting tool refresh process...")
        
        # Reset tools list first
        self.available_tools = []
        self.tool_names = []
        
        try:
            # Disconnect existing connection if any
            if self.http_client:
                logger.info("🔌 Disconnecting existing HTTP client...")
                try:
                    await self.http_client.disconnect()
                except:
                    pass  # Ignore disconnect errors
            
            # Create new HTTP client
            logger.info("🆕 Creating new HTTP client...")
            print(f"🆕 Creating new HTTP client for {base_url}...")
            
            auth_token = getattr(self, 'auth_token', '') or ""
            print(f"🔑 Auth token provided: {'Yes' if auth_token else 'No'}")
            
            self.http_client = MCPHTTPClient(
                base_url=base_url,
                auth_token=auth_token
            )
            
            # Connect and list tools
            logger.info("🔗 Establishing HTTP connection...")
            print("🔗 Establishing HTTP connection...")
            await self.http_client.connect()
            
            logger.info("📋 Listing tools from remote server...")
            print("📋 Listing tools from remote server...")
            self.available_tools = await self.http_client.list_tools()
            self.tool_names = [tool.get("name", "") for tool in self.available_tools if tool.get("name")]
            
            logger.info(f"✅ Found {len(self.tool_names)} tools: {', '.join(self.tool_names)}")
            print(f"✅ Found {len(self.tool_names)} tools: {', '.join(self.tool_names)}")
            
            return True  # Success
            
        except Exception as e:
            error_msg = f"Failed to refresh tools: {str(e)}"
            logger.error(f"❌ {error_msg}")
            print(f"❌ {error_msg}")
            
            # Ensure we have empty lists on failure
            self.available_tools = []
            self.tool_names = []
            
            # Clean up connection on failure
            if self.http_client:
                try:
                    await self.http_client.disconnect()
                except:
                    pass
                self.http_client = None
            
            # Re-raise the error so it can be properly handled
            raise e

    async def _ensure_connected(self):
        """Ensure we have a connection and tools are loaded"""
        debug_mode = getattr(self, 'debug_mode', False)
        
        if not self.http_client:
            auth_token = getattr(self, 'auth_token', '') or ""
            if debug_mode:
                print(f"🔧 Creating new HTTP client for {self.base_url}")
            
            self.http_client = MCPHTTPClient(
                base_url=self.base_url,
                auth_token=auth_token
            )
        
        if not self.http_client.connected:
            if debug_mode:
                print("🔗 Establishing HTTP connection...")
            await self.http_client.connect()
        
        # Always refresh tools to ensure we have the latest
        if debug_mode:
            print("📋 Refreshing tools from MCP server...")
        self.available_tools = await self.http_client.list_tools()
        self.tool_names = [tool.get("name", "") for tool in self.available_tools if tool.get("name")]
        if debug_mode:
            print(f"📋 Loaded {len(self.tool_names)} tools: {self.tool_names}")

    async def _list_tools_action(self) -> Data:
        """List all available tools on the MCP server"""
        debug_mode = getattr(self, 'debug_mode', False)
        
        try:
            # Force refresh to get latest tools
            if debug_mode:
                print("🔄 Force refreshing tools for list operation...")
            await self._force_refresh_tools()
            
            if debug_mode:
                print(f"📋 Found {len(self.available_tools)} tools")
                print(f"📋 Tool names: {self.tool_names}")
            
            tools_info = []
            for tool in self.available_tools:
                name = tool.get("name", "Unknown")
                desc = tool.get("description", "No description")
                input_schema = tool.get("inputSchema", {})
                
                if debug_mode:
                    print(f"📋 Processing tool: {name} - {desc[:50]}...")
                
                tool_data = {
                    "name": name,
                    "description": desc,
                    "input_schema": input_schema
                }
                tools_info.append(tool_data)
            
            return Data(data={
                "action": "list_tools",
                "tools_count": len(tools_info),
                "tools": tools_info,
                "tool_names": self.tool_names
            })
            
        except Exception as e:
            error_msg = f"Failed to list tools: {str(e)}"
            logger.error(error_msg)
            return Data(data={
                "action": "list_tools", 
                "error": error_msg
            })

    async def _execute_tool_action(self) -> Data:
        """Execute a specific tool with provided arguments"""
        debug_mode = getattr(self, 'debug_mode', False)
        debug_msgs = []
        try:
            # Validate inputs
            if not getattr(self, 'selected_tool', ''):
                msg = "[DEBUG] No tool selected."
                if debug_mode:
                    print(msg)
                logger.info(msg)
                debug_msgs.append(msg)
                return Data(data={
                    "action": "execute_tool",
                    "error": "No tool selected. Please select a tool first.",
                    "debug": "\n".join(debug_msgs) if debug_mode else None
                })
            # Parse tool arguments
            try:
                arguments = json.loads(getattr(self, 'tool_arguments', '{}'))
            except json.JSONDecodeError as e:
                msg = f"[DEBUG] Invalid JSON in tool arguments: {str(e)}"
                if debug_mode:
                    print(msg)
                logger.info(msg)
                debug_msgs.append(msg)
                return Data(data={
                    "action": "execute_tool",
                    "error": f"Invalid JSON in tool arguments: {str(e)}",
                    "debug": "\n".join(debug_msgs) if debug_mode else None
                })
            await self._ensure_connected()
            msg = f"[DEBUG] Available tool names: {self.tool_names}"
            if debug_mode:
                print(msg)
            logger.info(msg)
            debug_msgs.append(msg)
            msg = f"[DEBUG] Selected tool: {self.selected_tool}"
            if debug_mode:
                print(msg)
            logger.info(msg)
            debug_msgs.append(msg)
            msg = f"[DEBUG] Arguments: {arguments}"
            if debug_mode:
                print(msg)
            logger.info(msg)
            debug_msgs.append(msg)
            if self.selected_tool not in self.tool_names:
                msg = f"[DEBUG] Tool '{self.selected_tool}' not found in available tools: {self.tool_names}"
                if debug_mode:
                    print(msg)
                logger.info(msg)
                debug_msgs.append(msg)
                return Data(data={
                    "action": "execute_tool",
                    "error": f"Tool '{self.selected_tool}' not found in available tools: {self.tool_names}",
                    "debug": "\n".join(debug_msgs) if debug_mode else None
                })
            msg = f"🔧 Executing tool: {self.selected_tool} with args: {arguments}"
            if debug_mode:
                print(msg)
            logger.info(msg)
            debug_msgs.append(msg)
            # Execute the tool
            result, call_debug_msgs = await self.http_client.call_tool(self.selected_tool, arguments, debug_mode=debug_mode, collect_debug=True)
            debug_msgs.extend(call_debug_msgs)
            msg = f"[DEBUG] Tool execution result: {result}"
            if debug_mode:
                print(msg)
            logger.info(msg)
            debug_msgs.append(msg)
            return Data(data={
                "action": "execute_tool",
                "tool_name": self.selected_tool,
                "arguments": arguments,
                "result": result,
                "debug": "\n".join(debug_msgs) if debug_mode else None
            })
        except Exception as e:
            error_msg = f"Failed to execute tool: {str(e)}"
            logger.error(error_msg)
            msg = f"[DEBUG] Exception in execute_tool_action: {error_msg}"
            if debug_mode:
                print(msg)
            debug_msgs.append(msg)
            return Data(data={
                "action": "execute_tool",
                "error": error_msg,
                "debug": "\n".join(debug_msgs) if debug_mode else None
            })

    async def _test_connection_action(self) -> Data:
        """Test the connection to the MCP server"""
        debug_mode = getattr(self, 'debug_mode', False)
        
        try:
            if debug_mode:
                print(f"🧪 Testing connection to {self.base_url}")
            
            # Force refresh to test connection and get latest tools
            await self._force_refresh_tools()
            
            connection_info = {
                "base_url": self.base_url,
                "connected": self.http_client.connected,
                "tools_count": len(self.available_tools),
                "tool_names": self.tool_names
            }
            
            if debug_mode:
                print(f"✅ Connection test successful: {connection_info}")
            
            return Data(data={
                "action": "test_connection",
                "success": True,
                "connection_info": connection_info
            })
            
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg)
            return Data(data={
                "action": "test_connection",
                "success": False,
                "error": error_msg
            })

    def execute_mcp_action(self) -> Data:
        """Main method that routes to the appropriate action"""
        action = getattr(self, "action", "List Tools")
        debug_mode = getattr(self, 'debug_mode', False)
        
        if debug_mode:
            print(f"🚀 Executing MCP action: {action}")
        
        # Set up async event loop
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            if action == "List Tools":
                return loop.run_until_complete(self._list_tools_action())
            elif action == "Execute Tool":
                return loop.run_until_complete(self._execute_tool_action())
            elif action == "Test Connection":
                return loop.run_until_complete(self._test_connection_action())
            else:
                return Data(data={
                    "error": f"Unknown action: {action}"
                })
        except Exception as e:
            error_msg = f"Error executing action '{action}': {str(e)}"
            logger.error(error_msg)
            return Data(data={
                "action": action,
                "error": error_msg
            })
        finally:
            # Keep connection alive for better performance
            # Connection will be cleaned up in __del__ or when component is destroyed
            pass

    def __del__(self):
        """Cleanup HTTP connection on component destruction"""
        if self.http_client:
            try:
                # Try to clean up the connection
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.http_client.disconnect())
            except:
                pass  # Ignore cleanup errors 