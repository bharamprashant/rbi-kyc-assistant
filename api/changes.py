from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit
from _common import handle_changes


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status, headers, body = handle_changes("GET", dict(self.headers), urlsplit(self.path).query)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass
