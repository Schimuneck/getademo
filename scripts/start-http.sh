#!/bin/bash
set -e

echo "Starting Xvfb..."
Xvfb :99 -screen 0 ${XVFB_RESOLUTION:-2560x1440x24} &
sleep 2

echo "Starting openbox..."
DISPLAY=:99 openbox &
sleep 1

echo "Starting video server on port ${VIDEO_SERVER_PORT:-8090}..."
python /app/scripts/video-server.py &

echo "Starting FastMCP Proxy Multiplexer on port ${MCP_PORT:-8080}..."
echo "This will expose all tools: demo-recorder (13) + Playwright (22) = 35 tools"
exec python -m recorder.proxy_multiplexer

