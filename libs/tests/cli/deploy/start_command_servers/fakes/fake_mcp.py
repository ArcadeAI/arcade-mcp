"""A stand-in MCP server that answers the handshake on one path.

    python fake_mcp.py --port 8123 [--path /mcp] [--host 127.0.0.1] [--sse] [--launcher]
                       [--decoy-port 8124]

``--launcher`` runs this script again as a child process and waits for it, the way
``uv run`` does, so the listener belongs to a descendant rather than the started process.
``--decoy-port`` also listens on a second port that answers every request with 404.
"""

import argparse
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fake_responses import answer


class Server(ThreadingHTTPServer):
    def __init__(self, host: str, port: int, handler: type[BaseHTTPRequestHandler]) -> None:
        self.address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        super().__init__((host, port), handler)


class NotFound(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(host: str, port: int, path: str, sse: bool) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path != path:
                self.send_error(404)
                return
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            status, headers, payload = answer(body, sse=sse)
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    Server(host, port, Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--sse", action="store_true")
    parser.add_argument("--launcher", action="store_true")
    parser.add_argument("--decoy-port", type=int)
    args = parser.parse_args()

    if args.launcher:
        child_args = [arg for arg in sys.argv[1:] if arg != "--launcher"]
        sys.exit(subprocess.call([sys.executable, __file__, *child_args]))

    if args.decoy_port:
        decoy = Server(args.host, args.decoy_port, NotFound)
        threading.Thread(target=decoy.serve_forever, daemon=True).start()
    serve(args.host, args.port, args.path, args.sse)


if __name__ == "__main__":
    main()
