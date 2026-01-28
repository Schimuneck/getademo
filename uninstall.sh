#!/bin/bash
# getademo uninstaller
# Removes virtual environment and Cursor MCP configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              getademo Uninstaller                         ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/.venv"

# Detect OS
case "$(uname -s)" in
    Darwin*)    CURSOR_CONFIG="$HOME/.cursor/mcp.json" ;;
    Linux*)     CURSOR_CONFIG="$HOME/.cursor/mcp.json" ;;
    *)          CURSOR_CONFIG="$HOME/.cursor/mcp.json" ;;
esac

echo "This will remove:"
echo "  - Virtual environment: $VENV_DIR"
echo "  - getademo from Cursor MCP config"
echo ""

read -p "Are you sure you want to uninstall getademo? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "Uninstall cancelled"
    exit 0
fi

# Remove virtual environment
if [ -d "$VENV_DIR" ]; then
    info "Removing virtual environment..."
    rm -rf "$VENV_DIR"
    success "Virtual environment removed"
else
    info "Virtual environment not found"
fi

# Remove from Cursor MCP config
if [ -f "$CURSOR_CONFIG" ]; then
    if grep -q '"getademo"' "$CURSOR_CONFIG" 2>/dev/null; then
        info "Removing getademo from Cursor MCP config..."
        
        # Use Python to safely update JSON
        python3 << EOF
import json

config_path = "$CURSOR_CONFIG"

with open(config_path, 'r') as f:
    config = json.load(f)

if 'mcpServers' in config and 'getademo' in config['mcpServers']:
    del config['mcpServers']['getademo']
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("getademo removed from Cursor config")
else:
    print("getademo not found in Cursor config")
EOF
        success "Cursor MCP config updated"
    else
        info "getademo not found in Cursor MCP config"
    fi
else
    info "Cursor MCP config not found"
fi

echo ""
success "getademo has been uninstalled"
echo ""
echo "Note: The source files remain in $SCRIPT_DIR"
echo "To completely remove, delete the directory:"
echo "  rm -rf $SCRIPT_DIR"
echo ""
echo "Restart Cursor to apply changes."


