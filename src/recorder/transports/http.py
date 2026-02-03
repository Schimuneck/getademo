#!/usr/bin/env python3
"""
HTTP/SSE Server for Demo Recorder MCP

Exposes the MCP server over HTTP using Server-Sent Events (SSE) transport.
This allows remote clients to connect to the MCP server over the internet.

Uses FastMCP's built-in SSE transport which handles the protocol correctly.

Usage:
    python -m recorder.http_server
    # or
    uv run recorder-http
"""

import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run the HTTP server using FastMCP's SSE transport."""
    from recorder.server import mcp
    
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8080"))
    
    logger.info(f"Starting Demo Recorder MCP HTTP Server on {host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info("Using FastMCP built-in SSE transport")
    
    # FastMCP handles all the SSE protocol details
    mcp.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
