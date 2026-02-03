"""
Guide tools - protocol phase guides for demo recording workflow.

To create a demo, ALWAYS start with planning_phase_1() first!
"""


def register_guide_tools(mcp):
    """Register guide tools with the MCP server."""
    
    @mcp.tool(description="START HERE! Phase 1: Demo planning. ALWAYS call this FIRST when asked to create a demo. Returns the planning guide with instructions.")
    async def planning_phase_1() -> str:
        """Get phase 1 planning guide. MUST be called first for any demo creation."""
        from ..utils.protocol import get_planning_guide
        return get_planning_guide()
    
    @mcp.tool(description="Phase 2: Pre-recording setup. Call AFTER planning_phase_1 is complete.")
    async def setup_phase_2() -> str:
        """Get phase 2 setup guide."""
        from ..utils.protocol import get_setup_guide
        return get_setup_guide()
    
    @mcp.tool(description="Phase 3: Recording guide. Call AFTER setup_phase_2 is complete.")
    async def recording_phase_3() -> str:
        """Get phase 3 recording guide."""
        from ..utils.protocol import get_recording_guide
        return get_recording_guide()
    
    @mcp.tool(description="Phase 4: Final assembly. Call AFTER all scenes are recorded in phase 3.")
    async def editing_phase_4() -> str:
        """Get phase 4 editing guide."""
        from ..utils.protocol import get_assembly_guide
        return get_assembly_guide()
