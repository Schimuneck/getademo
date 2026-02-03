#!/usr/bin/env python3
"""
demo-recorder - FastMCP Server for Demo Recording

Provides tools for:
- Screen recording (start/stop)
- Text-to-speech generation (OpenAI or Edge TTS)
- Video/audio composition (merge, replace audio, trim)

Supports two operational modes:
- Container mode: Docker/Podman with Xvfb and Playwright
- Host mode: Native execution with cursor-browser-extension

IMPORTANT: To create a demo, ALWAYS start with planning_phase_1() tool first!
"""

from fastmcp import FastMCP

from .backends import get_backend
from .tools import register_all_tools

# Create the FastMCP server with instructions for the LLM
mcp = FastMCP(
    "demo-recorder",
    stateless_http=True,
    instructions="""Demo Recorder MCP Server - Creates professional demo videos.

IMPORTANT: To create a demo, ALWAYS call planning_phase_1() FIRST!

The workflow follows 4 phases:
1. planning_phase_1() - Plan the demo structure and scenes
2. setup_phase_2() - Prepare browser and environment  
3. recording_phase_3() - Record scenes with narration
4. editing_phase_4() - Assemble final video

Never skip phases. Each phase guide provides detailed instructions."""
)

# Auto-select backend based on environment
backend = get_backend()

# Register all tools
register_all_tools(mcp, backend)


# =============================================================================
# Entry Points
# =============================================================================

def run():
    """Entry point for STDIO transport (default)."""
    mcp.run()


def main():
    """Entry point for HTTP transport."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    run()
