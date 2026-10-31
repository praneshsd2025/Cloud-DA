import os
import sys
import threading
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "frontend"))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))

class GazeboProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy_request("GET")
        else:
            # SPA fallback: if file does not exist, serve index.html
            local_path = os.path.join(FRONTEND_DIR, self.path.lstrip("/").split("?")[0])
            if not os.path.exists(local_path) and not self.path.startswith("/images/"):
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy_request("POST")
        else:
            self.send_error(405)

    def do_PUT(self):
        if self.path.startswith("/api/"):
            self.proxy_request("PUT")
        else:
            self.send_error(405)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self.proxy_request("DELETE")
        else:
            self.send_error(405)

    def proxy_request(self, method):
        target_url = f"http://127.0.0.1:5000{self.path}"
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        headers = {}
        for k, v in self.headers.items():
            if k.lower() not in ["host", "content-length"]:
                headers[k] = v
        headers["Host"] = "localhost:8080"

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ["transfer-encoding", "content-length"]:
                        self.send_header(k, v)
                resp_body = resp.read()
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ["transfer-encoding", "content-length"]:
                    self.send_header(k, v)
            err_body = e.read()
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            err_msg = f'{{"error": "Bad Gateway: {str(e)}"}}'.encode()
            self.send_header("Content-Length", str(len(err_msg)))
            self.end_headers()
            self.wfile.write(err_msg)


def start_backend():
    sys.path.insert(0, BACKEND_DIR)
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BACKEND_DIR, ".env"))
    import app as flask_app
    print("Starting Flask Backend on http://127.0.0.1:5000 ...", flush=True)
    flask_app.app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def start_frontend():
    print("Starting Frontend Reverse Proxy on http://localhost:8080 ...", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", 8080), GazeboProxyHandler)
    server.serve_forever()


if __name__ == "__main__":
    t_backend = threading.Thread(target=start_backend, daemon=True)
    t_backend.start()

    # Wait 2 seconds for backend to start
    import time
    time.sleep(2)

    start_frontend()

