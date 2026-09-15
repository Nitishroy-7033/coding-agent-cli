import asyncio
import threading
import json
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List
from contextlib import AsyncExitStack

# Try to import mcp SDK
try:
    from mcp.client.session import ClientSession
    import mcp.client.stdio
    import mcp.client.sse
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class MCPManager:
    """Manages MCP server connections in a background asyncio loop."""

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.config_path = workspace_dir / "agent" / "mcp.json"
        
        self.servers: Dict[str, dict] = {}
        self.sessions: Dict[str, "ClientSession"] = {}
        self.mcp_tools: List[dict] = []  # List of OpenAI-formatted tool schemas
        self.server_status: Dict[str, dict] = {}  # detailed status per server
        self._exit_stack = None
        
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self.stats = {"servers": 0, "tools": 0}

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load MCP config: {e}")
            return {}

    async def _connect_server(self, name: str, config: dict, exit_stack: AsyncExitStack):
        """Connects to a single MCP server."""
        try:
            conn_type = config.get("type", "stdio")
            
            if conn_type == "stdio":
                command = config.get("command")
                args = config.get("args", [])
                env = config.get("env", None)
                
                server_params = mcp.client.stdio.StdioServerParameters(
                    command=command, 
                    args=args, 
                    env=env
                )
                
                read_stream, write_stream = await exit_stack.enter_async_context(
                    mcp.client.stdio.stdio_client(server_params)
                )
            
            elif conn_type in ("https", "sse"):
                url = config.get("url")
                if not url:
                    raise ValueError(f"MCP server '{name}' missing 'url' for https/sse connection.")
                
                read_stream, write_stream = await exit_stack.enter_async_context(
                    mcp.client.sse.sse_client(url)
                )
                
            else:
                raise ValueError(f"Unknown MCP connection type: {conn_type}")
                
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            await session.initialize()
            self.sessions[name] = session
            self.stats["servers"] += 1
            
            # Fetch tools
            tools_response = await session.list_tools()
            tool_names = []
            for tool in tools_response.tools:
                self._register_tool(name, tool)
                self.stats["tools"] += 1
                tool_names.append(tool.name)
                
            self.server_status[name] = {"status": "Active", "tools": tool_names}
                
        except Exception as e:
            logging.error(f"Error connecting to MCP server '{name}': {e}")
            self.server_status[name] = {"status": "Error", "error": str(e), "tools": []}

    def _register_tool(self, server_name: str, tool: Any):
        """Convert MCP tool to OpenAI schema and store it."""
        # Create a unique name to avoid collisions, but keep it clean
        # e.g., markitdown_convert
        safe_server_name = server_name.replace("/", "_").replace("-", "_")
        tool_name = f"{safe_server_name}_{tool.name}"
        
        # Convert MCP json schema to dict if necessary
        # Usually tool.inputSchema is a dict
        input_schema = tool.inputSchema
        
        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool.description or f"Tool {tool.name} from MCP server {server_name}",
                "parameters": input_schema
            }
        }
        
        # Store metadata to easily route the call later
        self.mcp_tools.append({
            "schema": schema,
            "server_name": server_name,
            "mcp_tool_name": tool.name
        })

    async def _initialize_async(self):
        config_data = self._load_config()
        self.servers = config_data.get("servers", {})
        
        if not self.servers:
            return
            
        self._exit_stack = AsyncExitStack()
        
        # Connect to all servers concurrently
        tasks = []
        for name, config in self.servers.items():
            tasks.append(self._connect_server(name, config, self._exit_stack))
            
        if tasks:
            await asyncio.gather(*tasks)

    async def _stop_async(self):
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
        self.sessions.clear()
        self.mcp_tools.clear()
        self.server_status.clear()
        self.stats = {"servers": 0, "tools": 0}

    def stop_sync(self):
        """Synchronously stops all MCP connections."""
        future = asyncio.run_coroutine_threadsafe(self._stop_async(), self._loop)
        future.result()

    def reload_sync(self):
        """Synchronously stops and restarts all MCP connections."""
        self.stop_sync()
        self.initialize_sync()

    def initialize_sync(self):
        """Synchronously initializes MCP connections. Blocks until complete."""
        if not MCP_AVAILABLE:
            logging.warning("MCP library not installed. Skipping MCP initialization.")
            return
            
        future = asyncio.run_coroutine_threadsafe(self._initialize_async(), self._loop)
        future.result() # Wait for completion

    async def _call_tool_async(self, server_name: str, mcp_tool_name: str, args: dict) -> str:
        session = self.sessions.get(server_name)
        if not session:
            return f"Error: MCP server '{server_name}' is not connected."
            
        try:
            result = await session.call_tool(mcp_tool_name, arguments=args)
            
            # Format result content (list of TextContent, etc.)
            output = []
            for content in result.content:
                if content.type == "text":
                    output.append(content.text)
                else:
                    output.append(str(content))
                    
            if result.isError:
                return "Error from MCP server:\n" + "\n".join(output)
            return "\n".join(output)
            
        except Exception as e:
            return f"Exception calling MCP tool '{mcp_tool_name}': {str(e)}"

    def call_tool_sync(self, server_name: str, mcp_tool_name: str, args: dict) -> str:
        """Synchronously calls an MCP tool."""
        future = asyncio.run_coroutine_threadsafe(
            self._call_tool_async(server_name, mcp_tool_name, args), 
            self._loop
        )
        return future.result()

    def get_stats(self) -> Dict[str, int]:
        return self.stats
        
    def inject_tools(self, registry_module) -> None:
        """Injects discovered MCP tools into the agent's tool registry."""
        registry_module.unregister_dynamic_tools()
        for tool_info in self.mcp_tools:
            schema = tool_info["schema"]
            tool_name = schema["function"]["name"]
            server_name = tool_info["server_name"]
            mcp_tool_name = tool_info["mcp_tool_name"]
            
            # Create a closure that binds the routing information
            def make_handler(srv, mcp_t):
                def handler(**kwargs):
                    return self.call_tool_sync(srv, mcp_t, kwargs)
                return handler
                
            handler = make_handler(server_name, mcp_tool_name)
            registry_module.register_dynamic_tool(tool_name, handler, schema)
