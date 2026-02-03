"""
Window management tools - list and manage windows.
"""


def register_window_tools(mcp):
    """Register window management tools with the MCP server."""
    
    @mcp.tool(description="List all windows in the display. Call after browser_navigate().")
    async def list_windows() -> str:
        """List all visible windows."""
        from ..utils.window_manager import (
            list_windows as _list_windows,
            DependencyMissingError,
            WindowManagerError,
        )
        
        try:
            windows = _list_windows()
            
            if not windows:
                return "No visible windows found."
            
            output = f"Found {len(windows)} visible windows:\n\n"
            for i, win in enumerate(windows, 1):
                output += f"{i}. {win.title}\n"
                if win.app_name:
                    output += f"   App: {win.app_name}\n"
                output += f"   ID: {win.window_id}\n"
                if win.pid:
                    output += f"   PID: {win.pid}\n"
                if win.bounds:
                    output += f"   Bounds: x={win.bounds.x}, y={win.bounds.y}, "
                    output += f"w={win.bounds.width}, h={win.bounds.height}\n"
                output += "\n"
            
            return output
        
        except DependencyMissingError as e:
            return f"Missing dependencies: {str(e)}"
        except WindowManagerError as e:
            return f"Error listing windows: {str(e)}"
    
    @mcp.tool(description="Check availability of window management tools (wmctrl, xdotool).")
    async def window_tools() -> str:
        """Check window management tool availability."""
        from ..utils.window_manager import check_dependencies
        
        deps = check_dependencies()
        
        output = f"Window Management Tools Status\n"
        output += f"{'=' * 40}\n\n"
        output += f"Platform: {deps['platform']}\n"
        output += f"Available: {'Yes' if deps['available'] else 'No'}\n"
        output += f"Message: {deps['message']}\n"
        
        if deps['missing']:
            output += f"\nMissing tools: {', '.join(deps['missing'])}\n"
            
            if deps['platform'] == 'linux':
                output += f"\nTo install:\n"
                output += f"  Ubuntu/Debian: sudo apt install wmctrl xdotool\n"
                output += f"  Fedora/RHEL:   sudo dnf install wmctrl xdotool\n"
                output += f"  Arch:          sudo pacman -S wmctrl xdotool\n"
        
        return output
