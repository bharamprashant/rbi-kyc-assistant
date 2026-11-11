from http.server import BaseHTTPRequestHandler
from _common import handle_ask, MAX_BODY


class handler(BaseHTTPRequestHandler):
    def _send(self, status, headers, body):
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            n = int(self.headers.get("content-length", "0"))
        except ValueError:
            n = 0
        body = self.rfile.read(min(max(n, 0), MAX_BODY + 1))
        self._send(*handle_ask("POST", dict(self.headers), body))

    def do_GET(self):
        self._send(*handle_ask("GET", dict(self.headers), b""))

    def log_message(self, *a):   # never log request lines (privacy)
        pass
