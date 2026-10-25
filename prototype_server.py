"""THROWAWAY prototype server. Run: python prototype_server.py. No persistence or external services."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import os

ROOT = Path(__file__).resolve().parent
FILES = {
    "/": ("prototype.html", "text/html; charset=utf-8"),
    "/prototype": ("prototype.html", "text/html; charset=utf-8"),
    "/prototype.html": ("prototype.html", "text/html; charset=utf-8"),
    "/prototype.css": ("prototype.css", "text/css; charset=utf-8"),
    "/prototype.js": ("prototype.js", "text/javascript; charset=utf-8"),
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        entry = FILES.get(urlsplit(self.path).path)
        if entry is None:
            self.send_error(404)
            return
        body = (ROOT / entry[0]).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", entry[1])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    if os.environ.get("APP_ENV") == "production":
        raise SystemExit("This is a throwaway prototype, not a production server.")
    port = int(os.environ.get("PROTOTYPE_PORT", "8765"))
    print(f"Prototype: http://127.0.0.1:{port}/prototype?variant=A", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
