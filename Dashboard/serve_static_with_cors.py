
import http.server
from http.server import ThreadingHTTPServer
class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
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
