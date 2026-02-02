#!/usr/bin/env python3
"""
HTTP/SSE Server for MCP Multiplexer

Exposes all MCP tools (demo-recorder + Playwright) over HTTP using SSE transport.
This allows remote clients to connect and use all 35 tools.

Usage:
    python -m recorder.http_multiplexer
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional
from dataclasses import dataclass, field

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse

from mcp.server.sse import SseServerTransport
from mcp.server import Server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ChildMCP:
    """Represents a child MCP server process."""
    name: str
    command: list[str]
    process: Optional[asyncio.subprocess.Process] = None
    tools: dict[str, dict] = field(default_factory=dict)
    request_id: int = 0
    pending_requests: dict[int, asyncio.Future] = field(default_factory=dict)
    read_task: Optional[asyncio.Task] = None


class HTTPMultiplexer:
    """HTTP-based MCP multiplexer that exposes all tools via SSE."""
    
    def __init__(self):
        self.children: dict[str, ChildMCP] = {}
        self.tool_to_child: dict[str, str] = {}
        self.server = Server("mcp-http-multiplexer")
        self._all_tools: list[Tool] = []
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return self._all_tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            if name not in self.tool_to_child:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
            child_name = self.tool_to_child[name]
            child = self.children[child_name]
            
            try:
                result = await self._call_child_tool(child, name, arguments)
                return result
            except Exception as e:
                logger.error(f"Error calling {name}: {e}")
                return [TextContent(type="text", text=f"Error calling {name}: {str(e)}")]
    
    async def start_child(self, name: str, command: list[str]):
        """Start a child MCP server."""
        logger.info(f"Starting child MCP: {name} with command: {' '.join(command)}")
        
        child = ChildMCP(name=name, command=command)
        
        child.process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "CONTAINER": os.environ.get("CONTAINER", "docker")},
        )
        
        self.children[name] = child
        
        # Start background reader
        child.read_task = asyncio.create_task(self._read_child_output(child))
        
        # Initialize and discover tools
        await self._initialize_child(child)
        
        logger.info(f"Child {name} started with {len(child.tools)} tools")
    
    async def _read_child_output(self, child: ChildMCP):
        """Background task to read output from child MCP."""
        try:
            while True:
                if child.process is None or child.process.stdout is None:
                    break
                
                line = await child.process.stdout.readline()
                if not line:
                    break
                
                try:
                    response = json.loads(line.decode())
                    request_id = response.get("id")
                    
                    if request_id and request_id in child.pending_requests:
                        future = child.pending_requests.pop(request_id)
                        if not future.done():
                            future.set_result(response)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Error reading from {child.name}: {e}")
    
    async def _send_request(self, child: ChildMCP, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request to child."""
        if child.process is None or child.process.stdin is None:
            raise RuntimeError(f"Child {child.name} not running")
        
        child.request_id += 1
        request_id = child.request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params:
            request["params"] = params
        
        future = asyncio.get_event_loop().create_future()
        child.pending_requests[request_id] = future
        
        request_line = json.dumps(request) + "\n"
        child.process.stdin.write(request_line.encode())
        await child.process.stdin.drain()
        
        try:
            response = await asyncio.wait_for(future, timeout=30)
            return response
        except asyncio.TimeoutError:
            child.pending_requests.pop(request_id, None)
            raise TimeoutError(f"Timeout waiting for {method} from {child.name}")
    
    async def _initialize_child(self, child: ChildMCP):
        """Initialize child and discover tools."""
        # Send initialize
        await self._send_request(child, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "http-multiplexer", "version": "1.0.0"}
        })
        
        # Send initialized notification
        if child.process and child.process.stdin:
            notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
            child.process.stdin.write(notif.encode())
            await child.process.stdin.drain()
        
        # Get tools
        response = await self._send_request(child, "tools/list", {})
        
        if "result" in response and "tools" in response["result"]:
            for tool in response["result"]["tools"]:
                tool_name = tool["name"]
                child.tools[tool_name] = tool
                self.tool_to_child[tool_name] = child.name
                
                self._all_tools.append(Tool(
                    name=tool_name,
                    description=tool.get("description", ""),
                    inputSchema=tool.get("inputSchema", {"type": "object", "properties": {}})
                ))
    
    async def _call_child_tool(self, child: ChildMCP, tool_name: str, arguments: dict) -> list[TextContent]:
        """Call a tool on a child MCP."""
        response = await self._send_request(child, "tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if "error" in response:
            return [TextContent(type="text", text=f"Error: {response['error'].get('message', 'Unknown error')}")]
        
        if "result" in response:
            content = response["result"].get("content", [])
            return [TextContent(type="text", text=c.get("text", "")) for c in content if c.get("type") == "text"]
        
        return [TextContent(type="text", text="No response")]
    
    async def stop_all(self):
        """Stop all child processes."""
        for child in self.children.values():
            if child.read_task:
                child.read_task.cancel()
            if child.process:
                child.process.terminate()
                await child.process.wait()


# Global multiplexer instance
multiplexer = HTTPMultiplexer()
sse_transport = SseServerTransport("/messages/")


@asynccontextmanager
async def lifespan(app):
    """Application lifespan context manager."""
    logger.info("Starting HTTP Multiplexer...")
    
    # Start demo-recorder MCP
    await multiplexer.start_child(
        "demo-recorder",
        ["python", "-m", "recorder.server"]
    )
    
    # Start Playwright MCP
    try:
        await multiplexer.start_child(
            "playwright",
            ["npx", "@playwright/mcp"]
        )
    except Exception as e:
        logger.warning(f"Failed to start Playwright MCP: {e}")
    
    logger.info(f"HTTP Multiplexer ready with {len(multiplexer._all_tools)} tools")
    
    yield
    
    logger.info("Shutting down HTTP Multiplexer...")
    await multiplexer.stop_all()


async def handle_sse(request):
    """Handle SSE connection."""
    logger.info(f"New SSE connection from {request.client.host}")
    
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await multiplexer.server.run(
            streams[0],
            streams[1],
            multiplexer.server.create_initialization_options()
        )


async def handle_messages(request):
    """Handle MCP messages via POST."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def health_check(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-http-multiplexer",
        "tools_count": len(multiplexer._all_tools),
        "children": list(multiplexer.children.keys())
    })


async def info(request):
    """Info endpoint."""
    return JSONResponse({
        "name": "demo-recorder-mcp",
        "description": "MCP server for browser automation, video recording, and TTS",
        "transport": "sse",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages/",
            "health": "/health"
        },
        "tools_count": len(multiplexer._all_tools)
    })


async def tools_list(request):
    """List all available tools."""
    tools = [
        {
            "name": t.name,
            "description": t.description,
        }
        for t in multiplexer._all_tools
    ]
    return JSONResponse({"tools": tools, "count": len(tools)})


app = Starlette(
    debug=os.environ.get("DEBUG", "false").lower() == "true",
    lifespan=lifespan,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages/", endpoint=handle_messages, methods=["POST"]),
        Route("/health", endpoint=health_check),
        Route("/tools", endpoint=tools_list),
        Route("/", endpoint=info),
    ],
)


def main():
    """Run the HTTP multiplexer server."""
    import uvicorn
    
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    logger.info(f"Starting MCP HTTP Multiplexer on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()

