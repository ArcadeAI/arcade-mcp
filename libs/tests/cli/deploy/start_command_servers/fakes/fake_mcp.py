"""A stand-in MCP server that answers the handshake on one path.

    python fake_mcp.py --port 8123 [--path /mcp] [--host 127.0.0.1] [--sse] [--launcher]
                       [--decoy-port 8124] [--tools a,b] [--fail-tools-list] [--html-elsewhere]
                       [--bearer TOKEN] [--bearer-for-tools TOKEN] [--key-header H --key K]
                       [--well-known NAME=JSON ...]

``--launcher`` runs this script again as a child process and waits for it, the way
``uv run`` does, so the listener belongs to a descendant rather than the started process.
``--decoy-port`` also listens on a second port that answers every request with 404.
``--html-elsewhere`` answers 200 with a web page on every other path, as a web app does.

Auth: ``--bearer`` refuses every MCP request without that bearer token (401 with a Bearer
challenge, as an OAuth resource server does); ``--bearer-for-tools`` refuses only
``tools/list``; ``--key-header``/``--key`` refuse requests without that static key (401, no
challenge). ``--well-known name=JSON`` serves a document at ``/.well-known/<name>`` (and its
path-inserted form under the MCP path).
"""

import argparse
import json
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


def _refusal(args: argparse.Namespace, headers: object, body: bytes) -> tuple[int, dict[str, str]] | None:
    """The 401 this server answers a request with, or None to serve it."""
    authorization = getattr(headers, "get")("Authorization") or ""
    if args.key_header and getattr(headers, "get")(args.key_header) != args.key:
        return 401, {}
    challenge = {"WWW-Authenticate": 'Bearer resource_metadata="/.well-known/oauth-protected-resource"'}
    if args.bearer and authorization != f"Bearer {args.bearer}":
        return 401, challenge
    if args.bearer_for_tools and authorization != f"Bearer {args.bearer_for_tools}":
        if json.loads(body or b"{}").get("method") == "tools/list":
            return 401, challenge
    return None


def serve(args: argparse.Namespace) -> None:
    documents = {}
    for entry in args.well_known:
        name, _, document = entry.partition("=")
        documents[f"/.well-known/{name}"] = document
        documents[f"/.well-known/{name}{args.path}"] = document

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in documents:
                self._send(200, {"Content-Type": "application/json"}, documents[self.path].encode())
            else:
                self.send_error(404)

        def _send(self, status: int, headers: dict[str, str], payload: bytes) -> None:
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            refusal = _refusal(args, self.headers, body) if self.path == args.path else None
            if refusal:
                self._send(refusal[0], refusal[1], b"")
                return
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
    parser.add_argument("--bearer")
    parser.add_argument("--bearer-for-tools")
    parser.add_argument("--key-header")
    parser.add_argument("--key")
    parser.add_argument("--well-known", action="append", default=[])
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
