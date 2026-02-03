#!/usr/bin/env python3
"""
Simple HTTP server to serve recorded videos from the container.

Serves files from /app/recordings on port 8080.
Access videos at: http://localhost:8080/videos/<filename>
"""

import http.server
import os
import socketserver
from pathlib import Path
from urllib.parse import unquote

RECORDINGS_DIR = Path(os.environ.get("RECORDINGS_DIR", "/app/recordings"))
PORT = int(os.environ.get("VIDEO_SERVER_PORT", 8080))


class VideoHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves videos from the recordings directory."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RECORDINGS_DIR), **kwargs)
    
    def translate_path(self, path):
        """Override to serve from RECORDINGS_DIR."""
        # Remove /videos prefix if present
        path = unquote(path)
        if path.startswith("/videos/"):
            path = path[7:]  # Remove "/videos"
        elif path.startswith("/videos"):
            path = path[6:]  # Remove "/videos" (no trailing slash)
        
        # Ensure path doesn't escape recordings dir
        path = path.lstrip("/")
        full_path = RECORDINGS_DIR / path
        
        # Security: ensure we stay within recordings dir
        try:
            full_path.resolve().relative_to(RECORDINGS_DIR.resolve())
            return str(full_path)
        except ValueError:
            # Path escapes recordings dir
            return str(RECORDINGS_DIR / "nonexistent")
    
    def do_GET(self):
        """Handle GET requests."""
        # Root path shows directory listing
        if self.path in ("/", "/videos", "/videos/"):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            html = self._generate_listing()
            self.wfile.write(html.encode())
            return
        
        # Otherwise serve the file
        super().do_GET()
    
    def _generate_listing(self) -> str:
        """Generate an HTML directory listing."""
        files = []
        for f in sorted(RECORDINGS_DIR.rglob("*")):
            if f.is_file():
                rel_path = f.relative_to(RECORDINGS_DIR)
                size_mb = f.stat().st_size / (1024 * 1024)
                files.append((str(rel_path), size_mb))
        
        rows = "\n".join(
            f'<tr><td><a href="/videos/{path}">{path}</a></td><td>{size:.2f} MB</td></tr>'
            for path, size in files
        )
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Demo Recordings</title>
    <style>
        body {{ font-family: system-ui, sans-serif; padding: 20px; max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        tr:hover {{ background: #f9f9f9; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .count {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>📹 Demo Recordings</h1>
    <p class="count">{len(files)} file(s) in recordings directory</p>
    <table>
        <tr><th>File</th><th>Size</th></tr>
        {rows if files else '<tr><td colspan="2">No recordings yet</td></tr>'}
    </table>
</body>
</html>"""

    def log_message(self, format, *args):
        """Suppress logging to keep stdout clean for MCP."""
        pass  # Don't log to stdout - MCP uses it


def main():
    """Start the video server."""
    # Ensure recordings directory exists
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Allow address reuse
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("0.0.0.0", PORT), VideoHandler) as httpd:
        # Print to stderr since stdout is used by MCP
        print(f"Video server running on port {PORT}", file=__import__('sys').stderr)
        print(f"Access videos at: http://localhost:{PORT}/videos/", file=__import__('sys').stderr)
        httpd.serve_forever()


if __name__ == "__main__":
    main()



















