#!/usr/bin/env python3
"""
FastMCP Proxy Multiplexer

Combines demo-recorder tools (from server.py) with Playwright MCP tools
and exposes them all through a single FastMCP HTTP endpoint.

This is the main entry point for the HTTP container - it provides:
- All 13 demo-recorder tools (recording, TTS, video editing, guides, window mgmt)
- All 22+ Playwright MCP tools (browser automation)
= 35+ total tools available via streamable-HTTP at /mcp/

OpenAI's Responses API requires streamable-HTTP transport (not SSE).
See: https://gofastmcp.com/integrations/openai

Usage:
    python -m recorder.proxy_multiplexer
    # or
    uv run recorder-proxy
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Optional

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholder for the proxy - will be created in main() with lifespan
proxy: Optional[FastMCP] = None


@dataclass
class PlaywrightChild:
    """Represents the Playwright MCP child process."""
    process: Optional[asyncio.subprocess.Process] = None
    tools: dict[str, dict] = field(default_factory=dict)
    request_id: int = 0
    pending_requests: dict[int, asyncio.Future] = field(default_factory=dict)
    read_task: Optional[asyncio.Task] = None


# Global Playwright child process
_playwright: Optional[PlaywrightChild] = None


async def _read_playwright_output(child: PlaywrightChild):
    """Background task to read output from Playwright MCP."""
    try:
        while True:
            if child.process is None or child.process.stdout is None:
                logger.warning("Playwright stdout reader: process or stdout is None")
                break
            
            line = await child.process.stdout.readline()
            if not line:
                logger.warning("Playwright stdout reader: empty line (EOF)")
                break
            
            try:
                response = json.loads(line.decode())
                request_id = response.get("id")
                logger.debug(f"Playwright response: id={request_id}")
                
                if request_id and request_id in child.pending_requests:
                    future = child.pending_requests.pop(request_id)
                    if not future.done():
                        future.set_result(response)
                elif request_id:
                    logger.warning(f"Received response for unknown request id: {request_id}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error from Playwright: {e}, line: {line[:100]}")
    except asyncio.CancelledError:
        logger.info("Playwright stdout reader cancelled")
    except Exception as e:
        logger.error(f"Error reading from Playwright: {e}")


async def _send_playwright_request(method: str, params: dict = None) -> dict:
    """Send JSON-RPC request to Playwright MCP."""
    global _playwright
    
    if _playwright is None or _playwright.process is None or _playwright.process.stdin is None:
        raise RuntimeError("Playwright MCP not running")
    
    _playwright.request_id += 1
    request_id = _playwright.request_id
    
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
    }
    if params:
        request["params"] = params
    
    future = asyncio.get_event_loop().create_future()
    _playwright.pending_requests[request_id] = future
    
    request_line = json.dumps(request) + "\n"
    _playwright.process.stdin.write(request_line.encode())
    await _playwright.process.stdin.drain()
    
    try:
        # Increase timeout for browser operations
        timeout = 120 if method == "tools/call" else 60
        logger.debug(f"Waiting for {method} (id={request_id}) with timeout={timeout}")
        response = await asyncio.wait_for(future, timeout=timeout)
        return response
    except asyncio.TimeoutError:
        _playwright.pending_requests.pop(request_id, None)
        # Check if process is still alive
        if _playwright.process and _playwright.process.returncode is not None:
            logger.error(f"Playwright process died with code {_playwright.process.returncode}")
        raise TimeoutError(f"Timeout waiting for {method} from Playwright")


async def _start_playwright():
    """Start the Playwright MCP child process."""
    global _playwright
    
    logger.info("Starting Playwright MCP...")
    
    _playwright = PlaywrightChild()
    
    # Start Playwright MCP process with Firefox (more reliable in containers)
    browser = os.environ.get("PLAYWRIGHT_BROWSER", "firefox")
    _playwright.process = await asyncio.create_subprocess_exec(
        "npx", "@playwright/mcp", "--browser", browser,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "CONTAINER": os.environ.get("CONTAINER", "docker")},
    )
    
    # Start background reader
    _playwright.read_task = asyncio.create_task(_read_playwright_output(_playwright))
    
    # Initialize MCP connection
    await _send_playwright_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "proxy-multiplexer", "version": "1.0.0"}
    })
    
    # Send initialized notification
    if _playwright.process and _playwright.process.stdin:
        notif = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"
        _playwright.process.stdin.write(notif.encode())
        await _playwright.process.stdin.drain()
    
    # Get tools list
    response = await _send_playwright_request("tools/list", {})
    
    if "result" in response and "tools" in response["result"]:
        for tool in response["result"]["tools"]:
            _playwright.tools[tool["name"]] = tool
    
    logger.info(f"Playwright MCP started with {len(_playwright.tools)} tools")


async def _call_playwright_tool(tool_name: str, arguments: dict) -> str:
    """Call a tool on Playwright MCP and return the result."""
    response = await _send_playwright_request("tools/call", {
        "name": tool_name,
        "arguments": arguments
    })
    
    if "error" in response:
        return f"Error: {response['error'].get('message', 'Unknown error')}"
    
    if "result" in response:
        content = response["result"].get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        return "\n".join(texts) if texts else "No response"
    
    return "No response"


async def _stop_playwright():
    """Stop the Playwright MCP child process."""
    global _playwright
    
    if _playwright:
        if _playwright.read_task:
            _playwright.read_task.cancel()
        if _playwright.process:
            _playwright.process.terminate()
            await _playwright.process.wait()
        _playwright = None


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the proxy multiplexer server."""
    global proxy
    
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    logger.info(f"Starting MCP Proxy Multiplexer on {host}:{port}")
    logger.info("Using streamable-HTTP transport at /mcp/ for OpenAI compatibility")
    logger.info("See: https://gofastmcp.com/integrations/openai")
    
    # Create lifespan context manager for starting/stopping Playwright
    @asynccontextmanager
    async def lifespan(app):
        """Lifespan context manager for the FastMCP server."""
        # Startup
        logger.info("Starting Playwright MCP in lifespan...")
        try:
            await _start_playwright()
            logger.info("Playwright MCP started successfully")
        except Exception as e:
            logger.warning(f"Failed to start Playwright MCP: {e}")
            logger.warning("Playwright tools will not be available")
        
        yield  # Server is running
        
        # Shutdown
        logger.info("Shutting down Playwright MCP...")
        await _stop_playwright()
        logger.info("Playwright MCP stopped")
    
    # Create the FastMCP server with lifespan
    proxy = FastMCP("demo-recorder", stateless_http=True, lifespan=lifespan)
    
    # Import and register all demo-recorder tools from server.py
    from .server import mcp as demo_recorder_mcp
    
    # Copy tools from demo-recorder to proxy
    async def copy_tools():
        tools_dict = await demo_recorder_mcp.get_tools()
        for tool_name, tool in tools_dict.items():
            proxy.add_tool(tool)
        logger.info(f"Copied {len(tools_dict)} tools from demo-recorder")
    
    # Run the copy in a new event loop (since we're not in async context)
    asyncio.get_event_loop().run_until_complete(copy_tools())
    
    # Register Playwright tool proxies
    _register_playwright_tools(proxy)
    
    # Add custom routes
    _register_custom_routes(proxy)
    
    # Use HTTP transport (streamable-http) - required for OpenAI Responses API
    # path="/mcp/" with trailing slash to match OpenAI's expected URL format
    # json_response=True for clients that only accept application/json
    # See: https://gofastmcp.com/integrations/openai
    proxy.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp/",
        json_response=True,
    )


