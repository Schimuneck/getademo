#!/bin/bash
# Demo Recorder MCP installer
# Installs dependencies, configures environment, and sets up Cursor MCP

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║           Demo Recorder MCP Installer v0.2.0              ║"
echo "║      MCP Server for Professional Demo Recording           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    OS="macos" ;;
        Linux*)     OS="linux" ;;
        MINGW*|CYGWIN*|MSYS*) OS="windows" ;;
        *)          OS="unknown" ;;
    esac
    info "Detected OS: $OS"
}

# Check Python version
check_python() {
    info "Checking Python installation..."
    
    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "Python not found. Please install Python 3.10 or higher."
        echo ""
        echo "Installation instructions:"
        case "$OS" in
            macos)  echo "  brew install python@3.12" ;;
            linux)  echo "  sudo apt install python3 python3-venv python3-pip" ;;
            *)      echo "  Download from https://www.python.org/downloads/" ;;
        esac
        exit 1
    fi
    
    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        error "Python 3.10+ required. Found: Python $PYTHON_VERSION"
        exit 1
    fi
    
    success "Python $PYTHON_VERSION found ($PYTHON_CMD)"
}

# Check and install ffmpeg
check_ffmpeg() {
    info "Checking ffmpeg installation..."
    
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n1 | grep -o 'ffmpeg version [^ ]*' | cut -d' ' -f3)
        success "ffmpeg found: $FFMPEG_VERSION"
        return 0
    fi
    
    warn "ffmpeg not found. ffmpeg is required for screen recording and video editing."
    echo ""
    
    read -p "Would you like to install ffmpeg now? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Installing ffmpeg..."
        case "$OS" in
            macos)
                if command -v brew &> /dev/null; then
                    brew install ffmpeg
                else
                    error "Homebrew not found. Please install Homebrew first: https://brew.sh"
                    exit 1
                fi
                ;;
            linux)
                if command -v apt &> /dev/null; then
                    sudo apt update && sudo apt install -y ffmpeg
                elif command -v dnf &> /dev/null; then
                    sudo dnf install -y ffmpeg
                elif command -v pacman &> /dev/null; then
                    sudo pacman -S ffmpeg
                else
                    error "Could not detect package manager. Please install ffmpeg manually."
                    exit 1
                fi
                ;;
            *)
                error "Please install ffmpeg manually: https://ffmpeg.org/download.html"
                exit 1
                ;;
        esac
        success "ffmpeg installed successfully"
    else
        warn "Skipping ffmpeg installation. Some features may not work."
    fi
}

# Check and install window management tools
check_window_tools() {
    info "Checking window management tools..."
    
    case "$OS" in
        macos)
            # macOS uses built-in osascript (AppleScript) - no extra deps needed
            success "macOS: Using built-in AppleScript (osascript)"
            ;;
        linux)
            # Linux needs wmctrl and xdotool for window management
            MISSING_TOOLS=()
            
            if ! command -v wmctrl &> /dev/null; then
                MISSING_TOOLS+=("wmctrl")
            fi
            if ! command -v xdotool &> /dev/null; then
                MISSING_TOOLS+=("xdotool")
            fi
            
            if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
                warn "Missing window management tools: ${MISSING_TOOLS[*]}"
                echo ""
                echo "These tools are needed for window-based recording."
                echo ""
                
                read -p "Would you like to install them now? (y/n) " -n 1 -r
                echo ""
                
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    info "Installing window management tools..."
                    if command -v apt &> /dev/null; then
                        sudo apt update && sudo apt install -y wmctrl xdotool
                    elif command -v dnf &> /dev/null; then
                        sudo dnf install -y wmctrl xdotool
                    elif command -v pacman &> /dev/null; then
                        sudo pacman -S --noconfirm wmctrl xdotool
                    elif command -v zypper &> /dev/null; then
                        sudo zypper install -y wmctrl xdotool
                    else
                        warn "Could not detect package manager. Please install manually:"
                        echo "  wmctrl xdotool"
                    fi
                    
                    # Verify installation
                    if command -v wmctrl &> /dev/null && command -v xdotool &> /dev/null; then
                        success "Window management tools installed successfully"
                    else
                        warn "Some tools may not have installed correctly."
                    fi
                else
                    warn "Skipping window tools installation."
                fi
            else
                success "Linux: wmctrl and xdotool are available"
            fi
            ;;
        windows)
            # Windows uses built-in ctypes (Win32 API) - no extra deps needed
            success "Windows: Using built-in Win32 API (ctypes)"
            ;;
        *)
            warn "Unknown OS: Window management tools may not work."
            ;;
    esac
}

