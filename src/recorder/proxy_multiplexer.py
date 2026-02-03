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
from dataclasses import dataclass, field
from typing import Any, Optional

# Import the FastMCP instance from server.py - it already has all demo-recorder tools registered
from .server import mcp as proxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        response = await asyncio.wait_for(future, timeout=60)
        return response
    except asyncio.TimeoutError:
        _playwright.pending_requests.pop(request_id, None)
        raise TimeoutError(f"Timeout waiting for {method} from Playwright")


async def _start_playwright():
    """Start the Playwright MCP child process."""
    global _playwright
    
    logger.info("Starting Playwright MCP...")
    
    _playwright = PlaywrightChild()
    
    # Start Playwright MCP process
    _playwright.process = await asyncio.create_subprocess_exec(
        "npx", "@playwright/mcp",
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
# Playwright Tool Proxies - Add to the FastMCP server
# =============================================================================

# Define Playwright tool proxies with their original descriptions
# These wrap the Playwright MCP tools and forward calls to the child process

@proxy.tool(description="Close the page")
async def browser_close() -> str:
    return await _call_playwright_tool("browser_close", {})


@proxy.tool(description="Resize the browser window")
async def browser_resize(width: int, height: int) -> str:
    return await _call_playwright_tool("browser_resize", {"width": width, "height": height})


@proxy.tool(description="Returns all console messages")
async def browser_console_messages(level: str = "info", filename: str = None) -> str:
    args = {"level": level}
    if filename:
        args["filename"] = filename
    return await _call_playwright_tool("browser_console_messages", args)


@proxy.tool(description="Handle a dialog")
async def browser_handle_dialog(accept: bool, promptText: str = None) -> str:
    args = {"accept": accept}
    if promptText:
        args["promptText"] = promptText
    return await _call_playwright_tool("browser_handle_dialog", args)


@proxy.tool(description="Evaluate JavaScript expression on page or element")
async def browser_evaluate(function: str, element: str = None, ref: str = None) -> str:
    args = {"function": function}
    if element:
        args["element"] = element
    if ref:
        args["ref"] = ref
    return await _call_playwright_tool("browser_evaluate", args)


@proxy.tool(description="Upload one or multiple files")
async def browser_file_upload(paths: list[str] = None) -> str:
    args = {}
    if paths:
        args["paths"] = paths
    return await _call_playwright_tool("browser_file_upload", args)


@proxy.tool(description="Fill multiple form fields")
async def browser_fill_form(fields: list[dict]) -> str:
    return await _call_playwright_tool("browser_fill_form", {"fields": fields})


@proxy.tool(description="Install the browser specified in the config")
async def browser_install() -> str:
    return await _call_playwright_tool("browser_install", {})


@proxy.tool(description="Press a key on the keyboard")
async def browser_press_key(key: str) -> str:
    return await _call_playwright_tool("browser_press_key", {"key": key})


@proxy.tool(description="Type text into editable element")
async def browser_type(ref: str, text: str, element: str = None, slowly: bool = None, submit: bool = None) -> str:
    args = {"ref": ref, "text": text}
    if element:
        args["element"] = element
    if slowly is not None:
        args["slowly"] = slowly
    if submit is not None:
        args["submit"] = submit
    return await _call_playwright_tool("browser_type", args)


@proxy.tool(description="Navigate to a URL")
async def browser_navigate(url: str) -> str:
    return await _call_playwright_tool("browser_navigate", {"url": url})


@proxy.tool(description="Go back to the previous page in the history")
async def browser_navigate_back() -> str:
    return await _call_playwright_tool("browser_navigate_back", {})


@proxy.tool(description="Returns all network requests since loading the page")
async def browser_network_requests(includeStatic: bool = False, filename: str = None) -> str:
    args = {"includeStatic": includeStatic}
    if filename:
        args["filename"] = filename
    return await _call_playwright_tool("browser_network_requests", args)


@proxy.tool(description="Run Playwright code snippet")
async def browser_run_code(code: str) -> str:
    return await _call_playwright_tool("browser_run_code", {"code": code})


@proxy.tool(description="Take a screenshot of the current page")
async def browser_take_screenshot(type: str = "png", element: str = None, ref: str = None, filename: str = None, fullPage: bool = None) -> str:
    args = {"type": type}
    if element:
        args["element"] = element
    if ref:
        args["ref"] = ref
    if filename:
        args["filename"] = filename
    if fullPage is not None:
        args["fullPage"] = fullPage
    return await _call_playwright_tool("browser_take_screenshot", args)


@proxy.tool(description="Capture accessibility snapshot of the current page, this is better than screenshot")
async def browser_snapshot(filename: str = None) -> str:
    args = {}
    if filename:
        args["filename"] = filename
    return await _call_playwright_tool("browser_snapshot", args)


@proxy.tool(description="Perform click on a web page")
async def browser_click(ref: str, element: str = None, button: str = None, doubleClick: bool = None, modifiers: list[str] = None) -> str:
    args = {"ref": ref}
    if element:
        args["element"] = element
    if button:
        args["button"] = button
    if doubleClick is not None:
        args["doubleClick"] = doubleClick
    if modifiers:
        args["modifiers"] = modifiers
    return await _call_playwright_tool("browser_click", args)


@proxy.tool(description="Perform drag and drop between two elements")
async def browser_drag(startElement: str, startRef: str, endElement: str, endRef: str) -> str:
    return await _call_playwright_tool("browser_drag", {
        "startElement": startElement,
        "startRef": startRef,
        "endElement": endElement,
        "endRef": endRef
    })


@proxy.tool(description="Hover over element on page")
async def browser_hover(ref: str, element: str = None) -> str:
    args = {"ref": ref}
    if element:
        args["element"] = element
    return await _call_playwright_tool("browser_hover", args)


@proxy.tool(description="Select an option in a dropdown")
async def browser_select_option(ref: str, values: list[str], element: str = None) -> str:
    args = {"ref": ref, "values": values}
    if element:
        args["element"] = element
    return await _call_playwright_tool("browser_select_option", args)


@proxy.tool(description="List, create, close, or select a browser tab")
async def browser_tabs(action: str, index: int = None) -> str:
    args = {"action": action}
    if index is not None:
        args["index"] = index
    return await _call_playwright_tool("browser_tabs", args)


@proxy.tool(description="Wait for text to appear or disappear or a specified time to pass")
async def browser_wait_for(text: str = None, textGone: str = None, time: int = None) -> str:
    args = {}
    if text:
        args["text"] = text
    if textGone:
        args["textGone"] = textGone
    if time is not None:
        args["time"] = time
    return await _call_playwright_tool("browser_wait_for", args)


# =============================================================================
# Custom Routes
# =============================================================================

# Add health endpoint
@proxy.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint."""
    from starlette.responses import JSONResponse
    tools = await proxy.get_tools()
    return JSONResponse({
        "status": "healthy",
        "service": "demo-recorder-mcp",
        "tools_count": len(tools)
    })


# Add info endpoint
@proxy.custom_route("/", methods=["GET"])
async def info(request):
    """Server info endpoint."""
    from starlette.responses import JSONResponse
    tools = await proxy.get_tools()
    return JSONResponse({
        "name": "demo-recorder-mcp",
        "description": "MCP server for browser automation, video recording, and TTS",
        "transport": "streamable-http",
        "endpoints": {
            "mcp": "/mcp/",
            "health": "/health"
        },
        "tools_count": len(tools)
    })


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the proxy multiplexer server."""
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    logger.info(f"Starting MCP Proxy Multiplexer on {host}:{port}")
    logger.info("Using streamable-HTTP transport at /mcp/ for OpenAI compatibility")
    logger.info("See: https://gofastmcp.com/integrations/openai")
    
    # Start Playwright child process before running the server
    async def startup():
        try:
            await _start_playwright()
        except Exception as e:
            logger.warning(f"Failed to start Playwright MCP: {e}")
            logger.warning("Playwright tools will not be available")
    
    async def shutdown():
        await _stop_playwright()
    
    # Run startup before server
    asyncio.get_event_loop().run_until_complete(startup())
    
    try:
        # Use HTTP transport (streamable-http) - required for OpenAI Responses API
        # OpenAI's MCP client requires streamable-HTTP, NOT SSE
        proxy.run(transport="http", host=host, port=port)
    finally:
        asyncio.get_event_loop().run_until_complete(shutdown())


if __name__ == "__main__":
    main()
