"""Minimal local HTTP interface for HYPERLEX_INSTRUMENT_V1.

POST /v1/observe
GET  /v1/health
GET  /v1/manifest
GET  /v1/capabilities
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

from .runtime import get_capabilities, get_manifest, health, observe

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8741


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("X-Hyperlex-Authority", "advisory")
    handler.send_header("X-Hyperlex-Semantic-Truth", "false")
    handler.end_headers()
    handler.wfile.write(body)


class InstrumentHandler(BaseHTTPRequestHandler):
    server_version = "HyperlexInstrument/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter tests
        return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/v1/health":
            _json_response(self, 200, health())
            return
        if path == "/v1/manifest":
            _json_response(self, 200, get_manifest())
            return
        if path == "/v1/capabilities":
            _json_response(self, 200, get_capabilities())
            return
        _json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/v1/observe":
            _json_response(self, 404, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            req = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            _json_response(self, 400, {"ok": False, "error": "invalid_json"})
            return
        text = req.get("text")
        if not isinstance(text, str):
            _json_response(self, 400, {"ok": False, "error": "text_required"})
            return
        requested = req.get("requested")
        try:
            obs = observe(text, requested=requested)
        except ValueError as exc:
            _json_response(self, 400, {"ok": False, "error": str(exc)})
            return
        _json_response(self, 200, obs)


def make_server(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), InstrumentHandler)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    httpd = make_server(host, port)
    print(f"hyperlex-instrument listening on http://{host}:{port}")
    httpd.serve_forever()


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="hyperlex-instrument-api")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = p.parse_args(argv)
    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