# Create virtual environment and install package
install_package() {
    info "Setting up Python virtual environment..."
    
    # Create venv if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        $PYTHON_CMD -m venv "$VENV_DIR"
        success "Virtual environment created at $VENV_DIR"
    else
        info "Virtual environment already exists"
    fi
    
    # Activate venv
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    info "Upgrading pip..."
    pip install --upgrade pip -q
    
    # Install package
    info "Installing demo-recorder-mcp with all dependencies..."
    pip install -e "$SCRIPT_DIR[all]" -q
    
    success "demo-recorder-mcp installed successfully"
    
    # Verify installation
    if [ -f "$VENV_DIR/bin/recorder" ]; then
        success "recorder command is available"
    else
        warn "recorder command not found, but package may still be installed"
    fi
}

# Configure Cursor MCP
configure_cursor() {
    info "Configuring Cursor MCP..."
    
    # Detect Cursor config location
    case "$OS" in
        macos)
            CURSOR_CONFIG_DIR="$HOME/.cursor"
            ;;
        linux)
            CURSOR_CONFIG_DIR="$HOME/.cursor"
            ;;
        windows)
            CURSOR_CONFIG_DIR="$APPDATA/Cursor"
            ;;
        *)
            CURSOR_CONFIG_DIR="$HOME/.cursor"
            ;;
    esac
    
    MCP_CONFIG="$CURSOR_CONFIG_DIR/mcp.json"
    RECORDER_CMD="$VENV_DIR/bin/recorder"
    RECORDINGS_DIR="$HOME/recordings"
    
    # Create recordings directory
    mkdir -p "$RECORDINGS_DIR"
    
    # Check if Cursor config directory exists
    if [ ! -d "$CURSOR_CONFIG_DIR" ]; then
        warn "Cursor config directory not found at $CURSOR_CONFIG_DIR"
        warn "Please make sure Cursor IDE is installed."
        echo ""
        echo "After installing Cursor, add this to your MCP config ($MCP_CONFIG):"
        echo ""
        echo '{'
        echo '  "mcpServers": {'
        echo '    "demo-recorder-local": {'
        echo "      \"command\": \"$RECORDER_CMD\","
        echo '      "env": {'
        echo '        "OPENAI_API_KEY": "your-api-key-here",'
        echo "        \"RECORDINGS_DIR\": \"$RECORDINGS_DIR\""
        echo '      }'
        echo '    }'
        echo '  }'
        echo '}'
        return 0
    fi
    
    # Create config directory if needed
    mkdir -p "$CURSOR_CONFIG_DIR"
    
    # Check if mcp.json exists
    if [ -f "$MCP_CONFIG" ]; then
        # Check if demo-recorder is already configured
        if grep -q '"demo-recorder-local"' "$MCP_CONFIG" 2>/dev/null; then
            info "demo-recorder-local is already configured in Cursor"
            read -p "Would you like to update the configuration? (y/n) " -n 1 -r
            echo ""
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                info "Keeping existing configuration"
                return 0
            fi
        fi
        
        # Backup existing config
        cp "$MCP_CONFIG" "$MCP_CONFIG.backup"
        info "Backed up existing config to $MCP_CONFIG.backup"
    fi
    
    # Ask for OpenAI API key
    echo ""
    info "OpenAI API key is optional but recommended for high-quality TTS."
    info "You can also use Edge TTS (free) without an API key."
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
    
    if [ -z "$OPENAI_KEY" ]; then
        OPENAI_KEY=""
        warn "No API key provided. Edge TTS will be used (free)."
        warn "You can add your API key later to $MCP_CONFIG"
    fi
    
    # Create or update mcp.json
    if [ -f "$MCP_CONFIG" ]; then
        # Use Python to safely update JSON
        $PYTHON_CMD << EOF
