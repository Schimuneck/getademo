#!/bin/bash
# Run MCP server(s) based on argument
#
# Usage:
#   run-mcp.sh playwright     - Start Playwright MCP only
#   run-mcp.sh demo-recorder  - Start demo-recorder MCP only (14 tools, STDIO)
#   run-mcp.sh multi-stdio    - Start multiplexer with STDIO (36 tools, for Cursor)
#   run-mcp.sh multi          - Start multiplexer with HTTP (36 tools, for OpenAI)

case "$1" in
    "playwright")
        # Playwright MCP with Firefox (ARM64 compatible)
        exec npx @playwright/mcp --browser firefox
        ;;
    "demo-recorder")
        # Demo recorder MCP only (14 tools)
        exec recorder
        ;;
    "multi-stdio")
        # Multiplexer mode with STDIO transport (all 36 tools for Cursor)
        export MCP_TRANSPORT=stdio
        exec recorder-proxy
        ;;
    "multi"|"")
        # Multiplexer mode with HTTP transport (default) - for OpenAI Responses API
        exec recorder-proxy
        ;;
    *)
        echo "Usage: run-mcp.sh [playwright|demo-recorder|multi-stdio|multi]" >&2
        echo "  playwright     - Start Playwright MCP server only" >&2
        echo "  demo-recorder  - Start demo-recorder MCP server only (14 tools)" >&2
        echo "  multi-stdio    - Start multiplexer with STDIO transport (36 tools)" >&2
        echo "  multi          - Start multiplexer with HTTP transport (default)" >&2
        exit 1
        ;;
esac
