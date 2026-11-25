"""Local fake-vendor HTTP fixture for black-box subprocess testing of the
frozen app/napster_adapter.py CLI (factory-lite/tests/CONTRACT.md "Stage 3
adapter CLI"). Not a test module itself (doesn't match test_*.py).

Simulates the two vendor calls the adapter makes:
  POST /v1/sessions                              -> {"session_id": "..."}
  POST /v1/sessions/{session_id}/{avatar|audio|handoff} -> {"status": "ok"}

Each path has its own scripted queue of HTTP status codes; every request
to that path pops the next status (the last one repeats once the queue is
exhausted). All requests are recorded (method, path, body) so tests can
assert exactly how many attempts the adapter made -- this is how the
bounded-retry and duplicate-rejection tests prove the *app's* behavior
without ever reaching a real vendor.
"""
import http.server
import json
import threading


class FakeVendorServer:
    def __init__(self):
        self.requests = []  # list of (method, path, body_dict)
        self._status_queues = {}  # path -> list[int]
        handler_cls = _make_handler(self)
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def script(self, path, statuses):
        """Queue the HTTP status codes this path should return, in order.
        Once exhausted, the last status repeats."""
        self._status_queues[path] = list(statuses)

    def _next_status(self, path):
        queue = self._status_queues.get(path)
        if not queue:
            return 200
        status = queue[0]
        if len(queue) > 1:
            queue.pop(0)
        return status

    @property
    def base_url(self):
        host, port = self.httpd.server_address
        return f"http://127.0.0.1:{port}"

    def request_count(self, path=None):
        if path is None:
            return len(self.requests)
        return sum(1 for _, p, _ in self.requests if p == path)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.httpd.shutdown()
        self.httpd.server_close()


def _make_handler(server):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                body = {}
            server.requests.append(("POST", self.path, body))

            status = server._next_status(self.path)
            if self.path == "/v1/sessions" and status < 400:
                payload = {"session_id": "fake-session-1"}
            elif status < 400:
                payload = {"status": "ok"}
            else:
                payload = {"error": f"fake_status_{status}"}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    return Handler
