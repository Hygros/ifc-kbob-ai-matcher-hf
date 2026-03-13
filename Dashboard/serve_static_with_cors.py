
import http.server
import os
from http.server import ThreadingHTTPServer

_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://127.0.0.1:8501,http://localhost:8501,http://127.0.0.1:3000,http://localhost:3000"
).split(",")

_ALLOW_ALL_ORIGINS = bool(os.environ.get("SPACE_ID"))


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        origin = self.headers.get("Origin", "")
        if _ALLOW_ALL_ORIGINS and origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        elif origin in _ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        super().end_headers()

if __name__ == '__main__':
    import sys
    import os
    directory = sys.argv[1] if len(sys.argv) > 1 else 'static'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    bind_addr = "0.0.0.0" if os.environ.get("SPACE_ID") else "127.0.0.1"
    os.chdir(directory)
    with ThreadingHTTPServer((bind_addr, port), CORSRequestHandler) as httpd:
        print(f"Serving static files with CORS (HTTP/1.1) at http://{bind_addr}:{port}/")
        httpd.serve_forever()