import json
import os

config_path = "$MCP_CONFIG"
recorder_cmd = "$RECORDER_CMD"
openai_key = "$OPENAI_KEY"
recordings_dir = "$RECORDINGS_DIR"

# Read existing config
with open(config_path, 'r') as f:
    config = json.load(f)

# Ensure mcpServers exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add/update demo-recorder-local
env_config = {"RECORDINGS_DIR": recordings_dir}
if openai_key:
    env_config["OPENAI_API_KEY"] = openai_key

config['mcpServers']['demo-recorder-local'] = {
    "command": recorder_cmd,
    "env": env_config
}

# Write updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
EOF
    else
        # Create new config
        if [ -n "$OPENAI_KEY" ]; then
            cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "demo-recorder-local": {
      "command": "$RECORDER_CMD",
      "env": {
        "OPENAI_API_KEY": "$OPENAI_KEY",
        "RECORDINGS_DIR": "$RECORDINGS_DIR"
      }
    }
  }
}
EOF
        else
            cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "demo-recorder-local": {
      "command": "$RECORDER_CMD",
      "env": {
        "RECORDINGS_DIR": "$RECORDINGS_DIR"
      }
    }
  }
}
EOF
        fi
    fi
    
    success "Cursor MCP configured at $MCP_CONFIG"
}

# Grant screen recording permission (macOS)
check_screen_permission() {
    if [ "$OS" != "macos" ]; then
        return 0
    fi
    
    echo ""
    warn "IMPORTANT: Screen Recording Permission Required"
    echo ""
    echo "On macOS, you need to grant screen recording permission:"
    echo ""
    echo "  1. Open System Settings -> Privacy & Security -> Screen Recording"
    echo "  2. Click the '+' button"
    echo "  3. Add 'Cursor' (or your terminal app)"
    echo "  4. Restart Cursor after granting permission"
    echo ""
    read -p "Press Enter to continue..."
}

# Print summary
print_summary() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║              Installation Complete!                       ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo ""
    success "demo-recorder-mcp has been installed and configured!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Cursor to load the MCP server"
    echo "  2. Ask the AI: 'Create a demo of [any website]'"
    echo ""
    echo "Configuration:"
    echo "  - Package: $SCRIPT_DIR"
    echo "  - Virtual env: $VENV_DIR"
    echo "  - Recordings: $HOME/recordings"
    echo "  - Cursor config: $CURSOR_CONFIG_DIR/mcp.json"
    echo ""
    echo "Available tools:"
    echo "  Recording:"
    echo "    - start_recording / stop_recording / recording_status"
    echo "  Audio:"
    echo "    - text_to_speech (OpenAI or Edge TTS)"
    echo "  Video Editing:"
    echo "    - adjust_video_to_audio / concatenate_videos / media_info"
    echo "  Protocol Guides:"
    echo "    - planning_phase_1 / setup_phase_2 / recording_phase_3 / editing_phase_4"
    echo "  Utility:"
    echo "    - list_windows / window_tools"
    echo ""
    echo "Documentation: https://github.com/Schimuneck/demo-recorder-mcp"
    echo ""
}

# Main installation flow
main() {
    detect_os
    check_python
    check_ffmpeg
    check_window_tools
    install_package
    configure_cursor
    check_screen_permission
    print_summary
}

# Run installer
main
