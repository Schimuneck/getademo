"""
Window management tools - list and manage windows.
"""

from ..core.config import is_container_environment


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
    
    # Only register fullscreen/maximize tools in host mode (not available in container)
    if not is_container_environment():
        @mcp.tool(description="Maximize browser window for demo recording. RECOMMENDED over fullscreen. HOST MODE ONLY. REQUIRES window_title parameter.")
        async def maximize_window(window_title: str = None) -> str:
            """Maximize a window to fill the screen (without entering fullscreen mode).
            
            RECOMMENDED for demo recording because:
            - Keeps window title consistent (doesn't change on navigation)
            - Stays in same Space/workspace on macOS
            - No fullscreen animation delay
            
            Args:
                window_title: REQUIRED. Window title pattern to match (e.g., 'Google Chrome', 'Firefox').
                             Use list_windows() to see available windows.
            
            Returns:
                Status message indicating success or failure.
            """
            from ..utils.window_manager import (
                maximize_window as _maximize_window,
                WindowNotFoundError,
                WindowManagerError,
                get_platform,
            )
            
            # Require window_title to prevent operating on wrong window
            if not window_title:
                return (
                    "ERROR: window_title parameter is REQUIRED.\n\n"
                    "You must specify which window to maximize. Examples:\n"
                    "  maximize_window(window_title='Google Chrome')\n"
                    "  maximize_window(window_title='Firefox')\n"
                    "  maximize_window(window_title='Safari')\n\n"
                    "Use list_windows() to see all available windows and their exact names."
                )
            
            try:
                _maximize_window(window_title)
                platform = get_platform()
                
                return (
                    f"Window '{window_title}' maximized.\n"
                    f"Window will fill the screen while staying in the same Space.\n"
                    f"The window title will remain consistent during navigation."
                )
                    
            except WindowNotFoundError as e:
                return f"Window not found: {str(e)}\nTip: Run list_windows() to see available windows."
            except WindowManagerError as e:
                return f"Error: {str(e)}"
        
        # NOTE: fullscreen_window tool disabled - use maximize_window instead
        # Native fullscreen mode on macOS causes issues:
        # - Creates separate Space with inconsistent window titles
        # - Requires animation delay before recording
        # The maximize_window tool is the recommended approach.
