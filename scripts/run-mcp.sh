#!/bin/bash
# Run MCP server(s) based on argument
#
# Usage:
#   run-mcp.sh playwright     - Start Playwright MCP only
#   run-mcp.sh demo-recorder  - Start demo-recorder MCP only
#   run-mcp.sh multi          - Start multiplexer (RECOMMENDED - exposes all tools)

case "$1" in
    "playwright")
        # Playwright MCP with Firefox (ARM64 compatible)
        exec npx @playwright/mcp --browser firefox
        ;;
    "demo-recorder")
        # Demo recorder MCP only
        exec recorder
        ;;
    "multi"|"")
        # Multiplexer mode (default) - runs both MCPs and exposes all tools
        exec recorder-proxy
        ;;
    *)
        echo "Usage: run-mcp.sh [playwright|demo-recorder|multi]" >&2
        echo "  playwright     - Start Playwright MCP server only" >&2
        echo "  demo-recorder  - Start demo-recorder MCP server only" >&2
        echo "  multi          - Start multiplexer with all tools (default)" >&2
        exit 1
        ;;
esac