def _register_playwright_tools(mcp_instance: FastMCP):
    """Register all Playwright tool proxies on the given FastMCP instance."""
    
    @mcp_instance.tool
    async def browser_close() -> str:
        """Close the page."""
        return await _call_playwright_tool("browser_close", {})

    @mcp_instance.tool
    async def browser_resize(width: int, height: int) -> str:
        """Resize the browser window."""
        return await _call_playwright_tool("browser_resize", {"width": width, "height": height})

    @mcp_instance.tool
    async def browser_console_messages(level: str = "info", filename: str = None) -> str:
        """Returns all console messages."""
        args = {"level": level}
        if filename:
            args["filename"] = filename
        return await _call_playwright_tool("browser_console_messages", args)

    @mcp_instance.tool
    async def browser_handle_dialog(accept: bool, promptText: str = None) -> str:
        """Handle a dialog."""
        args = {"accept": accept}
        if promptText:
            args["promptText"] = promptText
        return await _call_playwright_tool("browser_handle_dialog", args)

    @mcp_instance.tool
    async def browser_evaluate(function: str, element: str = None, ref: str = None) -> str:
        """Evaluate JavaScript expression on page or element."""
        args = {"function": function}
        if element:
            args["element"] = element
        if ref:
            args["ref"] = ref
        return await _call_playwright_tool("browser_evaluate", args)

    @mcp_instance.tool
    async def browser_file_upload(paths: list[str] = None) -> str:
        """Upload one or multiple files."""
        args = {}
        if paths:
            args["paths"] = paths
        return await _call_playwright_tool("browser_file_upload", args)

    @mcp_instance.tool
    async def browser_fill_form(fields: list[dict]) -> str:
        """Fill multiple form fields."""
        return await _call_playwright_tool("browser_fill_form", {"fields": fields})

    @mcp_instance.tool
    async def browser_install() -> str:
        """Install the browser specified in the config."""
        return await _call_playwright_tool("browser_install", {})

    @mcp_instance.tool
    async def browser_press_key(key: str) -> str:
        """Press a key on the keyboard."""
        return await _call_playwright_tool("browser_press_key", {"key": key})

    @mcp_instance.tool
    async def browser_type(ref: str, text: str, element: str = None, submit: bool = None, slowly: bool = None) -> str:
        """Type text into editable element."""
        args = {"ref": ref, "text": text}
        if element:
            args["element"] = element
        if submit is not None:
            args["submit"] = submit
        if slowly is not None:
            args["slowly"] = slowly
        return await _call_playwright_tool("browser_type", args)

    @mcp_instance.tool
    async def browser_navigate(url: str) -> str:
        """Navigate to a URL."""
        return await _call_playwright_tool("browser_navigate", {"url": url})

    @mcp_instance.tool
    async def browser_navigate_back() -> str:
        """Go back to the previous page in the history."""
        return await _call_playwright_tool("browser_navigate_back", {})

    @mcp_instance.tool
    async def browser_network_requests(includeStatic: bool = False, filename: str = None) -> str:
        """Returns all network requests since loading the page."""
        args = {"includeStatic": includeStatic}
        if filename:
            args["filename"] = filename
        return await _call_playwright_tool("browser_network_requests", args)

    @mcp_instance.tool
    async def browser_run_code(code: str) -> str:
        """Run Playwright code snippet."""
        return await _call_playwright_tool("browser_run_code", {"code": code})

    @mcp_instance.tool
    async def browser_take_screenshot(type: str = "png", filename: str = None, element: str = None, ref: str = None, fullPage: bool = None) -> str:
        """Take a screenshot of the current page."""
        args = {"type": type}
        if filename:
            args["filename"] = filename
        if element:
            args["element"] = element
        if ref:
            args["ref"] = ref
        if fullPage is not None:
            args["fullPage"] = fullPage
        return await _call_playwright_tool("browser_take_screenshot", args)

    @mcp_instance.tool
    async def browser_snapshot(filename: str = None) -> str:
        """Capture accessibility snapshot of the current page, this is better than screenshot."""
        args = {}
        if filename:
            args["filename"] = filename
        return await _call_playwright_tool("browser_snapshot", args)

    @mcp_instance.tool
    async def browser_click(ref: str, element: str = None, doubleClick: bool = None, button: str = None, modifiers: list[str] = None) -> str:
        """Perform click on a web page."""
        args = {"ref": ref}
        if element:
            args["element"] = element
        if doubleClick is not None:
            args["doubleClick"] = doubleClick
        if button:
            args["button"] = button
        if modifiers:
            args["modifiers"] = modifiers
        return await _call_playwright_tool("browser_click", args)

    @mcp_instance.tool
    async def browser_drag(startElement: str, startRef: str, endElement: str, endRef: str) -> str:
        """Perform drag and drop between two elements."""
        return await _call_playwright_tool("browser_drag", {
            "startElement": startElement,
            "startRef": startRef,
            "endElement": endElement,
            "endRef": endRef
        })

    @mcp_instance.tool
    async def browser_hover(ref: str, element: str = None) -> str:
        """Hover over element on page."""
        args = {"ref": ref}
        if element:
            args["element"] = element
        return await _call_playwright_tool("browser_hover", args)

    @mcp_instance.tool
    async def browser_select_option(ref: str, values: list[str], element: str = None) -> str:
        """Select an option in a dropdown."""
        args = {"ref": ref, "values": values}
        if element:
            args["element"] = element
        return await _call_playwright_tool("browser_select_option", args)

    @mcp_instance.tool
    async def browser_tabs(action: str, index: int = None) -> str:
        """List, create, close, or select a browser tab."""
        args = {"action": action}
        if index is not None:
            args["index"] = index
        return await _call_playwright_tool("browser_tabs", args)

    @mcp_instance.tool
    async def browser_wait_for(time: int = None, text: str = None, textGone: str = None) -> str:
        """Wait for text to appear or disappear or a specified time to pass."""
        args = {}
        if time is not None:
            args["time"] = time
        if text:
            args["text"] = text
        if textGone:
            args["textGone"] = textGone
        return await _call_playwright_tool("browser_wait_for", args)


def _register_custom_routes(mcp_instance: FastMCP):
    """Register custom HTTP routes on the given FastMCP instance."""
    
    @mcp_instance.custom_route("/health", methods=["GET"])
    async def health_check(request):
        """Health check endpoint."""
        from starlette.responses import JSONResponse
        tools = await mcp_instance.get_tools()
        return JSONResponse({
            "status": "healthy",
            "service": "demo-recorder-mcp",
            "tools_count": len(tools)
        })

    @mcp_instance.custom_route("/", methods=["GET"])
    async def info(request):
        """Server info endpoint."""
        from starlette.responses import JSONResponse
        tools = await mcp_instance.get_tools()
        return JSONResponse({
            "name": "demo-recorder-mcp",
            "description": "MCP server for browser automation, video recording, and TTS",
            "transport": "http",
            "endpoints": {
                "mcp": "/mcp/",
                "health": "/health"
            },
            "tools_count": len(tools)
        })


if __name__ == "__main__":
    main()
