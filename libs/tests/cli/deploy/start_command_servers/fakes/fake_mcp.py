"""A stand-in MCP server that answers the handshake on one path.

    python fake_mcp.py --port 8123 [--path /mcp] [--host 127.0.0.1] [--sse] [--launcher]
                       [--decoy-port 8124] [--tools a,b] [--fail-tools-list] [--html-elsewhere]

``--launcher`` runs this script again as a child process and waits for it, the way
``uv run`` does, so the listener belongs to a descendant rather than the started process.
``--decoy-port`` also listens on a second port that answers every request with 404.
``--html-elsewhere`` answers 200 with a web page on every other path, as a web app does.
"""

import argparse
import socket
import socketserver
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from fake_responses import answer


class Server(ThreadingHTTPServer):
    def __init__(self, host: str, port: int, handler: type[BaseHTTPRequestHandler]) -> None:
        self.address_family = socket.AF_INET6 if ":" in host else socket.AF_INET
        super().__init__((host, port), handler)

    def server_bind(self) -> None:
        # HTTPServer.server_bind looks up socket.getfqdn(host) between bind() and listen().
        # That reverse DNS lookup can stall for seconds (GitHub's macOS runners), leaving
        # the port bound but not listening, so skip it.
        socketserver.TCPServer.server_bind(self)
        self.server_name = str(self.server_address[0])
        self.server_port = int(self.server_address[1])


class NotFound(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.send_error(404)

    def log_message(self, format: str, *args: object) -> None:
        pass


def serve(args: argparse.Namespace) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path != args.path:
                if not args.html_elsewhere:
                    self.send_error(404)
                    return
                status, headers, payload = 200, {"Content-Type": "text/html"}, b"<html></html>"
            else:
                status, headers, payload = answer(
                    body,
                    sse=args.sse,
                    tools=tuple(args.tools.split(",")),
                    fail_tools_list=args.fail_tools_list,
                )
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass

    Server(args.host, args.port, Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--sse", action="store_true")
    parser.add_argument("--launcher", action="store_true")
    parser.add_argument("--decoy-port", type=int)
    parser.add_argument("--tools", default="echo")
    parser.add_argument("--fail-tools-list", action="store_true")
    parser.add_argument("--html-elsewhere", action="store_true")
    args = parser.parse_args()

    if args.launcher:
        child_args = [arg for arg in sys.argv[1:] if arg != "--launcher"]
        sys.exit(subprocess.call([sys.executable, __file__, *child_args]))

    if args.decoy_port:
        decoy = Server(args.host, args.decoy_port, NotFound)
        threading.Thread(target=decoy.serve_forever, daemon=True).start()
    serve(args)


if __name__ == "__main__":
    main()
