#!/bin/bash
# getademo installer
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
echo "║              getademo Installer v0.1.0                    ║"
echo "║     MCP Server for Professional Demo Recording            ║"
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
    info "Installing getademo with all dependencies..."
    pip install -e "$SCRIPT_DIR[all]" -q
    
    success "getademo installed successfully"
    
    # Verify installation
    if command -v getademo &> /dev/null; then
        success "getademo command is available"
    else
        warn "getademo command not found in PATH, but package is installed"
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
    GETADEMO_CMD="$VENV_DIR/bin/getademo"
    
    # Check if Cursor config directory exists
    if [ ! -d "$CURSOR_CONFIG_DIR" ]; then
        warn "Cursor config directory not found at $CURSOR_CONFIG_DIR"
        warn "Please make sure Cursor IDE is installed."
        echo ""
        echo "After installing Cursor, add this to your MCP config ($MCP_CONFIG):"
        echo ""
        echo '{'
        echo '  "mcpServers": {'
        echo '    "getademo": {'
        echo "      \"command\": \"$GETADEMO_CMD\","
        echo '      "env": {'
        echo '        "OPENAI_API_KEY": "your-api-key-here"'
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
        # Check if getademo is already configured
        if grep -q '"getademo"' "$MCP_CONFIG" 2>/dev/null; then
            info "getademo is already configured in Cursor"
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
        OPENAI_KEY="your-api-key-here"
        warn "No API key provided. You can add it later to $MCP_CONFIG"
    fi
    
    # Create or update mcp.json
    if [ -f "$MCP_CONFIG" ]; then
        # Use Python to safely update JSON
        $PYTHON_CMD << EOF
import json
import os

config_path = "$MCP_CONFIG"
getademo_cmd = "$GETADEMO_CMD"
openai_key = "$OPENAI_KEY"

# Read existing config
with open(config_path, 'r') as f:
    config = json.load(f)

# Ensure mcpServers exists
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Add/update getademo
config['mcpServers']['getademo'] = {
    "command": getademo_cmd,
    "env": {
        "OPENAI_API_KEY": openai_key
    }
}

# Write updated config
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("Configuration updated successfully")
EOF
    else
        # Create new config
        cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "getademo": {
      "command": "$GETADEMO_CMD",
      "env": {
        "OPENAI_API_KEY": "$OPENAI_KEY"
      }
    }
  }
}
EOF
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
    echo "  1. Open System Settings → Privacy & Security → Screen Recording"
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
    success "getademo has been installed and configured!"
    echo ""
    echo "Next steps:"
    echo "  1. Restart Cursor to load the MCP server"
    echo "  2. Ask the AI: 'Create a demo of [any website]'"
    echo ""
    echo "Configuration:"
    echo "  - Package: $SCRIPT_DIR"
    echo "  - Virtual env: $VENV_DIR"
    echo "  - Cursor config: $CURSOR_CONFIG_DIR/mcp.json"
    echo ""
    echo "Available tools:"
    echo "  - start_recording / stop_recording"
    echo "  - text_to_speech (OpenAI or Edge TTS)"
    echo "  - adjust_video_to_audio_length"
    echo "  - concatenate_videos"
    echo "  - get_demo_protocol"
    echo ""
    echo "Documentation: https://github.com/Schimuneck/getademo"
    echo ""
}

# Main installation flow
main() {
    detect_os
    check_python
    check_ffmpeg
    install_package
    configure_cursor
    check_screen_permission
    print_summary
}

# Run installer
main


