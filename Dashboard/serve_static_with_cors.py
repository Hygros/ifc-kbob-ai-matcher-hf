
import http.server
import os
from http.server import ThreadingHTTPServer


def _build_allowed_origins() -> list[str]:
    """Build the list of allowed CORS origins.

    Local development ports are always permitted.  When running on
    Hugging Face Spaces the Space's own ``*.hf.space`` origin is added
    so that the viewer iframe can fetch IFC files in no-proxy mode.
    The previous behaviour of mirroring *any* ``Origin`` header is
    removed to prevent data exfiltration by arbitrary third-party
    websites.
    """
    origins = os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:8501,http://localhost:8501,http://127.0.0.1:7860,http://localhost:7860,http://127.0.0.1:3000,http://localhost:3000",
    ).split(",")

    space_id = os.environ.get("SPACE_ID", "")
    if space_id:
        # SPACE_ID is e.g. "Hygros/ifc-kbob-ai-matcher-hf" → slug is
        # "hygros-ifc-kbob-ai-matcher-hf"
        slug = space_id.replace("/", "-").lower()
        origins.append(f"https://{slug}.hf.space")

    return [o.strip() for o in origins if o.strip()]


_ALLOWED_ORIGINS: list[str] = _build_allowed_origins()


class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------
    # Security: disable directory listing so that ``GET /`` or any
    # directory path returns 403 instead of an HTML index of files.
    # ------------------------------------------------------------------
    def list_directory(self, path):  # type: ignore[override]
        self.send_error(403, "Directory listing is disabled")
        return None

    def end_headers(self):
        origin = self.headers.get("Origin", "")
        self.send_header("Vary", "Origin")
        if origin in _ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
        super().end_headers()

if __name__ == '__main__':
    import sys
    import os
    directory = sys.argv[1] if len(sys.argv) > 1 else 'static'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    os.chdir(directory)
    with ThreadingHTTPServer(("127.0.0.1", port), CORSRequestHandler) as httpd:
        print(f"Serving static files with CORS (HTTP/1.1) at http://127.0.0.1:{port}/")
        httpd.serve_forever()
